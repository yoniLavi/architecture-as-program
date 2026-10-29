"""The banking report renders from committed records only (task 4.3). Stdlib-only."""

from __future__ import annotations

import json

from poc.agentdojo import report


def _baseline(tmp_path, monkeypatch, runs: list[dict]) -> None:
    path = tmp_path / "claude-haiku-5-5" / "rep-0.jsonl"
    path.parent.mkdir(parents=True)
    path.write_text("".join(json.dumps(r) + "\n" for r in runs))
    monkeypatch.setattr(report, "BASELINE", tmp_path)


def _run(user: str, inj: str | None, utility: bool, attacked: bool | None) -> dict:
    return {"user_task": user, "injection_task": inj, "utility": utility,
            "attack_success": attacked, "model_resolved": ["claude-haiku-5-5"]}  # fmt: skip


def test_the_report_renders_every_section_with_its_caveats(tmp_path, monkeypatch):
    _baseline(tmp_path, monkeypatch, [_run("user_task_0", None, True, None)])
    assert report.main([str(tmp_path / "out")]) == 0
    md = (tmp_path / "out" / "agentdojo-banking.md").read_text()
    for text in (
        "not a benchmark result",
        "0% attack success is not the absence of a residual",
        "succeed on any payment to the attacker",
        "partial: 1/160 runs",
    ):
        assert text in md
    data = json.loads((tmp_path / "out" / "agentdojo-banking.json").read_text())
    assert all(c["held"] for c in data["corpus"])
    assert all(p["contradictions"] == [] for p in data["oracle_plans"])


def test_the_baseline_counts_utility_and_attacks_apart(tmp_path, monkeypatch):
    _baseline(
        tmp_path,
        monkeypatch,
        [
            _run("user_task_0", None, True, None),
            _run("user_task_1", None, False, None),
            _run("user_task_0", "injection_task_5", False, True),
            _run("user_task_0", "injection_task_7", True, False),
        ],
    )
    (b,) = report.baseline_summary()
    assert b["utility"] == {"hits": 1, "n": 2}
    assert b["utility_under_attack"] == {"hits": 1, "n": 2}
    assert b["attack_success"] == {"hits": 1, "n": 2}
    assert b["attack_success_by_goal"] == {"injection_task_5": 1}
    assert not b["complete"]
