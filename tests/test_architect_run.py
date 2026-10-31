"""The pilot driver (task 4.1), with scripted models and a stub AgentDojo run.
Nothing calls a model."""

from __future__ import annotations

import json

from poc.architect import mapping, run
from poc.architect.run import PILOT_LABEL, pilot_task
from tests.test_architect_loop import GOOD_ONE, Scripted


def test_a_pilot_task_records_every_step_and_its_label():
    # The worked example's graph, offered for task 4 (a refund to a named IBAN): it
    # pays the wrong payee, so the formal review must say so; the run is stubbed.
    two = json.dumps(mapping.EXAMPLE)
    caps = mapping.EXAMPLE["capabilities"]
    verdict = json.dumps({"grants": [{"capability": c, "verdict": "needed"} for c in caps]})
    backends = {"architect": Scripted([GOOD_ONE, two]), "reviewer": Scripted([verdict])}
    ran = []

    def run_graph(graph, task, backend):
        ran.append((graph["name"], task))
        return {"utility": False, "failure": None}

    rec = pilot_task("user_task_4", "claude-haiku-5-5", backends.get, run_graph=run_graph)
    assert rec["label"] == PILOT_LABEL and rec["architect"]["outcome"] == "graph"
    assert ran == [("ArchitectUserTask4", "user_task_4")]
    widened = {w["grant"] for w in rec["formal"]["widenings"]}
    assert "Payments<['DE75512108001245126199'], '25.00'>" in widened
    assert {f["problem"] for f in rec["formal"]["links"]} == {"fabricated-link"}
    assert rec["reviewer"]["score"]["missed"] == sorted(widened)


def test_an_architect_that_fails_is_recorded_without_review_or_run():
    backends = {"architect": Scripted(["no"] * 5)}
    rec = pilot_task("user_task_1", "claude-haiku-5-5", backends.get, run_graph=None)
    assert rec["architect"]["outcome"] == "failed-stage-one"
    assert rec["formal"] is rec["reviewer"] is rec["run"] is None


def test_the_agentdojo_run_scores_a_graph_with_the_backend_it_is_given():
    import pytest

    harness = pytest.importorskip("poc.agentdojo.harness")
    from poc.agentdojo.standins import OracleModel

    g = harness.load_graph("banking-user-task-0")
    result = run._agentdojo_run(g, "user_task_0", OracleModel(harness.oracle_answers(g)))
    assert result["utility"] is True and result["model"] == "live"
    assert result["tier"] == "host" and result["failure"] is None


def test_records_live_under_the_run_and_model():
    p = run.record_path("pilot", "claude-haiku-5-5", "user_task_3")
    assert p.parts[-3:] == ("pilot", "claude-haiku-5-5", "user_task_3.json")
