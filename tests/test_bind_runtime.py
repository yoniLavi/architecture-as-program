"""A bind enforced at node activation (value-bound grants, task 2.2).

Before a binding node runs, the runtime resolves the bind's paths against that
activation's inputs and hands the node a handle narrowed to the bound values. A
path that does not resolve, or resolves to a value of the wrong type, fails the run
before the node runs, and nothing falls back to the grant's static bound. Every
activation gets its own facade: under a per-item map, one per item.

Host tier here: the body is plain Python, and the facade is host discipline, as
every host-tier handle is. The confined tier is `tests/test_bind_confined.py`.
"""

from __future__ import annotations

import copy

import pytest

from poc.bank import MemoryBank
from poc.graph import assemble, validate_graph_dicts
from poc.handles import CapabilityError, World
from poc.llm import StubLLM
from poc.nodes import REGISTRY
from poc.runtime import ExecutionError, execute

PAY = "Payments<[any], '2000'>"
BILL = {"iban": "GB1", "total": 120.0}


def _graph(bind: dict | None = None) -> dict:
    node = {"name": "PayBill", "inputs": ["Bill", PAY], "output": "Receipt"}
    if bind is not None:
        node["bind"] = {PAY: bind}
    return {
        "name": "BindRun",
        "parameters": ["Bill", PAY],
        "capabilities": [PAY],
        "nodes": [node],
        "data_edges": [],
    }


BOUND = {"payee": "in0.iban", "amount": "in0.total", "uses": 1}


def _run(graph: dict, body, value=BILL, bank: MemoryBank | None = None):
    bank = bank if bank is not None else MemoryBank()
    assembled = assemble(graph, backend=StubLLM(), world=World(bank=bank))
    result = execute(assembled, value, impls={"PayBill": body})
    return result, bank


def test_the_bound_payment_is_made():
    result, bank = _run(_graph(BOUND), lambda bill, pay: pay.send("GB1", 120.0, "bill", "d"))
    assert [w[1]["recipient"] for w in bank.writes] == ["GB1"]
    assert "PayBill" in result.terminals


def test_another_payee_an_amount_over_the_bound_and_a_second_payment_are_refused():
    refusals: list[str] = []

    def body(bill, pay):
        for reach in (
            lambda: pay.send("GB2", 1.0, "x", "d"),
            lambda: pay.send("GB1", 121.0, "x", "d"),
        ):
            with pytest.raises(CapabilityError) as e:
                reach()
            refusals.append(str(e.value))
        pay.send("GB1", 120.0, "bill", "d")
        with pytest.raises(CapabilityError, match="spent"):
            pay.send("GB1", 120.0, "again", "d")
        return {"result": "paid"}

    _, bank = _run(_graph(BOUND), body)
    assert len(refusals) == 2 and len(bank.writes) == 1


def test_without_a_bind_the_static_grant_is_unchanged():
    def body(bill, pay):
        pay.send("GB2", 5.0, "a", "d")
        pay.send("GB3", 5.0, "b", "d")

    _, bank = _run(_graph(None), body)
    assert len(bank.writes) == 2


def test_each_activation_gets_its_own_count():
    graph = _graph(BOUND)
    calls = []

    def body(bill, pay):
        calls.append(pay.uses_left)
        pay.send(bill["iban"], bill["total"], "bill", "d")

    bank = MemoryBank()
    _run(graph, body, bank=bank)
    _run(graph, body, value={"iban": "GB9", "total": 5.0}, bank=bank)
    assert calls == [1, 1]
    assert [w[1]["recipient"] for w in bank.writes] == ["GB1", "GB9"]


@pytest.mark.parametrize(
    ("value", "match"),
    [
        ({"total": 120.0}, "no field 'iban'"),
        ({"iban": 7, "total": 120.0}, "payee must be a non-empty string"),
        ({"iban": "GB1", "total": "120"}, "amount must be a positive number"),
        ({"iban": "GB1", "total": 0}, "amount must be a positive number"),
        ("not a record", "no field 'iban'"),
    ],
)
def test_an_unresolvable_bind_fails_the_run_before_the_node_runs(value, match):
    ran = []
    bank = MemoryBank()
    with pytest.raises(ExecutionError, match=match):
        _run(_graph(BOUND), lambda bill, pay: ran.append(pay), value=value, bank=bank)
    assert ran == [] and bank.writes == []


