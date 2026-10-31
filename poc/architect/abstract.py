"""Stage one: the prompt → an abstract graph, with no capability catalogue (design D1).

The architect names each step by its role and says what each edge carries. It is not
told about capability kinds, so it cannot reach for one here; which stage widens
authority under a pretext is then visible, because only stage two can.

The output schema is checked here, and each failure is a `Reason`: a class from a closed
set and a detail written by this checker about the architect's own output. That pair is
all the architect is shown when it repairs.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

PROMPTS = Path(__file__).resolve().parent / "prompts"
STAGE_ONE_SYSTEM = (PROMPTS / "stage-one.md").read_text()

NAME = re.compile(r"^[A-Z][A-Za-z0-9]*$")

# The reason classes stage one can earn, closed.
NOT_JSON = "not-json"
SHAPE = "shape"
BAD_NAME = "bad-name"
DUPLICATE = "duplicate-name"
UNKNOWN_NODE = "unknown-node"
CYCLE = "cycle"
STAGE_ONE_CLASSES = (NOT_JSON, SHAPE, BAD_NAME, DUPLICATE, UNKNOWN_NODE, CYCLE)


@dataclass(frozen=True)
class Reason:
    """One structured verdict on the architect's own output."""

    cls: str
    detail: str

    def as_dict(self) -> dict[str, str]:
        return asdict(self)


def parse_json_object(text: str) -> tuple[Any, list[Reason]]:
    """The one JSON object in a reply (code fences and prose around it tolerated)."""
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < start:
        return None, [Reason(NOT_JSON, "the reply holds no JSON object")]
    try:
        return json.loads(text[start : end + 1]), []
    except json.JSONDecodeError as e:
        return None, [Reason(NOT_JSON, f"the reply's JSON does not parse: {e}")]


def _fields(obj: Any, required: tuple[str, ...], where: str) -> list[Reason]:
    if not isinstance(obj, dict):
        return [Reason(SHAPE, f"{where} is not an object")]
    out = []
    extra = sorted(set(obj) - set(required))
    if extra:
        out.append(Reason(SHAPE, f"{where} has fields outside the shape: {extra}"))
    for key in required:
        if not isinstance(obj.get(key), str) or not obj[key].strip():
            out.append(Reason(SHAPE, f"{where} needs a non-empty string {key!r}"))
    return out


def check(abstract: Any) -> list[Reason]:
    """Every way `abstract` misses stage one's schema; empty if it fits."""
    if not isinstance(abstract, dict):
        return [Reason(SHAPE, "the reply is not a JSON object")]
    reasons: list[Reason] = []
    extra = sorted(set(abstract) - {"nodes", "edges"})
    if extra:
        reasons.append(Reason(SHAPE, f"the graph has fields outside the shape: {extra}"))
    nodes, edges = abstract.get("nodes"), abstract.get("edges")
    if not isinstance(nodes, list) or not nodes:
        return [*reasons, Reason(SHAPE, "`nodes` must be a non-empty list")]
    if not isinstance(edges, list):
        return [*reasons, Reason(SHAPE, "`edges` must be a list")]
    names: list[str] = []
    for i, n in enumerate(nodes):
        found = _fields(n, ("name", "role"), f"node {i}")
        reasons += found
        if found or not isinstance(n, dict):
            continue
        if not NAME.match(n["name"]):
            reasons.append(Reason(BAD_NAME, f"node name {n['name']!r} is not CamelCase"))
        if n["name"] in names:
            reasons.append(Reason(DUPLICATE, f"two nodes are named {n['name']!r}"))
        names.append(n["name"])
    successors: dict[str, set[str]] = {name: set() for name in names}
    for i, e in enumerate(edges):
        found = _fields(e, ("from", "to", "carries"), f"edge {i}")
        reasons += found
        if found or not isinstance(e, dict):
            continue
        for end in ("from", "to"):
            if e[end] not in successors:
                reasons.append(Reason(UNKNOWN_NODE, f"edge {i} names {e[end]!r}, not a node"))
        if e["from"] in successors and e["to"] in successors:
            successors[e["from"]].add(e["to"])
    if _has_cycle(successors):
        reasons.append(Reason(CYCLE, "the edges form a cycle"))
    return reasons


def _has_cycle(successors: dict[str, set[str]]) -> bool:
    state: dict[str, int] = {}  # 1 on the stack, 2 done

    def visit(n: str) -> bool:
        state[n] = 1
        for m in successors[n]:
            if state.get(m) == 1 or (m not in state and visit(m)):
                return True
        state[n] = 2
        return False

    return any(n not in state and visit(n) for n in successors)


def parse(reply: str) -> tuple[dict | None, list[Reason]]:
    """A stage-one reply → the abstract graph, or the reasons it is not one."""
    obj, reasons = parse_json_object(reply)
    if reasons:
        return None, reasons
    reasons = check(obj)
    return (None, reasons) if reasons else (obj, [])


def prompt(task_prompt: str, document: str | None = None) -> str:
    """What stage one is shown: the task, and (channel B) a document it is given."""
    text = f"The task, from the user:\n\n{task_prompt}\n"
    if document is not None:
        text += f"\nA document the user gave you with the task:\n\n{document}\n"
    return text
