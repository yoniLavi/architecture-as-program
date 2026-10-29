"""The exclusive-branch merge (Paper 4's AgentDojo harness, task 2.3).

A node declaring `merge: true` may take several edges at one input position when
every pair is exclusive, so exactly one value arrives. The validator proves the
exclusivity; the runtime needs nothing new, because it already refuses a second
arrival. The corpus pins the two verdicts (`test_banking_kinds.py`); this file
runs the accepted shape on both branches and checks the marker's own misuse."""

from __future__ import annotations

import pytest

from poc.agentdojo.corpus import lookup_graph
from poc.bank import MemoryBank
from poc.graph import assemble, validate_graph_dicts
from poc.handles import World
from poc.llm import StubLLM
from poc.nodes import REGISTRY
from poc.runtime import execute
from poc.values import Variant

FRIEND = "GB29NWBK60161331926819"


@pytest.fixture
def impls(monkeypatch):
    def find(request):
        if request == "refund":
            return Variant("found", {"recipient": FRIEND, "amount": 10.0})
        return Variant("none", "nothing to refund")

    def send(order, payments):
        payments.send(order["recipient"], order["amount"], "Refund", "2022-04-01")
        return "sent"

    for name, impl in {
        "Start": lambda r: r,
        "FindRefund": find,
        "SendRefund": send,
        "SkipRefund": lambda _none: "skipped",
        "Acknowledge": lambda _r: "ack",
        "Report": lambda ack, outcome: f"{ack}:{outcome}",
    }.items():
        monkeypatch.setitem(REGISTRY, name, impl)


@pytest.mark.parametrize(("request_", "reply"), [("refund", "ack:sent"), ("other", "ack:skipped")])
def test_a_merge_runs_once_on_whichever_branch_fired(impls, request_, reply):
    bank = MemoryBank(
        transactions=[
            {
                "id": 5,
                "sender": FRIEND,
                "recipient": "me",
                "amount": 10.0,
                "subject": "Sushi",
                "date": "2022-03-07",
                "recurring": False,
            }
        ]
    )
    graph = assemble(lookup_graph(), backend=StubLLM(), world=World(bank=bank))
    result = execute(graph, request_)
    assert result.terminals == {"Report": reply}
    assert result.order.count("Report") == 1
    assert len(bank.writes) == (1 if reply.endswith("sent") else 0)


def test_without_the_marker_the_join_rule_still_holds():
    graph = lookup_graph()
    del graph["nodes"][-1]["merge"]
    errors = validate_graph_dicts([graph])
    assert any("each position of a join takes exactly one" in e for e in errors), errors


def test_a_marker_with_nothing_to_merge_is_rejected():
    graph = lookup_graph()
    graph["nodes"][2]["merge"] = True  # SendRefund: one edge in
    errors = validate_graph_dicts([graph])
    assert any("a merge with one source merges nothing" in e for e in errors), errors