def test_the_trace_records_the_bound_crossing_as_the_unbound_one():
    from poc.sandbox.interfaces import interface_for

    bound, _ = _run(_graph(BOUND), lambda bill, pay: pay.send("GB1", 1.0, "bill", "d"))
    plain, _ = _run(_graph(None), lambda bill, pay: pay.send("GB1", 1.0, "bill", "d"))
    (node,) = bound.trace.nodes
    assert [(c.interface, c.operation) for c in node.calls] == [(interface_for(PAY), "send")]
    assert node.crossings == plain.trace.nodes[0].crossings


# ── Under a per-item map ─────────────────────────────────────────────

CHILD = {
    "name": "PayEach",
    "parameters": ["Bill", PAY],
    "capabilities": [PAY],
    "nodes": [
        {
            "name": "PayOne",
            "inputs": ["Bill", PAY],
            "output": "Receipt",
            "bind": {PAY: dict(BOUND)},
        }
    ],
    "data_edges": [],
}

PARENT = {
    "name": "PayAll",
    "parameters": ["Bills", PAY],
    "capabilities": [PAY],
    "nodes": [
        {"name": "Gather", "inputs": ["Bills"], "output": "List<Bill>"},
        {"name": "PayEach", "inputs": ["List<Bill>", PAY], "output": "List<Receipt>", "each": True},
    ],
    "data_edges": [{"from": "Gather", "to": "PayEach"}],
}


def _run_each(parent: dict, child: dict, bills: list[dict], body) -> MemoryBank:
    assert validate_graph_dicts([parent, child]) == []
    bank = MemoryBank()
    assembled = assemble(parent, backend=StubLLM(), world=World(bank=bank))
    old = dict(REGISTRY)
    REGISTRY["PayOne"] = body
    REGISTRY["Gather"] = lambda bills: list(bills)
    try:
        execute(assembled, bills, graphs={"PayEach": child})
    finally:
        REGISTRY.clear()
        REGISTRY.update(old)
    return bank


BILLS = [{"iban": "GB1", "total": 10.0}, {"iban": "GB2", "total": 20.0}]


def test_under_a_per_item_map_each_item_has_its_own_facade_and_count():
    seen = []

    def body(bill, pay):
        seen.append(pay.uses_left)
        pay.send(bill["iban"], bill["total"], "bill", "d")
        with pytest.raises(CapabilityError):
            pay.send(bill["iban"], bill["total"], "again", "d")
        # Another item's payee is outside this item's bound.
        other = "GB2" if bill["iban"] == "GB1" else "GB1"
        with pytest.raises(CapabilityError):
            pay.send(other, 1.0, "x", "d")
        return {"result": "ok"}

    bank = _run_each(PARENT, CHILD, BILLS, body)
    assert seen == [1, 1]
    assert [(w[1]["recipient"], w[1]["amount"]) for w in bank.writes] == [
        ("GB1", 10.0),
        ("GB2", 20.0),
    ]


def test_a_bind_on_the_per_item_node_binds_each_child_run():
    parent = copy.deepcopy(PARENT)
    parent["nodes"][1]["bind"] = {PAY: dict(BOUND)}
    child = copy.deepcopy(CHILD)
    del child["nodes"][0]["bind"]

    def body(bill, pay):
        other = "GB2" if bill["iban"] == "GB1" else "GB1"
        with pytest.raises(CapabilityError):
            pay.send(other, 1.0, "x", "d")
        pay.send(bill["iban"], bill["total"], "bill", "d")
        with pytest.raises(CapabilityError, match="spent"):
            pay.send(bill["iban"], 1.0, "again", "d")
        return {"result": "ok"}

    bank = _run_each(parent, child, BILLS, body)
    assert [w[1]["recipient"] for w in bank.writes] == ["GB1", "GB2"]
