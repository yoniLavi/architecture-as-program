"""Is a green body *behaviourally* the body it replaces, on the inputs we have?

A green trial is a body that fits its node: it builds, imports only what the
node's `with` clause grants, keeps its contract on generated inputs, and lets the
graph run. The contract vocabulary cannot say what a body should *compute*, so
green says nothing about whether it computes what the hand-written body does.
This step asks that, and reports the answer as information: it does not gate a
trial, because the hand-written body is one implementation, not the
specification. A body may differ and be right.

**How.** For each input the node's contract generates (`Subject.test_inputs`, the
same inputs the contract step uses), run the hand-written component and the
generated one, each with fresh stub handles, both on the confined tier through
the same adapter, and compare what each returned and what each did to its
handles: messages sent, notifications, events emitted, state written, and the
task labels of the model calls it made.

**The model stand-in.** For a node that calls a model, the comparison must not
measure prompt wording: two bodies that word a prompt differently would get
different replies from a stand-in that reads the prompt (as `StubLLM`, keyword by
keyword, does), and every such pair would "differ". So `KeyedLLM` answers from
the request's **task label** and the **node's input** alone — it never reads the
prompt — and, for a tool-capable client, from how many calls it has answered.
The input is not visible behind the handle; the step builds a fresh stand-in per
input, keyed to it. A body that passes a different task label gets a different
reply, and that is reported as a difference, because it is one.

Runs in the check process (`check.py --differential`): a generated body may loop.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

from ..feed_values import Category, Importance
from ..handles import (
    AppendDBHandle,
    EventEmitter,
    InferenceLLM,
    Notifier,
    ReadWriteStateHandle,
    ResponseChannel,
    ToolLLM,
)
from ..llm import LLMRequest, LLMResponse, ToolCall
from ..values import Intent


def input_key(value: object) -> str:
    """A stable key for one input: the digest of its repr. Every input type here
    is a frozen dataclass, tuple, `Untrusted` wrapper or string, whose repr is
    deterministic."""
    return hashlib.sha256(repr(value).encode()).hexdigest()


def _pick(options: list[str], key: str, salt: str) -> str:
    digest = hashlib.sha256(f"{salt}:{key}".encode()).digest()
    return options[int.from_bytes(digest[:4], "big") % len(options)]


@dataclass
class KeyedLLM:
    """A model stand-in that never reads the prompt.

    Its reply is a function of the task label, the input key, and (for the tool
    path) how many calls it has answered. Replies for the labels the hand-written
    bodies use are drawn from the closed sets those bodies parse — an intent, a
    moderation verdict, a `<category> <importance>` pair — so a reply is always
    one a correct body can handle."""

    key: str
    calls: list[str] = field(default_factory=list)

    def generate(self, request: LLMRequest) -> LLMResponse:
        index = len(self.calls)
        self.calls.append(request.task)
        task, key = request.task, self.key
        if request.offered_tools and index == 0:
            tool = sorted(request.offered_tools)[0]
            return LLMResponse(tool_calls=(ToolCall(tool, {"query": f"q-{key[:8]}"}),))
        if task == "classify":
            text = _pick([i.value for i in Intent], key, task)
        elif task == "moderate":
            text = _pick(["ok", "ok", "ok", "violation"], key, task)
        elif task == "triage":
            category = _pick([c.value for c in Category], key, "category")
            importance = _pick([i.value for i in Importance], key, "importance")
            text = f"{category} {importance}"
        else:
            text = f"{task} reply {key[:12]}."
        return LLMResponse(text=text)


def keyed_handles(handles: tuple, value: object) -> tuple:
    """`handles` with every model client's backend replaced by a `KeyedLLM` for
    this input. Everything else is the subject's own fresh stub."""
    key = input_key(value)
    out = []
    for h in handles:
        if isinstance(h, InferenceLLM):
            out.append(InferenceLLM(KeyedLLM(key)))
        elif isinstance(h, ToolLLM):
            out.append(ToolLLM(KeyedLLM(key), h.allowed_tools))
        else:
            out.append(h)
    return tuple(out)


def effects(handles: tuple) -> list:
    """What a call did to its handles, in `with`-clause order. Reads leave no
    effect; a model call leaves its task label (never its prompt)."""
    out: list = []
    for h in handles:
        if isinstance(h, InferenceLLM | ToolLLM) and isinstance(h.backend, KeyedLLM):
            out.append(("model", tuple(h.backend.calls)))
        elif isinstance(h, ResponseChannel | Notifier):
            out.append(("sent", tuple(h.sent)))
        elif isinstance(h, EventEmitter):
            out.append(("emitted", tuple(h.emitted)))
        elif isinstance(h, AppendDBHandle):
            out.append(("appended", tuple(h.appended)))
        elif isinstance(h, ReadWriteStateHandle):
            store = h._store
            keys = store.keys()  # StateStore's own method: its keys, sorted
            out.append(("state", tuple((k, store.get(k)) for k in keys)))
        else:
            out.append(("none",))
    return out


def _describe(value: object, limit: int = 400) -> str:
    text = repr(value)
    return text if len(text) <= limit else text[:limit] + "…"


def observe(call, subject, value, faults: tuple[type[BaseException], ...] = ()) -> tuple:
    """(outcome, effects) of one body on one input. An exception is an outcome:
    two bodies that both refuse an input the same way agree on it. `faults` are
    the harness's own failures (an incomplete host binding), which are never a
    body's behaviour and propagate."""
    handles = keyed_handles(subject.handles(), value)
    args = value if subject.arity > 1 else (value,)
    try:
        outcome: tuple = ("returned", call(*args, *handles))
    except faults:
        raise
    except Exception as e:  # what a body raises is part of what it does
        outcome = ("raised", type(e).__name__)
    return outcome, effects(handles)


@dataclass
class Comparison:
    inputs: int
    equal_on: int
    first_difference: dict | None

    @property
    def equal(self) -> bool:
        return self.equal_on == self.inputs

    def to_dict(self) -> dict:
        return {
            "inputs": self.inputs,
            "equal_on": self.equal_on,
            "equal": self.equal,
            "first_difference": self.first_difference,
        }


def compare(
    subject, reference_call, generated_call, faults: tuple[type[BaseException], ...] = ()
) -> Comparison:
    """Both bodies on every contract-generated input; the first difference kept."""
    inputs = subject.test_inputs()
    equal_on = 0
    first = None
    for value in inputs:
        ref = observe(reference_call, subject, value, faults)
        gen = observe(generated_call, subject, value, faults)
        if ref == gen:
            equal_on += 1
        elif first is None:
            first = {
                "input": _describe(value),
                "hand_written": {"outcome": _describe(ref[0]), "effects": _describe(ref[1])},
                "generated": {"outcome": _describe(gen[0]), "effects": _describe(gen[1])},
            }
    return Comparison(len(inputs), equal_on, first)
