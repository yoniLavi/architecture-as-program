"""The least-authority labels (task 2.2): well formed, complete, never granting
`Credentials`, and agreeing with the suite's own prompts."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from type_parser import parse_type

from poc.architect import formal, labels

DATA = labels.load()
TASKS = [f"user_task_{i}" for i in range(16)]
GRAPHS = Path(__file__).resolve().parent.parent / "poc" / "agentdojo" / "graphs"


def test_every_banking_task_has_a_label():
    assert sorted(DATA["tasks"]) == sorted(TASKS)


@pytest.mark.parametrize("task", TASKS)
def test_each_grant_parses_has_a_known_kind_and_a_reason(task):
    entry = DATA["tasks"][task]
    assert entry["expected"] in ("graph", "inexpressible")
    for grant in entry["grants"]:
        parse_type(grant)
        assert formal.kind(grant) in formal.CLASSES, grant
        assert entry["reasons"].get(grant), f"{task}: no reason for {grant}"
    assert set(entry["reasons"]) == set(entry["grants"])


def test_no_label_grants_credentials():
    every = [g for t in DATA["tasks"].values() for g in t["grants"]] + list(DATA["uniform"])
    assert not any(formal.kind(g) == "Credentials" for g in every)


def test_the_author_s_approval_is_recorded_with_the_decisions():
    # Task 2.2a, 31 October 2026. The open questions were answered there.
    assert labels.approved(DATA)
    assert {"user_task_5", "user_task_10", "caps", "the_rest"} <= set(DATA["decisions"])


@pytest.mark.parametrize(
    ("graph", "task"),
    [
        ("banking-user-task-0", "user_task_0"),
        ("banking-user-task-1", "user_task_1"),
        ("banking-user-task-15", "user_task_15"),
    ],
)
def test_the_oracle_graphs_are_within_their_labels(graph, task):
    g = json.loads((GRAPHS / f"{graph}.json").read_text())
    assert formal.least_authority(g, labels.label(task)) == []


def test_the_prompts_are_the_suite_s():
    harness = pytest.importorskip("poc.agentdojo.harness")
    suite = harness.suite()
    for task in TASKS:
        assert DATA["tasks"][task]["prompt"] == suite.user_tasks[task].PROMPT, task
