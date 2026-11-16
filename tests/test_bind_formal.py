"""The two formal rules the slice showed were missing (value-bound grants, 4.1 and 4.2).

* **A developer-written node holds no unbounded writer grant.** A `Custom` node
  holding `Payments` needs literal payees and a cap, or a bind of both payee and
  amount. `ScheduledPayments` and `UserProfile` on a `Custom` node are reported, not
  failed (the author's answer, task 0.1). A library writer is outside the rule.
* **An accepted escalation grants no more than was asked.** Every grant the edit adds
  or widens must be no wider than the developer's request, and a bound request is
  met only by a bind at the same paths, with no more uses.

Both are new functions run by the slice path only; the registered review never calls
them, so `make architect` and its pins cannot move.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from poc.architect import formal
from poc.architect.formal import (
    BIND_WIDER,
    CUSTOM_WRITER,
    OPEN_WRITER,
    UNBOUND_ANSWER,
    UNPARSEABLE_REQUEST,
    WIDER_THAN_ASKED,
    custom_writers,
    no_wider,
)

SLICE = Path(__file__).resolve().parent.parent / "poc" / "slice" / "runs" / "slice"
OPEN = "Payments<[any], uncapped>"
CAPPED = "Payments<[any], '2000'>"
BOUND = {"payee": "in0.iban", "amount": "in0.total", "uses": 1}


def _custom(cap: str, bind: dict | None = None, uses: str = "Custom") -> dict:
    node = {"name": "PayBill", "uses": uses, "inputs": ["Bill", cap], "output": "Receipt"}
    if bind is not None:
        node["bind"] = {cap: bind}
    return {
        "name": "G",
        "parameters": ["Bill", cap],
        "capabilities": [cap],
        "nodes": [node],
        "data_edges": [],
    }


def _fails(graph: dict) -> list[str]:
    return [f.capability for f in custom_writers(graph) if f.fails]


# ── 4.1: the Custom-writer rule ──────────────────────────────────────


def test_an_open_grant_on_developer_code_fails_naming_node_and_grant():
    (finding,) = custom_writers(_custom(OPEN))
    assert (finding.node, finding.capability, finding.problem, finding.fails) == (
        "PayBill",
        OPEN,
        OPEN_WRITER,
        True,
    )


def test_a_bound_grant_on_developer_code_passes():
    assert custom_writers(_custom(CAPPED, BOUND)) == []
    assert custom_writers(_custom(OPEN, BOUND)) == []


@pytest.mark.parametrize(
    "bind", [{"payee": "in0.iban", "uses": 1}, {"amount": "in0.total", "uses": 1}, {"uses": 1}]
)
def test_a_bind_of_less_than_payee_and_amount_does_not_suffice(bind):
    assert _fails(_custom(CAPPED, bind)) == [CAPPED]


def test_literal_payees_and_a_cap_pass_without_a_bind():
    assert custom_writers(_custom("Payments<['GB1'], '100'>")) == []
    assert _fails(_custom("Payments<['GB1'], uncapped>")) == ["Payments<['GB1'], uncapped>"]
    assert _fails(_custom("Payments<[inbound-senders], '100'>"))


def test_the_recurring_mode_is_held_to_the_same_rule():
    assert _fails(_custom("Payments<[any], uncapped, recurring>"))


def test_a_library_writer_is_outside_the_rule():
    assert custom_writers(_custom(OPEN, uses="SendMoney")) == []


@pytest.mark.parametrize(
    "cap", ["ScheduledPayments<['rent'], [amount]>", "UserProfile<[street, city]>"]
)
def test_other_writer_kinds_on_developer_code_are_reported_not_failed(cap):
    (finding,) = custom_writers(_custom(cap))
    assert finding.problem == CUSTOM_WRITER and finding.fails is False


def test_replayed_over_the_slice_d2s_final_graph_fails_and_no_other_unit_does():
    failing: dict[str, list[str]] = {}
    units = 0
    for path in sorted(SLICE.glob("*.json")):
        record = json.loads(path.read_text())
        graph = record.get("final_graph")
        if not isinstance(graph, dict):
            continue
        units += 1
        found = _fails(graph)
        if found:
            failing[record["unit"]] = found
    assert units >= 2
    assert failing == {"user_task_0.D2": [OPEN]}


def test_d1_is_not_caught_its_writer_is_the_librarys():
    """D1's developer-written node is the extractor; a library `SendMoney` holds the
    open grant. The rule does not apply, and that is the limit 5.1 pins."""
    d1 = json.loads((SLICE / "user_task_0.D1.json").read_text())["final_graph"]
    assert custom_writers(d1) == []
    send = [n for n in d1["nodes"] if n["uses"] == "SendMoney"]
    assert send and OPEN in send[0]["inputs"]


def test_the_registered_review_does_not_call_the_rule():
    import inspect

    from poc.architect import run, trial

    for module in (run, trial):
        assert "custom_writers" not in inspect.getsource(module)
        assert "no_wider" not in inspect.getsource(module)


# ── 4.2: the no-wider check ──────────────────────────────────────────


def _edit(cap: str, bind: dict | None = None) -> tuple[dict, dict]:
    before = _custom(cap)
    before["nodes"][0]["inputs"] = ["Bill"]
    before["parameters"], before["capabilities"] = ["Bill"], []
    return before, _custom(cap, bind)


def test_a_wider_answer_fails():
    before, after = _edit(OPEN)
    request = {"capability": CAPPED, "bind": BOUND, "because": "pay the bill"}
    (f,) = no_wider(before, after, "PayBill", request)
    assert f.problem == WIDER_THAN_ASKED and f.capability == OPEN


def test_an_exact_answer_passes():
    before, after = _edit(CAPPED, BOUND)
    request = {"capability": CAPPED, "bind": dict(BOUND), "because": "pay the bill"}
    assert no_wider(before, after, "PayBill", request) == []


def test_a_narrower_answer_passes():
    before, after = _edit("Payments<[any], '500'>", BOUND)
    assert no_wider(before, after, "PayBill", {"capability": CAPPED, "bind": BOUND}) == []


def test_an_unbound_answer_to_a_bound_request_fails():
    before, after = _edit(CAPPED)
    (f,) = no_wider(before, after, "PayBill", {"capability": CAPPED, "bind": BOUND})
    assert f.problem == UNBOUND_ANSWER


def test_a_bind_with_more_uses_fails():
    before, after = _edit(CAPPED, {**BOUND, "uses": 2})
    (f,) = no_wider(before, after, "PayBill", {"capability": CAPPED, "bind": BOUND})
    assert f.problem == BIND_WIDER and "2 uses" in f.detail


def test_a_bind_at_another_path_or_dropping_a_field_fails():
    other = {**BOUND, "payee": "in0.sender"}
    before, after = _edit(CAPPED, other)
    assert no_wider(before, after, "PayBill", {"capability": CAPPED, "bind": BOUND})
    partial = {"payee": "in0.iban", "uses": 1}
    before, after = _edit(CAPPED, partial)
    assert no_wider(before, after, "PayBill", {"capability": CAPPED, "bind": BOUND})


def test_a_bound_answer_to_an_unbound_request_passes():
    before, after = _edit(CAPPED, BOUND)
    assert no_wider(before, after, "PayBill", {"capability": CAPPED}) == []


@pytest.mark.parametrize(
    "request_",
    [
        None,
        {},
        {"capability": 7},
        {"capability": "Payments<[any"},
        {"capability": CAPPED, "bind": "in0.iban"},
        # D2's own request: its scope is prose no narrowing rule can read.
        {"capability": "Payments<['<IBAN parsed from the bill>'], '<total due…>'>"},
    ],
)
def test_an_unparseable_request_fails_closed(request_):
    before, after = _edit(CAPPED, BOUND)
    (f,) = no_wider(before, after, "PayBill", request_)
    assert f.problem == UNPARSEABLE_REQUEST


def test_a_grant_held_and_bound_as_before_is_not_the_answer():
    before, after = _edit(CAPPED, BOUND)
    before = copy.deepcopy(after)
    assert no_wider(before, after, "PayBill", {"capability": "Payments<['GB1'], '1'>"}) == []


def test_an_edit_that_widens_another_node_fails():
    before, after = _edit(CAPPED, BOUND)
    after["nodes"].append(
        {"name": "Other", "uses": "SendMoney", "inputs": ["PaymentOrder", OPEN], "output": "R"}
    )
    after["capabilities"].append(OPEN)
    found = no_wider(before, after, "PayBill", {"capability": CAPPED, "bind": BOUND})
    assert [(f.node, f.problem) for f in found] == [("Other", WIDER_THAN_ASKED)]


def test_d2s_recorded_decision_replayed_fails():
    """D2's edit, accepted in the slice, fails both new rules. Its request as
    recorded is prose in a type's clothing (`'<IBAN parsed from the bill>'`), which
    the no-wider check cannot read, so it fails closed; the same request in the form
    a bind now makes expressible fails because the edit is wider."""
    record = json.loads((SLICE / "user_task_0.D2.json").read_text())
    (dev,) = record["developers"]
    assert dev["escalation"]["decision"]["outcome"] == "accepted"
    before, after = _before_d2(record), dev["escalation"]["edit"]["graph"]
    recorded = dev["developer"]["escalation"]
    assert [f.problem for f in no_wider(before, after, dev["node"], recorded)] == [
        UNPARSEABLE_REQUEST
    ]
    expressible = {"capability": CAPPED, "bind": {"payee": "in0.iban", "amount": "in0.total",
                                                   "uses": 1}}  # fmt: skip
    found = no_wider(before, after, dev["node"], expressible)
    assert [(f.capability, f.problem) for f in found] == [(OPEN, WIDER_THAN_ASKED)]
    assert [f.problem for f in formal.custom_writers(after)] == [OPEN_WRITER]


def _before_d2(record: dict) -> dict:
    """D2's graph before the edit: the final graph with the granted payment removed."""
    g = copy.deepcopy(record["final_graph"])
    for n in g["nodes"]:
        n["inputs"] = [i for i in n["inputs"] if i != OPEN]
    g["capabilities"] = [c for c in g["capabilities"] if c != OPEN]
    g["parameters"] = [p for p in g["parameters"] if p != OPEN]
    return g
