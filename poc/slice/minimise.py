"""Crude minimisation (north-star step 6, task 4.1): narrow each grant to what the graph
can exercise.

From the behaviour view's provenance (`behaviour.provenance`), per grant:
* `Payments`: the payees narrow to the one payee every writer holding the grant sends
  as a constant, and the cap to the largest constant amount they send; a payee or
  amount the graph computes leaves that part as it is;
* `ScheduledPayments`, `UserProfile`: the fields narrow to those some writer holding
  the grant sets;
* a grant no node holds is dropped.

A grant a `Custom` node holds is not narrowed: its developer's code can use whatever
the handle admits, and nothing here reads the code. Nor are readers, inference or the
answer channel, whose scope is already one source or one session.

It reports each grant, its narrowed form and what was removed, and returns the
narrowed graph. Whether the narrowed graph still has utility is the slice run's to
measure (5.1), not this module's. By the roadmap's note it is expected to remove
little, and the 2.1 replay found no grant admitting a field its graph never sets.

Deterministic and stdlib-only; it calls no model.
"""

from __future__ import annotations

import copy
from decimal import Decimal, InvalidOperation

from ..agentdojo.library import SLICE_CATALOGUE, WRITER
from .behaviour import ALL, provenance, read_scope


def _writer_values(graph: dict, writer: str, prov: dict) -> dict[str, frozenset]:
    """A writer's input record: field → origins, from every edge into it."""
    out: dict[str, set] = {}
    for e in graph["data_edges"]:
        if e["to"] == writer:
            for k, v in prov.get(e["from"].split(".")[0], {}).items():
                out.setdefault(k, set()).update(v)
    return {k: frozenset(v) for k, v in out.items()}


def _field(values: dict[str, frozenset], name: str) -> frozenset:
    return values.get(name, values.get(ALL, frozenset()))


def _constants(origins: frozenset) -> list | None:
    """The constant values of a field, or None if any origin is not a constant."""
    if not origins or any(o[0] != "const" for o in origins):
        return None
    return [o[1] for o in origins]


def _amount(value: object) -> Decimal | None:
    try:
        return Decimal(str(value))
    except InvalidOperation:
        return None


def _payments(cap: str, writers: list[dict[str, frozenset]]) -> str:
    s = read_scope(cap)
    payees = [_constants(_field(w, "recipient")) for w in writers]
    amounts = [_constants(_field(w, "amount")) for w in writers]
    narrower = False
    payee_part = "[" + ", ".join([*(f"'{p}'" for p in s.payees), *s.dynamic]) + "]"
    if writers and all(p is not None and len(set(p)) == 1 for p in payees):
        named = {str(p[0]) for p in payees if p}
        admitted = "any" in s.dynamic or named <= set(s.payees)
        if len(named) == 1 and admitted and (s.dynamic or len(s.payees) > 1):
            payee_part, narrower = f"['{named.pop()}']", True
    cap_part = f"'{s.cap}'" if s.cap is not None else "uncapped"
    if writers and all(a is not None for a in amounts):
        found = [_amount(v) for a in amounts for v in a]  # type: ignore[union-attr]
        if found and all(f is not None for f in found):
            top = max(found)  # type: ignore[type-var]
            if s.cap is None or top < Decimal(s.cap):  # type: ignore[operator]
                cap_part, narrower = f"'{top:.2f}'", True
    if not narrower:  # never a re-spelling: the grant as written, or a narrower one
        return cap
    tail = ", recurring" if s.recurring else ""
    return f"Payments<{payee_part}, {cap_part}{tail}>"


def _fields_kind(cap: str, writers: list[dict[str, frozenset]]) -> str:
    s = read_scope(cap)
    used = [f for f in s.fields if any(_field(w, f) for w in writers)]
    if not used or len(used) == len(s.fields):  # nothing to narrow, or it changes nothing
        return cap
    if s.kind == "ScheduledPayments":
        orders = ", ".join(f"'{o}'" for o in s.orders)
        return f"ScheduledPayments<[{orders}], [{', '.join(used)}]>"
    return f"UserProfile<[{', '.join(used)}]>"


def narrowed(graph: dict, cap: str) -> tuple[str | None, str]:
    """The narrowest form of `cap` the graph exercises (None: drop it), and why."""
    holders = [n for n in graph["nodes"] if cap in n["inputs"]]
    if not holders:
        return None, "held by no node"
    if any(n["uses"] == "Custom" for n in holders):
        return cap, "a Custom node holds it: its code is not read"
    kind = read_scope(cap).kind
    if kind not in ("Payments", "ScheduledPayments", "UserProfile"):
        return cap, "not an effect grant"
    prov = provenance(graph)
    writers = [_writer_values(graph, n["name"], prov) for n in holders
               if SLICE_CATALOGUE[n["uses"]].family == WRITER]  # fmt: skip
    if kind == "Payments":
        return _payments(cap, writers), "payee and cap from the constants sent"
    return _fields_kind(cap, writers), "fields the graph sets"


def _rename(graph: dict, old: str, new: str | None) -> None:
    def swap(items: list[str]) -> list[str]:
        return [x for x in (new if i == old else i for i in items) if x is not None]

    graph["capabilities"] = list(dict.fromkeys(swap(graph["capabilities"])))
    graph["parameters"] = list(dict.fromkeys(swap(graph["parameters"])))
    for n in graph["nodes"]:
        n["inputs"] = swap(n["inputs"])
        because = n.get("because")
        if isinstance(because, dict) and old in because:
            quote = because.pop(old)
            if new is not None:
                because[new] = quote


def minimise(graph: dict) -> tuple[dict, list[dict]]:
    """The narrowed graph, and per grant: the grant, its narrowed form, and why."""
    out = copy.deepcopy(graph)
    report = []
    for cap in list(graph["capabilities"]):
        new, why = narrowed(graph, cap)
        report.append({"grant": cap, "narrowed": new, "changed": new != cap, "why": why})
        if new != cap:
            _rename(out, cap, new)
    return out, report
