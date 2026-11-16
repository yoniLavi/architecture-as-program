"""The node library's check of a bind's field types, and where `bind` is offered
(value-bound grants, task 1.3).

The validator knows types by name; the library knows the record schemas, so it
checks that each bound path names a field of the right type: a payee a string, an
amount a number. `bind` is offered in the slice's catalogue text only: the
registered architect run hashed `CATALOGUE`'s, which must not move.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

from poc.agentdojo.library import CATALOGUE, SLICE_CATALOGUE, check_graph
from poc.architect import mapping, registration
from poc.graph import validate_graph_dicts

GRAPHS = Path(__file__).resolve().parent.parent / "poc" / "agentdojo" / "graphs"
PAY = "Payments<[any], uncapped>"


def task0(bind: dict | None) -> dict:
    """Banking task 0's oracle graph, its `SendMoney` bound by `bind`."""
    g = json.loads((GRAPHS / "banking-user-task-0.json").read_text())
    if bind is not None:
        next(n for n in g["nodes"] if n["name"] == "PayBill")["bind"] = {PAY: bind}
    return g


def test_a_well_typed_bind_passes_both_checks():
    g = task0({"payee": "in0.recipient", "amount": "in0.amount", "uses": 1})
    assert validate_graph_dicts([g]) == []
    assert check_graph(g, SLICE_CATALOGUE) == []


def test_a_payee_bound_to_a_number_fails_naming_the_field():
    g = task0({"payee": "in0.amount", "uses": 1})
    errors = check_graph(g, SLICE_CATALOGUE)
    assert any("payee path 'in0.amount'" in e and "'amount', a number" in e for e in errors), errors


def test_an_amount_bound_to_a_string_fails():
    errors = check_graph(task0({"amount": "in0.subject", "uses": 1}), SLICE_CATALOGUE)
    assert any("an amount must be a number" in e for e in errors), errors


def test_a_field_the_record_lacks_fails():
    errors = check_graph(task0({"payee": "in0.iban", "uses": 1}), SLICE_CATALOGUE)
    assert any("'iban', which the input lacks" in e for e in errors), errors


def test_a_path_to_the_whole_record_or_into_a_field_fails():
    assert any("whole record" in e for e in check_graph(task0({"payee": "in0", "uses": 1})))
    assert any(
        "not a record" in e for e in check_graph(task0({"payee": "in0.recipient.x", "uses": 1}))
    )


def test_an_extract_record_outside_records_is_known_by_its_fields():
    g = task0(None)
    extract = next(n for n in g["nodes"] if n["name"] == "ExtractInvoice")
    extract["output"] = "Invoice"
    extract["params"]["fields"] = {"iban": "string", "total": "number"}
    custom = {
        "name": "PayBill",
        "uses": "Custom",
        "params": {"role": "Pay the invoice.", "fields": {"result": "string"}},
        "inputs": ["Invoice", PAY],
        "output": "Receipt",
        "bind": {PAY: {"payee": "in0.iban", "amount": "in0.total", "uses": 1}},
    }
    g["nodes"] = [custom if n["name"] == "PayBill" else n for n in g["nodes"]]
    assert check_graph(g, SLICE_CATALOGUE) == []
    wrong = copy.deepcopy(g)
    wrong["nodes"][3]["bind"][PAY]["payee"] = "in0.total"
    assert any("'total', a number" in e for e in check_graph(wrong, SLICE_CATALOGUE))


def test_bind_is_offered_in_the_slice_text_only():
    assert mapping.BIND_NOTE not in mapping.system()
    assert mapping.BIND_NOTE in mapping.system(SLICE_CATALOGUE)
    assert not any(e.bindable for e in CATALOGUE.values())
    assert {n for n, e in SLICE_CATALOGUE.items() if e.bindable} == {
        "SendMoney",
        "ScheduleTransaction",
        "Custom",
    }


def test_the_registered_architect_text_is_unchanged():
    registered = json.loads(registration.REGISTRATION_PATH.read_text())
    assert registration.task_hashes() == registered["task_sha256"]
