"""Stage one of the architect: the abstract graph's schema (task 1.1). Stdlib-only."""

from __future__ import annotations

import json

import pytest

from poc.architect import abstract
from poc.architect.abstract import (
    BAD_NAME,
    CYCLE,
    DUPLICATE,
    NOT_JSON,
    SHAPE,
    STAGE_ONE_CLASSES,
    UNKNOWN_NODE,
)

GOOD = {
    "nodes": [
        {"name": "ReadBill", "role": "read the bill the user names"},
        {"name": "PayBill", "role": "pay the amount the bill states"},
    ],
    "edges": [{"from": "ReadBill", "to": "PayBill", "carries": "the payee and the amount"}],
}


def classes(reasons) -> set[str]:
    return {r.cls for r in reasons}


def test_a_good_graph_parses_from_a_fenced_reply():
    reply = f"Here it is:\n```json\n{json.dumps(GOOD)}\n```"
    graph, reasons = abstract.parse(reply)
    assert reasons == [] and graph == GOOD


@pytest.mark.parametrize(
    ("mutate", "cls"),
    [
        (lambda g: g["nodes"][0].update(name="read_bill"), BAD_NAME),
        (lambda g: g["nodes"][1].update(name="ReadBill"), DUPLICATE),
        (lambda g: g["edges"][0].update(to="Nowhere"), UNKNOWN_NODE),
        (lambda g: g["edges"].append({"from": "PayBill", "to": "ReadBill", "carries": "x"}), CYCLE),
        (lambda g: g["nodes"][0].update(capability="Payments"), SHAPE),
        (lambda g: g.update(capabilities=[]), SHAPE),
        (lambda g: g["edges"][0].pop("carries"), SHAPE),
        (lambda g: g.update(nodes=[]), SHAPE),
    ],
)
def test_each_schema_failure_has_its_class(mutate, cls):
    g = json.loads(json.dumps(GOOD))
    mutate(g)
    graph, reasons = abstract.parse(json.dumps(g))
    assert graph is None
    assert cls in classes(reasons)
    assert classes(reasons) <= set(STAGE_ONE_CLASSES)


@pytest.mark.parametrize("reply", ["no json here", "{not: json}"])
def test_a_reply_that_is_not_json(reply):
    assert classes(abstract.parse(reply)[1]) == {NOT_JSON}


def test_the_stage_one_prompt_names_no_capability_kind():
    # The point of stage one: it is never told what kinds exist.
    from type_parser import CAPABILITY_HEADS

    from poc.agentdojo.library import CATALOGUE

    shown = abstract.STAGE_ONE_SYSTEM + abstract.prompt("Pay my bill.")
    for kind in CAPABILITY_HEADS:
        assert kind not in shown
    for entry in CATALOGUE:
        assert entry not in shown, entry


def test_channel_b_adds_the_document_and_nothing_else():
    plain = abstract.prompt("Pay my bill.")
    with_doc = abstract.prompt("Pay my bill.", document="DOC TEXT")
    assert with_doc.startswith(plain) and "DOC TEXT" in with_doc
