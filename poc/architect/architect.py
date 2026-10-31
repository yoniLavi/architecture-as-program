"""The architect: a task in natural language → a library graph, in two stages (tasks 1.3, 1.4).

    record = author(task_prompt, backend)            # channel A, or no pretext
    record = author(task_prompt, backend, document)  # channel B: a document beside it

Each stage repairs at most `MAX_REPAIRS` times, as Paper 3's harness does; a stage
still failing after them ends the attempt, recorded, never retried silently. What
drives a repair is a stage's own check: stage one's schema, then stage two's shape,
the validator and the library check (`verdicts.py`). **The link check and the
least-authority check are not in the loop.** They are the formal review, which judges
the graph the architect hands over; if their verdicts went back for repair, a
fabricated justification would be repaired into a quoted one before the review saw it.

**What the architect is shown, and nothing else:** the two stages' system texts, the
task, the document (channel B), its own abstract graph, its own earlier replies, and
reasons from a closed set of classes. No tool output, no injection, no reviewer
verdict: `author` takes no argument through which one could arrive, and a test holds
every request to that list.

Every input is hashed into the record, as Paper 3's task texts are, so a record names
exactly what its model was shown.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from ..llm import LLMBackend, LLMRequest, ModelCallError, UsageLimitReached
from . import abstract, mapping, verdicts
from .abstract import Reason

MAX_REPAIRS = 4

GRAPH = "graph"
INEXPRESSIBLE = "inexpressible"
FAILED_STAGE_ONE = "failed-stage-one"
FAILED_STAGE_TWO = "failed-stage-two"
OUTCOMES = (GRAPH, INEXPRESSIBLE, FAILED_STAGE_ONE, FAILED_STAGE_TWO)

CALL_FAILED = "model-call-failed"

REPAIR = (
    "{shown}\nYour previous reply:\n\n{reply}\n\n"
    "It was rejected, for these reasons (class: detail):\n\n{reasons}\n\n"
    "Reply with the corrected JSON object only."
)


class ModelMismatch(RuntimeError):
    """A call resolved to a model other than the one a registered run names."""


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def inputs(task_prompt: str, document: str | None = None) -> dict[str, str | None]:
    """The hashes of everything fixed that the architect is shown. Its abstract graph,
    its replies and their reasons are its own, and are in the record whole."""
    return {
        "stage_one_system": sha256(abstract.STAGE_ONE_SYSTEM),
        "stage_two_system": sha256(mapping.system()),
        "task_prompt": sha256(task_prompt),
        "document": None if document is None else sha256(document),
    }


def repair_text(shown: str, reply: str, reasons: list[Reason]) -> str:
    listed = "\n".join(f"- {r.cls}: {r.detail}" for r in reasons)
    return REPAIR.format(shown=shown, reply=reply, reasons=listed)


@dataclass
class _Caller:
    backend: LLMBackend
    expected_model: str | None
    model_ids: list[str] = field(default_factory=list)

    def __call__(self, system: str, prompt: str, stage: str) -> tuple[str, float]:
        began = time.perf_counter()
        try:
            reply = self.backend.generate(
                LLMRequest(system=system, prompt=prompt, task=f"architect:{stage}")
            ).text
        except UsageLimitReached:
            raise
        except ModelCallError as e:
            # Recorded as an attempt that produced nothing, so attempts stay counted.
            return f"[{CALL_FAILED}: {e}]", time.perf_counter() - began
        usage = getattr(self.backend, "usage", None)
        model_id = usage[-1]["model"] if usage else None
        if self.expected_model is not None and model_id != self.expected_model:
            raise ModelMismatch(
                f"the call resolved to {model_id!r}, not the registered {self.expected_model!r}"
            )
        if model_id is not None:
            self.model_ids.append(model_id)
        return reply, time.perf_counter() - began


def _stage(call: _Caller, stage: str, system: str, shown: str, parse) -> tuple[Any, list[dict]]:
    """Run one stage to a parse or to its repair bound. Returns (result, attempts)."""
    attempts: list[dict] = []
    prompt = shown
    for index in range(1, MAX_REPAIRS + 2):  # the first attempt, then the repairs
        reply, seconds = call(system, prompt, stage)
        result, reasons = parse(reply)
        attempts.append(
            {
                "stage": stage,
                "index": index,
                "prompt_sha256": sha256(prompt),
                "reply": reply,
                "reasons": [r.as_dict() for r in reasons],
                "model_seconds": round(seconds, 1),
            }
        )
        if not reasons:
            return result, attempts
        prompt = repair_text(shown, reply, reasons)
    return None, attempts


def author(
    task_prompt: str,
    backend: LLMBackend,
    document: str | None = None,
    *,
    name: str = "ArchitectGraph",
    expected_model: str | None = None,
) -> dict:
    """One architect attempt, recorded whole. Raises `UsageLimitReached` if the
    backend stops (nothing is recorded), and `ModelMismatch` for a registered run
    whose call resolved elsewhere."""
    call = _Caller(backend, expected_model)
    started = datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    record: dict[str, Any] = {
        "started": started,
        "inputs_sha256": inputs(task_prompt, document),
        "max_repairs": MAX_REPAIRS,
    }

    shown_one = abstract.prompt(task_prompt, document)
    abstract_graph, one = _stage(call, "one", abstract.STAGE_ONE_SYSTEM, shown_one, abstract.parse)
    record["attempts"] = one
    if abstract_graph is None:
        return {**record, "outcome": FAILED_STAGE_ONE, "graph": None,
                "abstract": None, "model_ids": sorted(set(call.model_ids))}  # fmt: skip

    def verdict(reply: str) -> tuple[Any, list[Reason]]:
        out, reasons = mapping.parse(reply, name)
        if reasons or isinstance(out, mapping.Inexpressible):
            return out, reasons
        return out, verdicts.check(out)

    shown_two = mapping.prompt(task_prompt, abstract_graph, document)
    out, two = _stage(call, "two", mapping.system(), shown_two, verdict)
    record["attempts"] = one + two
    if isinstance(out, mapping.Inexpressible):
        outcome, graph, why = INEXPRESSIBLE, None, out.why
    else:
        outcome, graph, why = (GRAPH if out is not None else FAILED_STAGE_TWO), out, None
    return {
        **record,
        "outcome": outcome,
        "abstract": abstract_graph,
        "graph": graph,
        "inexpressible": why,
        "model_ids": sorted(set(call.model_ids)),
    }
