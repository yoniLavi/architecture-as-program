"""The validator's structural checks on a `bind` (value-bound grants, tasks 1.1 and 1.2).

A bind narrows a grant a node holds to values read from its data inputs. The
validator checks structure only — a held grant of a bindable kind, data-input
paths in range, a positive `uses` — and labels each bind `trusted` or
`untrusted` from what its paths read. Field types are the library's check
(`tests/test_agentdojo_library.py`, `poc/agentdojo/library.py`).
"""

from __future__ import annotations

import copy

import pytest
from graph_validator import BINDABLE, bind_label, bind_labels

from poc.graph import validate_graph_dict

PAY = "Payments<[any], '2000'>"
BILL = "Untrusted<FileText>"


def _graph(bind: object, *, data: str = "Bill", holds: str = PAY, caps: tuple = (PAY,)) -> dict:
    """Start → PayBill (holds `holds`, binds `bind`). `data` is PayBill's input."""
    return {
        "name": "BindProbe",
        "parameters": ["Bill", *caps],
        "capabilities": list(caps),
        "nodes": [
            {"name": "Start", "inputs": ["Bill"], "output": data},
            {
                "name": "PayBill",
                "inputs": [data, holds],
                "output": "Untrusted<Receipt>" if "Untrusted" in data else "Receipt",
                "bind": bind,
            },
        ],
        "data_edges": [{"from": "Start", "to": "PayBill"}],
    }


def _errors(graph: dict) -> list[str]:
    return validate_graph_dict(graph)


def test_a_well_formed_bind_validates():
    g = _graph({PAY: {"payee": "in0.iban", "amount": "in0.total", "uses": 1}})
    assert _errors(g) == []


def test_a_graph_without_a_bind_is_unaffected():
    g = _graph({})
    del g["nodes"][1]["bind"]
    assert _errors(g) == []


def test_a_bind_on_an_ungranted_capability_fails_naming_node_and_bind():
    other = "Payments<[any], uncapped>"
    errs = _errors(_graph({other: {"payee": "in0.iban", "uses": 1}}))
    assert any("'PayBill'" in e and other in e and "holds no such grant" in e for e in errs)


def test_a_bind_on_a_kind_that_is_not_bindable_fails():
    db = "DBHandle<'transactions', read>"
    g = _graph({db: {"uses": 1}}, holds=db, caps=(db,))
    errs = _errors(g)
    assert any("not a bindable kind" in e for e in errs), errs
    assert set(BINDABLE) == {"Payments"}


def test_a_path_into_a_capability_fails():
    # Input 1 of PayBill is its Payments handle; a bind reads data, never a capability.
    errs = _errors(_graph({PAY: {"payee": "in1", "uses": 1}}))
    assert any("never a capability" in e for e in errs), errs


def test_a_path_out_of_range_fails():
    errs = _errors(_graph({PAY: {"amount": "in3.total", "uses": 1}}))
    assert any("names data input 3" in e for e in errs), errs


def test_a_malformed_path_fails():
    errs = _errors(_graph({PAY: {"payee": "bill.iban", "uses": 1}}))
    assert any("not of the form inN.field" in e for e in errs), errs


@pytest.mark.parametrize("uses", [0, -1, 1.5, True, "1", None])
def test_uses_must_be_a_positive_integer(uses):
    spec: dict = {"payee": "in0.iban"}
    if uses is not None:
        spec["uses"] = uses
    errs = _errors(_graph({PAY: spec}))
    assert any("`uses` must be a positive integer" in e for e in errs), errs


def test_an_unknown_bind_field_fails():
    errs = _errors(_graph({PAY: {"recipient": "in0.iban", "uses": 1}}))
    assert any("unknown fields ['recipient']" in e for e in errs), errs


def test_an_empty_or_non_object_bind_fails():
    assert any("non-empty object" in e for e in _errors(_graph({})))
    assert any("non-empty object" in e for e in _errors(_graph(["x"])))


def test_a_payee_only_bind_is_expressible():
    assert _errors(_graph({PAY: {"payee": "in0.iban", "uses": 1}})) == []


# ── Trust labels (task 1.2) ─────────────────────────────────────────


def test_an_untrusted_payee_is_accepted_and_labelled():
    g = _graph({PAY: {"payee": "in0.iban", "amount": "in0.total", "uses": 1}}, data=BILL)
    assert _errors(g) == []
    assert bind_labels(g["nodes"][1], g["capabilities"]) == {PAY: "untrusted"}


def test_a_trusted_input_labels_the_bind_trusted():
    g = _graph({PAY: {"payee": "in0.iban", "uses": 1}})
    assert bind_labels(g["nodes"][1], g["capabilities"]) == {PAY: "trusted"}


def test_a_false_trusted_claim_fails_naming_the_bind_and_the_input():
    g = _graph({PAY: {"amount": "in0.total", "uses": 1, "trusted": True}}, data=BILL)
    errs = _errors(g)
    assert any(
        "claims `trusted`" in e and PAY in e and BILL in e and "amount=in0.total" in e for e in errs
    ), errs


def test_a_true_trusted_claim_passes():
    g = _graph({PAY: {"payee": "in0.iban", "uses": 1, "trusted": True}})
    assert _errors(g) == []


def test_a_sum_input_with_one_untrusted_variant_is_labelled_untrusted():
    data = "found: Untrusted<Bill> | none: Missing"
    node = {"name": "N", "inputs": [data, PAY], "output": "Receipt"}
    assert bind_label(node, [PAY], {"payee": "in0.iban", "uses": 1}) == "untrusted"
    assert bind_label(node, [PAY], {"uses": 1}) == "trusted"  # reads nothing


def test_a_bind_reading_two_inputs_takes_the_least_trusted():
    node = {"name": "N", "inputs": ["Order", BILL, PAY], "output": "Receipt"}
    spec = {"payee": "in0.iban", "amount": "in1.total", "uses": 1}
    assert bind_label(node, [PAY], spec) == "untrusted"
    assert bind_label(node, [PAY], {**spec, "amount": "in0.total"}) == "trusted"


def test_the_canonical_graphs_still_validate():
    from pathlib import Path

    from graph_validator import validate_files

    files = [p for p in sorted(Path("graphs").glob("*.json")) if p.name != "schema.json"]
    assert validate_files(files) == []


def test_validation_does_not_mutate_the_bind():
    g = _graph({PAY: {"payee": "in0.iban", "amount": "in0.total", "uses": 1}}, data=BILL)
    before = copy.deepcopy(g)
    _errors(g)
    assert g == before
