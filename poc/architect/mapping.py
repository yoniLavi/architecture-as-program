"""Stage two: the abstract graph plus the catalogue → a graph over the node library (D1).

The catalogue the architect is shown is rendered from `library.CATALOGUE` and
`library.RECORDS`, so it cannot drift from what the library runs. It documents
**shapes, never values**: the fields each reader returns and their types, but no fact
about what the bank holds (who `sender` is on the user's own payments, which orders
exist, today's date). Those are tool output, which the architect never sees (design,
"What the architect never sees"). Where a value cannot be named in advance, the
architect has to read it at run time, through a selector or `Extract`.

Every grant carries a `because`: node-level, capability → a quote of the task. The
link check (`formal.py`) holds each quote to the prompt.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..agentdojo.library import (
    CATALOGUE,
    COMPOSE,
    EXTRACT,
    READER,
    RECORDS,
    RESPOND,
    SELECTOR,
    START,
    WRITER,
)
from .abstract import SHAPE, Reason, parse_json_object

PROMPTS = Path(__file__).resolve().parent / "prompts"
EXAMPLE = json.loads((PROMPTS / "example.json").read_text())

# What the readers and selectors return, field → type. Shapes, not values.
SHAPES: dict[str, dict[str, str]] = {
    "TaskRequest": {"prompt": "string"},
    "Transaction": {"id": "number", "sender": "string", "recipient": "string",
                    "amount": "number", "subject": "string", "date": "string",
                    "recurring": "boolean"},
    "FileText": {"text": "string"},
    "UserInfo": {"first_name": "string", "last_name": "string", "street": "string",
                 "city": "string"},
    "Balance": {"amount": "number"},
    "Iban": {"iban": "string"},
    "Total": {"amount": "number"},
    "NoMatch": {"matched": "number"},
    "Receipt": {"result": "string"},
}  # fmt: skip

_FAMILY_NOTE = {
    START: "Input: `TaskRequest`. Output: `TaskRequest`.",
    SELECTOR: "Input: one `Untrusted<TransactionList>`. The output keeps that label: "
    "`Untrusted<Transaction>`, `Untrusted<TransactionList>`, `Untrusted<Total>`, or "
    "`found: Untrusted<Transaction> | none: Untrusted<NoMatch>`. Holds no capability.",
    "Branch": "Input: any one value `T`; output `yes: T | no: T`, keeping `T`'s label. "
    "Holds no capability.",
    COMPOSE: "Inputs: any data. Output: a type you name; if it is one of the records "
    "below, the fields must fit it. Holds no capability.",
    EXTRACT: "Inputs: any data, then `LLMClient<inference>`. Output: a type you name, "
    "whose fields are the `fields` parameter.",
    RESPOND: "Inputs: any data, then `ResponseChannel<user-session>`. Output: "
    "`DeliveryConfirmation`. Every graph ends here.",
}


def _shape(fields: dict[str, str]) -> str:
    return "{" + ", ".join(f"{k}: {v}" for k, v in fields.items()) + "}"


def catalogue() -> str:
    """The library, as stage two is shown it."""
    lines: list[str] = []
    for e in CATALOGUE.values():
        line = f"- `{e.name}`: {e.doc}"
        if e.family == READER:
            scope = f"{e.scope}<name>" if e.scope == "file:" else e.scope
            line += (
                f" Inputs: `TaskRequest`, then `DBHandle<'{scope}', read>`. Output: `{e.output}`."
            )
        elif e.family == WRITER:
            record = e.inputs[0]  # type: ignore[index]
            line += f" Inputs: `{record}`, then a `{e.capability}` capability. Output: `Receipt`."
        else:
            line += " " + _FAMILY_NOTE.get(e.name, _FAMILY_NOTE[e.family])
        if e.params:
            line += " Parameters: " + "; ".join(f"`{k}`: {v}" for k, v in e.params.items()) + "."
        lines.append(line)
    lines += ["", "Data shapes (field: type):", ""]
    lines += [f"- `{name}` {_shape(fields)}" for name, fields in SHAPES.items()]
    lines.append("- `TransactionList`: a list of `Transaction`")
    lines += ["", "Records the writers take (`?` marks an optional field):", ""]
    lines += [f"- `{name}` {_shape(fields)}" for name, fields in RECORDS.items()]
    return "\n".join(lines)


def section(title: str) -> str:
    """One `## title` section of the stage-two text, so the reviewer reads the kinds
    exactly as the architect does."""
    text = (PROMPTS / "stage-two.md").read_text()
    body = text.split(f"## {title}\n", 1)[1]
    return body.split("\n## ", 1)[0].strip()


def system() -> str:
    text = (PROMPTS / "stage-two.md").read_text()
    return text.replace("{{CATALOGUE}}", catalogue()).replace(
        "{{EXAMPLE}}", json.dumps(EXAMPLE, indent=1)
    )


def prompt(task_prompt: str, abstract_graph: dict, document: str | None = None) -> str:
    """What stage two is shown, beside the system text: the task (which every
    `because` must quote), the document in channel B, and its own abstract graph."""
    text = f"The task, from the user:\n\n{task_prompt}\n"
    if document is not None:
        text += f"\nA document the user gave you with the task:\n\n{document}\n"
    text += f"\nYour abstract graph:\n\n{json.dumps(abstract_graph, indent=1)}\n"
    return text


@dataclass(frozen=True)
class Inexpressible:
    """The architect's answer that the library cannot carry out the task."""

    why: str


GRAPH_FIELDS = ("parameters", "capabilities", "nodes", "data_edges")


def parse(reply: str, name: str) -> tuple[dict | Inexpressible | None, list[Reason]]:
    """A stage-two reply → a graph named `name`, an `Inexpressible`, or the reasons it
    is neither. Only the top-level shape is checked here; the validator and the library
    check judge the graph (`verdicts.py`)."""
    obj, reasons = parse_json_object(reply)
    if reasons:
        return None, reasons
    if not isinstance(obj, dict):
        return None, [Reason(SHAPE, "the reply is not a JSON object")]
    if set(obj) == {"inexpressible"} and isinstance(obj["inexpressible"], str):
        return Inexpressible(obj["inexpressible"]), []
    found: list[Reason] = []
    extra = sorted(set(obj) - {*GRAPH_FIELDS, "name"})
    if extra:
        found.append(Reason(SHAPE, f"the graph has fields outside the shape: {extra}"))
    for key in GRAPH_FIELDS:
        if not isinstance(obj.get(key), list):
            found.append(Reason(SHAPE, f"the graph needs a list {key!r}"))
    if not found and not all(isinstance(n, dict) for n in obj["nodes"]):
        found.append(Reason(SHAPE, "every node must be an object"))
    if found:
        return None, found
    graph: dict[str, Any] = {"name": name, **{k: obj[k] for k in GRAPH_FIELDS}}
    return graph, []
