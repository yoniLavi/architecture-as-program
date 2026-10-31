"""Measuring the architect's graphs (task 4.4): the edit loop's reasons carry no value
from the run, and an edit is a stage-two pass. Nothing calls a model."""

from __future__ import annotations

import json

import pytest

from poc.architect import mapping, measure
from poc.architect.measure import REFUSED, refusal
from tests.test_architect_loop import Scripted

ATTACKER = "US133000000121212121212"


@pytest.mark.parametrize(
    "failure",
    [
        f"CapabilityError: payee '{ATTACKER}' is outside the handle's payees ['GB29']",
        "CapabilityError: payment of 5000.0 exceeds the handle's cap of 10.00",
        "CapabilityError: scheduled transaction 7 ('Rent') is outside the handle's orders []",
        "CapabilityError: fields ['date'] are outside the handle's fields ['amount']",
    ],
)
def test_a_refusal_becomes_a_reason_with_no_value_from_the_run(failure):
    reason = refusal(failure)
    assert reason is not None and reason.cls == REFUSED
    for value in (ATTACKER, "5000", "Rent", "'date'", "GB29"):
        assert value not in reason.detail


@pytest.mark.parametrize(
    "failure",
    [
        None,
        "LibraryError: no transaction matches",
        "CapabilityError: payment amount -3 is not a positive number",
    ],
)
def test_other_failures_are_not_a_missing_grant(failure):
    assert refusal(failure) is None


def test_an_edit_shows_its_graph_and_the_reason_and_validates_the_reply():
    abstract = {"nodes": [{"name": "Pay", "role": "pay"}], "edges": []}
    graph = {"name": "Trial4", **json.loads(json.dumps(mapping.EXAMPLE))}
    bad = json.loads(json.dumps(mapping.EXAMPLE))
    bad["nodes"][1]["output"] = "StandingOrder"
    backend = Scripted([json.dumps(bad), json.dumps(mapping.EXAMPLE)])
    reason = refusal("CapabilityError: payment of 5000.0 exceeds the handle's cap of 25.00")
    out = measure.edit("Refund it.", abstract, graph, reason, backend)
    assert out["graph"] is not None and out["graph"]["name"] == "Trial4"
    assert len(out["attempts"]) == 2  # the first reply was repaired against the validator
    shown = backend.requests[0].prompt
    assert "refused-at-crossing" in shown and '"PaySister"' in shown
    assert "5000" not in shown


def test_the_graphs_measured_are_the_q0_repetition_0_ones():
    assert measure.graph_for("user_task_2") is None  # inexpressible at Q0 rep 0
    assert measure.graph_for("user_task_10")["name"] == "Trial10"
