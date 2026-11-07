"""The vertical slice's custom node (`add-vertical-slice`, task 1.1): a library entry
with a role, a signature and a clause, and no body.

It is a new route to authority, so it lives in `SLICE_CATALOGUE` only. The registered
architect run hashed the catalogue it was shown; the first test holds that text
reproducible from the working tree, so adding the entry cannot drift it."""

from __future__ import annotations

import copy
import json

import pytest

from poc.agentdojo.library import (
    CATALOGUE,
    RECORDS,
    SLICE_CATALOGUE,
    check_graph,
    custom_schema,
)
from poc.architect import mapping, registration, verdicts
from poc.slice import control


def test_the_registered_architect_text_is_reproducible():
    registered = json.loads(registration.REGISTRATION_PATH.read_text())
    assert registration.task_hashes() == registered["task_sha256"]


def test_custom_is_in_the_slice_catalogue_only():
    assert "Custom" not in CATALOGUE
    assert set(SLICE_CATALOGUE) == {*CATALOGUE, "Custom"}
    assert "`Custom`" not in mapping.system()
    shown = mapping.system(SLICE_CATALOGUE)
    assert "- `Custom`: A node a developer writes" in shown
    assert "Use it only then." in shown


def custom_graph() -> dict:
    """Task 0's oracle graph with its `Extract` replaced by a custom node and a `Compose`:
    the developer step's control graph (`poc/slice/control`)."""
    return control.graph()


def test_a_custom_graph_passes_the_validator_and_the_slice_library():
    assert verdicts.check(custom_graph(), SLICE_CATALOGUE) == []


def test_the_registered_library_refuses_a_custom_node():
    assert check_graph(custom_graph()) == [
        "node 'ParseBill' uses 'Custom', which is not in the library"
    ]


def _custom(**change) -> dict:
    g = copy.deepcopy(custom_graph())
    node = next(n for n in g["nodes"] if n["name"] == "ParseBill")
    for key, value in change.items():
        if value is None:
            node.pop(key, None)
        else:
            node[key] = value
    for cap in node["inputs"][1:]:
        if cap not in g["capabilities"]:
            g["capabilities"].append(cap)
    return g


def _problems(**change) -> list[str]:
    return check_graph(_custom(**change), SLICE_CATALOGUE)


@pytest.mark.parametrize(
    ("held", "expected"),
    [
        ("ResponseChannel<user-session>", "may hold only"),
        ("Credentials", "may hold only"),
        ("DBHandle<'transactions', read-write>", "a reader's DBHandle"),
        ("DBHandle<'passwords', read>", "a reader's DBHandle"),
        ("LLMClient<[send_money]>", "LLMClient<inference> only"),
    ],
)
def test_each_grant_obeys_its_entry_rule(held, expected):
    problems = _problems(inputs=["Untrusted<FileText>", held])
    assert any(expected in p for p in problems), problems


def test_the_grantable_kinds_pass():
    held = [
        "DBHandle<'transactions', read>",
        "DBHandle<'file:landlord-notices.txt', read>",
        "LLMClient<inference>",
        "Payments<['GB29NWBK60161331926819'], '100.00'>",
        "ScheduledPayments<['Rent'], [amount]>",
        "UserProfile<[street]>",
    ]
    assert _problems(inputs=["Untrusted<FileText>", *held]) == []


@pytest.mark.parametrize(
    ("change", "expected"),
    [
        ({"params": {"fields": {"iban": "string"}}}, "needs a `role`"),
        ({"params": {"role": "x"}}, "non-empty `fields`"),
        ({"params": {"role": "x", "fields": {"iban": "bytes"}}}, "field types"),
        ({"output": "found: Untrusted<Bill> | none: Untrusted<NoMatch>"}, "one named record"),
        ({"output": "Bill"}, "must be Untrusted"),
        ({"discharges_trust": True}, "may not discharge trust"),
    ],
)
def test_parameters_and_labels(change, expected):
    problems = _problems(**change)
    assert any(expected in p for p in problems), problems


def test_reading_the_bank_labels_the_output_even_from_trusted_input():
    g = _custom(inputs=["Untrusted<FileText>", "DBHandle<'balance', read>"], output="Bill")
    node = next(n for n in g["nodes"] if n["name"] == "ParseBill")
    node["inputs"][0] = "TaskRequest"
    assert any("must be Untrusted" in p for p in check_graph(g, SLICE_CATALOGUE))


def test_a_writers_record_needs_no_fields_and_is_the_schema():
    g = _custom(output="Untrusted<PaymentOrder>", params={"role": "x"})
    node = next(n for n in g["nodes"] if n["name"] == "ParseBill")
    assert check_graph(g, SLICE_CATALOGUE) == []  # per node: the edges are the validator's
    assert custom_schema(node) == RECORDS["PaymentOrder"]
    node["params"]["fields"] = {"recipient": "string"}
    assert any("omit `fields`" in p for p in check_graph(g, SLICE_CATALOGUE))
    assert custom_schema(_custom()["nodes"][2]) == {"iban": "string", "amount": "number"}
