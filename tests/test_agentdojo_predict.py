"""Static predictions per task and injection pair (tasks 5.1 and 5.2). Stdlib-only."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from poc.agentdojo.predict import (
    BOUNDED,
    GOALS,
    IMPOSSIBLE,
    ORACLE,
    PREDICTIONS,
    RESIDUAL,
    contradictions,
    document,
    graph_sha256,
    predict,
)

ROOT = Path(__file__).resolve().parent.parent
GRAPHS = ROOT / "poc" / "agentdojo" / "graphs"
ORACLE_RECORD = ROOT / "poc" / "agentdojo" / "records" / "oracle-plans.json"


def graph(name: str) -> dict:
    return json.loads((GRAPHS / f"{name}.json").read_text())


@pytest.mark.parametrize(("name", "task"), ORACLE.items())
def test_the_committed_predictions_are_what_the_script_derives(name, task):
    committed = json.loads((PREDICTIONS / f"{name}.json").read_text())
    assert committed == json.loads(json.dumps(document(graph(name), task, author="oracle")))


@pytest.mark.parametrize(("name", "task"), ORACLE.items())
def test_a_prediction_names_the_graph_it_was_made_for(name, task):
    committed = json.loads((PREDICTIONS / f"{name}.json").read_text())
    assert committed["graph_sha256"] == graph_sha256(graph(name))
    assert sorted(committed["predictions"]) == list(GOALS)


def test_the_oracle_predictions():
    verdicts = {
        name: {g: p.verdict for g, p in predict(graph(name), task).items()}
        for name, task in ORACLE.items()
    }
    assert set(verdicts["banking-user-task-1"].values()) == {IMPOSSIBLE}
    assert set(verdicts["banking-user-task-15"].values()) == {IMPOSSIBLE}
    residual = {g for g, v in verdicts["banking-user-task-0"].items() if v == RESIDUAL}
    assert residual == {f"injection_task_{i}" for i in (0, 1, 2, 3, 5, 6)}


def test_no_stand_in_run_contradicts_a_prediction():
    runs = json.loads(ORACLE_RECORD.read_text())["runs"]
    for name in ORACLE:
        doc = json.loads((PREDICTIONS / f"{name}.json").read_text())
        assert contradictions(doc, runs) == []


def test_a_contradiction_is_listed():
    doc = json.loads((PREDICTIONS / "banking-user-task-1.json").read_text())
    run = {"graph": doc["graph"], "injection_task": "injection_task_5", "attack_success": True}
    assert contradictions(doc, [run]) == [run]


# ── The verdicts move with the graph ─────────────────────────────────


def _task0(cap: str, payees: str = "[any]") -> dict:
    g = copy.deepcopy(graph("banking-user-task-0"))
    old = "Payments<[any], uncapped>"
    new = f"Payments<{payees}, {cap}>"
    for key in ("parameters", "capabilities"):
        g[key] = [new if c == old else c for c in g[key]]
    for n in g["nodes"]:
        n["inputs"] = [new if c == old else c for c in n["inputs"]]
    return g


def test_a_cap_bounds_the_amount_goals_and_not_the_others():
    p = predict(_task0("'10.00'"), "user_task_0")
    assert p["injection_task_5"].verdict == BOUNDED
    assert p["injection_task_6"].verdict == BOUNDED
    assert p["injection_task_0"].verdict == RESIDUAL  # any payment still lands


def test_a_payee_list_bounds_every_payment_goal():
    p = predict(_task0("uncapped", "['UK12345678901234567890']"), "user_task_0")
    for goal in ("injection_task_0", "injection_task_5", "injection_task_6"):
        assert p[goal].verdict == BOUNDED


def test_an_extractor_reading_the_history_would_open_the_subject_goals():
    """Goal 8 needs the scheduled payments in the subject: the extractor must be able
    to read them. Wire `ReadScheduled` into it and the verdict moves."""
    g = copy.deepcopy(graph("banking-user-task-0"))
    g["parameters"].append("DBHandle<'scheduled-transactions', read>")
    g["capabilities"].append("DBHandle<'scheduled-transactions', read>")
    g["nodes"].append(
        {"name": "ReadScheduled", "uses": "ReadScheduled",
         "inputs": ["TaskRequest", "DBHandle<'scheduled-transactions', read>"],
         "output": "Untrusted<TransactionList>"}
    )  # fmt: skip
    extract = next(n for n in g["nodes"] if n["name"] == "ExtractInvoice")
    extract["inputs"].insert(1, "Untrusted<TransactionList>")
    g["data_edges"] = [e for e in g["data_edges"] if e["to"] != "ExtractInvoice"] + [
        {"from": "Start", "to": "ReadScheduled"},
        {"from": "ReadBill", "to": "ExtractInvoice", "to_input": 0},
        {"from": "ReadScheduled", "to": "ExtractInvoice", "to_input": 1},
    ]
    assert predict(g, "user_task_0")["injection_task_8"].verdict == RESIDUAL
