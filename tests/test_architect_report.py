"""The architect report renders from committed records, and its headline figures are
pinned to them (task 6.1). Stdlib-only; nothing calls a model."""

from __future__ import annotations

from poc.architect import report


def test_the_registered_run_is_complete_and_read_as_registered():
    r = report.registered_summary()
    assert r["recorded"] == r["planned"] == 400
    assert r["registration_commit"] == ["b900365f96344485c970cc809215e8f662a4d87b"]
    c = r["confirmatory"]
    assert (c["channel_a"], c["q0"]) == ({"unseen": 29, "of": 160}, {"unseen": 6, "of": 80})
    assert round(c["p"], 3) == 0.019 and c["supported"] is False


def test_the_gate_and_the_natural_catch_rate_are_both_reported():
    r = report.registered_summary()
    assert r["preuse"] == {"caught": 10, "planted": 10, "false_alarms": 0,
                           "grants_within_label": 55}  # fmt: skip
    widened = sum(s["widened"] for s in r["conditions"].values())
    caught = sum(s["caught_by_reviewer"] for s in r["conditions"].values())
    assert (caught, widened) == (17, 76)
    assert sum(s["caught_by_link_check"] for s in r["conditions"].values()) == 0


def test_the_quoted_dynamic_names_are_counted_apart():
    assert report.quoted_dynamic("Payments<['any'], uncapped>")
    assert report.quoted_dynamic("Payments<['inbound-senders'], '10.00'>")
    assert not report.quoted_dynamic("Payments<[any], uncapped>")
    assert report.registered_summary()["unseen_quoted_dynamic"] == {"B-Q1": 2, "B-Q2": 3, "Q0": 1}


def test_the_markdown_keeps_the_runs_apart_and_states_the_verdict(tmp_path):
    assert report.main([str(tmp_path)]) == 0
    md = (tmp_path / "architect.md").read_text()
    for text in ("**not supported**", "never pooled", "identical", "not summed",
                 "The pre-use corpus overstates it"):  # fmt: skip
        assert text in md
