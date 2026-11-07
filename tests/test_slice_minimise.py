"""Crude minimisation (`add-vertical-slice`, task 4.1). Stdlib-only; calls no model."""

from __future__ import annotations

from poc.agentdojo.library import SLICE_CATALOGUE
from poc.architect import verdicts
from poc.slice import control
from poc.slice.minimise import minimise, narrowed
from poc.slice.replay import trials

IBAN = "UK12345678901234567890"


def _pay(fields: dict, grant: str, *, recurring: bool = False) -> dict:
    writer = "ScheduleTransaction" if recurring else "SendMoney"
    record = "StandingOrder" if recurring else "PaymentOrder"
    return {
        "name": "G", "parameters": ["TaskRequest", grant], "capabilities": [grant],
        "nodes": [
            {"name": "Start", "uses": "Start", "inputs": ["TaskRequest"], "output": "TaskRequest"},
            {"name": "Make", "uses": "Compose", "params": {"fields": fields},
             "inputs": ["TaskRequest"], "output": record},
            {"name": "Pay", "uses": writer, "inputs": [record, grant], "output": "Receipt"},
        ],
        "data_edges": [{"from": "Start", "to": "Make"}, {"from": "Make", "to": "Pay"}],
    }  # fmt: skip


ORDER = {"recipient": IBAN, "amount": 98.7, "subject": "Bill", "date": "2022-04-01"}


def test_constant_payee_and_amount_narrow_an_open_grant():
    assert narrowed(_pay(ORDER, "Payments<[any], uncapped>"), "Payments<[any], uncapped>")[0] == (
        f"Payments<['{IBAN}'], '98.70'>"
    )


def test_a_computed_payee_or_amount_is_left_open():
    grant = "Payments<[any], uncapped>"
    computed = {**ORDER, "recipient": "=in0.prompt", "amount": "=in0.prompt"}
    assert narrowed(_pay(computed, grant), grant)[0] == grant


def test_a_grant_already_as_narrow_is_unchanged_never_respelt():
    grant = f"Payments<['{IBAN}'], '98.70'>"
    assert narrowed(_pay(ORDER, grant), grant)[0] == grant
    quoted = "Payments<['any'], uncapped>"  # the registered records' spelling
    computed = {**ORDER, "recipient": "=in0.prompt", "amount": "=in0.prompt"}
    assert narrowed(_pay(computed, quoted), quoted)[0] == quoted


def test_fields_narrow_to_those_the_graph_sets():
    grant = "ScheduledPayments<['Rent'], [amount, date]>"
    g = _pay({"id": 7, "amount": 1100}, grant)
    g["nodes"][1]["output"], g["nodes"][2]["uses"] = "OrderUpdate", "UpdateScheduledTransaction"
    g["nodes"][2]["inputs"] = ["OrderUpdate", grant]
    out, report = minimise(g)
    assert report[0]["narrowed"] == "ScheduledPayments<['Rent'], [amount]>"
    assert out["capabilities"] == ["ScheduledPayments<['Rent'], [amount]>"]
    assert out["nodes"][2]["inputs"][1] == out["capabilities"][0]


def test_a_custom_node_is_not_narrowed_and_an_unheld_grant_is_dropped():
    g = control.graph()
    node = next(n for n in g["nodes"] if n["name"] == control.NODE)
    node["inputs"].append("Payments<[any], uncapped>")
    assert narrowed(g, "Payments<[any], uncapped>")[1].startswith("a Custom node holds it")
    g["capabilities"].append("DBHandle<'balance', read>")
    out, report = minimise(g)
    assert report[-1] == {"grant": "DBHandle<'balance', read>", "narrowed": None,
                          "changed": True, "why": "held by no node"}  # fmt: skip
    assert "DBHandle<'balance', read>" not in out["capabilities"]


def test_the_narrowed_graph_still_validates():
    out, _ = minimise(control.graph())
    assert verdicts.check(out, SLICE_CATALOGUE) == []


def test_over_the_registered_graphs_it_narrows_nothing():
    """The finding (task 4.1): 0 of 1,134 grants in the 305 registered graphs. Their
    wide grants are wide where the graph computes the value, which no constant reaches."""
    rows = [minimise(r["architect"]["graph"])[1] for r in trials()]
    assert (len(rows), sum(map(len, rows))) == (305, 1134)
    assert sum(x["changed"] for row in rows for x in row) == 0
