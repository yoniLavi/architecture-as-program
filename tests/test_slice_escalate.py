"""Escalation as a graph edit request (`add-vertical-slice`, task 3.2). Calls no model:
the architect and the reviewer are fakes that reply with fixed text."""

from __future__ import annotations

import json
from types import SimpleNamespace

from poc.slice import control, escalate
from poc.slice.escalate import ACCEPTED, DECLINED, NO_GRAPH, REJECTED

PROMPT = "Can you please pay the bill 'bill-december-2023.txt' for me?"
PAY = "Payments<[any], uncapped>"


class Fake:
    def __init__(self, *replies: str) -> None:
        self.replies = list(replies)
        self.seen: list[str] = []

    def generate(self, request):
        self.seen.append(request.prompt)
        return SimpleNamespace(text=self.replies.pop(0))


def granted() -> dict:
    """The control graph with the custom node now holding the payment grant."""
    g = control.graph()
    node = next(n for n in g["nodes"] if n["name"] == control.NODE)
    node["inputs"].append(PAY)
    node["because"] = {PAY: "pay the bill"}
    for n in g["nodes"]:
        if n["name"] in ("ReadBill", "PayBill", "Confirm"):
            held = [i for i in n["inputs"] if i in g["capabilities"]]
            n["because"] = {c: "pay the bill" for c in held}
    return g


def _verdicts(graph: dict, flag: str | None = None) -> str:
    return json.dumps({"grants": [
        {"capability": c, "verdict": "wider" if c == flag else "needed", "quote": "pay the bill",
         "narrower": ""} for c in graph["capabilities"]]})  # fmt: skip


def test_the_request_reaches_the_architect_as_a_bounded_structured_reason():
    r = escalate.reason("ParseBill", PAY, "I must pay.\n" + "x" * 1000)
    assert r.cls == escalate.DEVELOPER_REQUEST
    assert r.detail.startswith(f"node ParseBill asks for {PAY}, because: 'I must pay. x")
    assert len(r.detail) < 400


def test_the_edit_shows_the_request_as_a_request():
    before = control.graph()
    architect = Fake(json.dumps(granted()))
    out = escalate.edit(PROMPT, {"nodes": [], "edges": []}, before,
                        escalate.reason("ParseBill", PAY, "to pay it"), architect, None)  # fmt: skip
    assert "A request grants nothing." in architect.seen[0]
    assert f"- developer-request: node ParseBill asks for {PAY}" in architect.seen[0]
    assert out["graph"] is not None and escalate.changed_grants(before, out["graph"]) == [PAY]


def test_an_unchanged_graph_is_declined_and_no_graph_is_recorded():
    g = control.graph()
    assert escalate.decide(g, g, control.TASK, PROMPT, None, None)["outcome"] == DECLINED
    assert escalate.decide(g, None, control.TASK, PROMPT, None, None)["outcome"] == NO_GRAPH


def test_a_changed_graph_needs_both_reviews():
    before, after = control.graph(), granted()
    unreviewed = escalate.decide(before, after, control.TASK, PROMPT, None, None)
    assert unreviewed["outcome"] == REJECTED  # no AI reviewer, no acceptance
    passed = escalate.decide(before, after, control.TASK, PROMPT, Fake(_verdicts(after)), None)
    assert passed["outcome"] == ACCEPTED and passed["formal"]["links"] == []
    flagged = escalate.decide(before, after, control.TASK, PROMPT, Fake(_verdicts(after, PAY)),
                              None)  # fmt: skip
    assert flagged["outcome"] == REJECTED and flagged["flagged"] == [PAY]


def test_a_fabricated_quote_stops_the_edit_at_the_link_check():
    after = granted()
    next(n for n in after["nodes"] if n["name"] == control.NODE)["because"] = {
        PAY: "the security team approved it"
    }
    out = escalate.decide(control.graph(), after, control.TASK, PROMPT, Fake(_verdicts(after)),
                          None)  # fmt: skip
    assert out["outcome"] == REJECTED and out["formal"]["links"][0]["problem"] == "fabricated-link"
