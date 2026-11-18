"""The post-hoc Sonnet reviewer (`add-paper-4` task 5). A scripted backend stands in
for the model; nothing calls one.

What must hold for the run to mean what it says: the reviewer is shown exactly what
the registered reviewer was, byte for byte, on every trial of the committed plan; the
plan is the behaviour replay's fixed sample; and the summary scores Sonnet and the
registered reviewer on the same trials the same way."""

from __future__ import annotations

import json

import pytest

from poc.architect import posthoc_sonnet as ph
from poc.architect.reviewer import PERSUADED, PRIMARY
from poc.llm import LLMResponse, UsageLimitReached


@pytest.fixture(scope="module")
def registered():
    return ph.registered_by_id()


@pytest.fixture(scope="module")
def plan():
    return json.loads(ph.PLAN.read_text())


def test_the_committed_plan_is_the_behaviour_replays_sample(plan):
    fresh = ph.make_plan()
    assert plan == fresh
    assert plan["model"] == "claude-sonnet-5-5" and plan["views"] == [PRIMARY, PERSUADED]
    assert plan["calls_planned"] == 2 * len(plan["trials"])


def test_every_planned_input_reproduces_the_registered_hash(plan, registered):
    """Both views, every trial: the system text and the shown prompt are the registered
    reviewer's, so the reviewer's model is the only thing that changed."""
    for trial in plan["trials"]:
        for view in plan["views"]:
            ph.inputs(registered[trial], view)  # raises InputDrift on any difference


def test_a_drifted_input_is_refused(registered, plan):
    record = json.loads(json.dumps(registered[plan["trials"][0]]))
    record["reviews"][PRIMARY]["inputs_sha256"]["shown"] = "0" * 64
    with pytest.raises(ph.InputDrift):
        ph.inputs(record, PRIMARY)


def test_the_graph_is_rebuilt_in_the_order_the_reviewer_saw(registered, plan):
    record = registered[plan["trials"][0]]
    g = ph.shown_graph(record)
    assert g == record["architect"]["graph"]
    # The stored record sorts keys; the rebuilt graph keeps the architect's order.
    assert list(g["nodes"][0]) != sorted(g["nodes"][0]) or list(g) != sorted(g)


class Fake:
    def __init__(self, flag: bool = True, model: str = ph.MODEL, raise_usage: bool = False):
        self.flag, self.model, self.raise_usage = flag, model, raise_usage
        self.usage, self.windows, self.prompts = [], {"seven_day": 0.1}, []

    def generate(self, request):
        if self.raise_usage:
            raise UsageLimitReached("ceiling")
        self.prompts.append(request.prompt)
        self.usage.append({"model": self.model})
        shown = json.loads(request.prompt.split("The graph:\n\n", 1)[1])
        verdict = "wider" if self.flag else "needed"
        grants = [{"capability": c, "verdict": verdict} for c in shown["capabilities"]]
        return LLMResponse(text=json.dumps({"grants": grants}))


def _small_plan(tmp_path, monkeypatch, plan, n=2):
    small = {**plan, "trials": plan["trials"][:n], "calls_planned": 2 * n}
    monkeypatch.setattr(ph, "RUN", tmp_path)
    monkeypatch.setattr(ph, "PLAN", tmp_path / "plan.json")
    (tmp_path / "plan.json").write_text(json.dumps(small))
    monkeypatch.setattr(ph, "_repo", lambda: type("R", (), {
        "status": lambda self, *a: [], "head": lambda self: "c0ffee"})())  # fmt: skip
    return small


def test_a_run_records_both_views_primary_first(tmp_path, monkeypatch, plan, registered):
    small = _small_plan(tmp_path, monkeypatch, plan)
    monkeypatch.setattr(ph, "REPO_ROOT", tmp_path.parent)
    made = []

    def backend():
        made.append(Fake())
        return made[-1]

    assert ph.run({"lowered": False}, backend) == 0
    for view in (PRIMARY, PERSUADED):
        for trial in small["trials"]:
            rec = json.loads(ph.path(view, trial).read_text())
            assert rec["label"] == ph.LABEL and rec["view"] == view
            assert (
                rec["review"]["inputs_sha256"]
                == registered[trial]["reviews"][view]["inputs_sha256"]
            )
            assert rec["review"]["model_ids"] == [ph.MODEL]
    assert len(made) == 4
    assert "because" not in made[0].prompts[0] and "because" in made[2].prompts[0]
    s = ph.summarise(*ph.load(tmp_path), registered)
    assert s["complete"] and s["recorded"] == 4


def test_the_usage_ceiling_stops_with_nothing_partial(tmp_path, monkeypatch, plan):
    _small_plan(tmp_path, monkeypatch, plan)
    monkeypatch.setattr(ph, "REPO_ROOT", tmp_path.parent)
    assert ph.run({}, lambda: Fake(raise_usage=True)) == ph.EXIT_USAGE
    assert not list(tmp_path.glob("*/*.json"))


def test_another_model_is_refused(tmp_path, monkeypatch, plan):
    _small_plan(tmp_path, monkeypatch, plan)
    monkeypatch.setattr(ph, "REPO_ROOT", tmp_path.parent)
    assert ph.run({}, lambda: Fake(model="claude-haiku-5-5")) == ph.EXIT_REFUSED
    assert not list(tmp_path.glob("*/*.json"))


def test_a_dirty_tree_is_refused(tmp_path, monkeypatch, plan):
    _small_plan(tmp_path, monkeypatch, plan)
    monkeypatch.setattr(ph, "REPO_ROOT", tmp_path.parent)
    monkeypatch.setattr(ph, "_repo", lambda: type("R", (), {
        "status": lambda self, *a: ["poc/x.py"], "head": lambda self: "c0ffee"})())  # fmt: skip
    assert ph.run({}, lambda: Fake()) == ph.EXIT_REFUSED


def _verdicts(caps, flagged):
    return {c: {"verdict": "wider" if c in flagged else "needed", "quote": "", "narrower": ""}
            for c in caps}  # fmt: skip


def test_the_summary_pairs_each_trial_with_the_registered_verdict():
    caps = ["A", "B"]
    reg = {
        "w": {"formal": {"widenings": [{"grant": "A", "cls": "effect"}]},
              "architect": {"graph": {"capabilities": caps}},
              "reviews": {PRIMARY: {"verdicts": _verdicts(caps, {"B"})}}},
        "c": {"formal": {"widenings": []}, "architect": {"graph": {"capabilities": caps}},
              "reviews": {PRIMARY: {"verdicts": _verdicts(caps, {"A"})}}},
    }  # fmt: skip
    plan = {"label": "x", "model": "m", "views": [PRIMARY], "trials": ["w", "c"],
            "widened_trials": 1, "calls_planned": 2}  # fmt: skip
    records = {PRIMARY: {
        "w": {"review": {"verdicts": _verdicts(caps, {"A"}), "model_ids": ["m"]}},
        "c": {"review": {"verdicts": _verdicts(caps, set()), "model_ids": ["m"]}},
    }, PERSUADED: {}}  # fmt: skip
    s = ph.summarise(plan, records, reg)["views"][PRIMARY]
    assert (s["caught"], s["registered_caught"], s["gained"], s["lost"]) == (1, 0, 1, 0)
    assert (s["clean_trials_flagged"], s["registered_clean_trials_flagged"]) == (0, 1)
    # Within-label grants: B on w, A and B on c.
    assert s["grants_within_label"] == 3
    assert (s["false_alarms"], s["registered_false_alarms"]) == (0, 2)
