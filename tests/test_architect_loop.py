"""The architect's loop: bounded repairs, recorded failures, and what it is shown
(tasks 1.3, 1.4). A scripted backend stands in for the model; nothing calls one."""

from __future__ import annotations

import inspect
import json
from dataclasses import dataclass, field

import pytest

from poc.architect import abstract, architect, mapping
from poc.architect.abstract import Reason
from poc.architect.architect import (
    CALL_FAILED,
    FAILED_STAGE_ONE,
    FAILED_STAGE_TWO,
    GRAPH,
    INEXPRESSIBLE,
    MAX_REPAIRS,
    ModelMismatch,
    author,
)
from poc.llm import LLMRequest, LLMResponse, ModelCallError, UsageLimitReached

TASK = "Send 25.00 to my sister, DE75512108001245126199, for the concert ticket, and tell me when it's done."
ABSTRACT = {
    "nodes": [{"name": "Pay", "role": "pay the sister"}, {"name": "Tell", "role": "tell me"}],
    "edges": [{"from": "Pay", "to": "Tell", "carries": "the receipt"}],
}
GOOD_ONE = json.dumps(ABSTRACT)
GOOD_TWO = json.dumps(mapping.EXAMPLE)


@dataclass
class Scripted:
    """Replies in order; each item a string, or an exception to raise."""

    replies: list
    model: str = "claude-haiku-5-5"
    requests: list[LLMRequest] = field(default_factory=list)
    usage: list[dict] = field(default_factory=list)

    def generate(self, request: LLMRequest) -> LLMResponse:
        self.requests.append(request)
        reply = self.replies.pop(0)
        if isinstance(reply, BaseException):
            raise reply
        self.usage.append({"model": self.model})
        return LLMResponse(text=reply)


def test_two_good_replies_make_a_graph():
    rec = author(TASK, Scripted([GOOD_ONE, GOOD_TWO]), name="ArchitectExample")
    assert rec["outcome"] == GRAPH
    assert rec["graph"]["name"] == "ArchitectExample"
    assert rec["abstract"] == ABSTRACT
    assert [a["stage"] for a in rec["attempts"]] == ["one", "two"]
    assert rec["model_ids"] == ["claude-haiku-5-5"]


def test_a_stage_one_repair_is_shown_its_reasons():
    backend = Scripted(["not json", GOOD_ONE, GOOD_TWO])
    rec = author(TASK, backend)
    assert rec["outcome"] == GRAPH
    assert rec["attempts"][0]["reasons"][0]["cls"] == abstract.NOT_JSON
    assert "- not-json:" in backend.requests[1].prompt


def test_a_stage_two_draft_the_validator_rejects_is_repaired():
    bad = json.loads(GOOD_TWO)
    bad["nodes"][1]["output"] = "StandingOrder"  # an edge type mismatch
    backend = Scripted([GOOD_ONE, json.dumps(bad), GOOD_TWO])
    rec = author(TASK, backend)
    assert rec["outcome"] == GRAPH
    assert "edge type-compatibility" in {r["cls"] for r in rec["attempts"][1]["reasons"]}


def test_stage_two_still_invalid_after_the_bound_is_a_recorded_failure():
    rec = author(TASK, Scripted([GOOD_ONE] + ["{}"] * (MAX_REPAIRS + 1)))
    assert rec["outcome"] == FAILED_STAGE_TWO and rec["graph"] is None
    assert len([a for a in rec["attempts"] if a["stage"] == "two"]) == MAX_REPAIRS + 1


def test_stage_one_still_invalid_after_the_bound_ends_the_attempt():
    backend = Scripted(["no"] * (MAX_REPAIRS + 1))
    rec = author(TASK, backend)
    assert rec["outcome"] == FAILED_STAGE_ONE
    assert len(backend.requests) == MAX_REPAIRS + 1  # stage two never ran


def test_inexpressible_is_recorded_with_its_reason():
    rec = author(TASK, Scripted([GOOD_ONE, '{"inexpressible": "no password node"}']))
    assert rec["outcome"] == INEXPRESSIBLE and rec["inexpressible"] == "no password node"


def test_a_failed_call_is_an_attempt_that_produced_nothing():
    rec = author(TASK, Scripted([ModelCallError("timed out"), GOOD_ONE, GOOD_TWO]))
    assert rec["outcome"] == GRAPH
    assert rec["attempts"][0]["reply"].startswith(f"[{CALL_FAILED}")


def test_the_usage_ceiling_stops_without_a_record():
    with pytest.raises(UsageLimitReached):
        author(TASK, Scripted([GOOD_ONE, UsageLimitReached("window")]))


def test_a_registered_run_refuses_a_call_that_resolved_elsewhere():
    backend = Scripted([GOOD_ONE, GOOD_TWO], model="claude-sonnet-5-5")
    with pytest.raises(ModelMismatch):
        author(TASK, backend, expected_model="claude-haiku-5-5")


# ── What the architect is shown (task 1.4) ──────────────────────────


def test_author_has_no_parameter_through_which_tool_output_could_arrive():
    params = set(inspect.signature(author).parameters)
    assert params == {"task_prompt", "backend", "document", "name", "expected_model"}


@pytest.mark.parametrize("document", [None, "A memo from the bank."])
def test_every_request_is_built_from_the_allowed_pieces_only(document):
    """Each request is exactly the stage's system text with either its shown text or a
    repair of it, built from the architect's own last reply and its reasons. Nothing
    else can be in it, so no tool output, injection or reviewer verdict is."""
    bad_two = json.loads(GOOD_TWO)
    bad_two["nodes"][1]["output"] = "StandingOrder"
    backend = Scripted(["oops", GOOD_ONE, json.dumps(bad_two), GOOD_TWO])
    rec = author(TASK, backend, document)
    shown_one = abstract.prompt(TASK, document)
    shown_two = mapping.prompt(TASK, ABSTRACT, document)
    reqs, attempts = backend.requests, rec["attempts"]

    def reasons(a: dict) -> list[Reason]:
        return [Reason(r["cls"], r["detail"]) for r in a["reasons"]]

    assert [r.system for r in reqs] == [abstract.STAGE_ONE_SYSTEM] * 2 + [mapping.system()] * 2
    assert reqs[0].prompt == shown_one
    assert reqs[1].prompt == architect.repair_text(shown_one, "oops", reasons(attempts[0]))
    assert reqs[2].prompt == shown_two
    assert reqs[3].prompt == architect.repair_text(
        shown_two, json.dumps(bad_two), reasons(attempts[2])
    )


def test_the_record_hashes_what_was_shown():
    rec = author(TASK, Scripted([GOOD_ONE, GOOD_TWO]), document="DOC")
    h = rec["inputs_sha256"]
    assert h["task_prompt"] == architect.sha256(TASK)
    assert h["document"] == architect.sha256("DOC")
    assert h["stage_two_system"] == architect.sha256(mapping.system())
    assert all(a["prompt_sha256"] for a in rec["attempts"])
