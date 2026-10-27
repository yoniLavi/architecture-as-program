"""The feed recorder: raw bodies archived through the graph's own allowlist, no
model called, failures recorded, one recorder at a time, gaps visible.

Every fetch here goes to the loopback fixture server; nothing touches the network.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest

from poc import serve
from poc.feeds import archive
from poc.graph import load_graph_dict
from poc.handles import WallTime
from poc.polite import LOWEST_NICE, lower_priority
from tests.feed_fixtures import ATOM, RSS, ok, redirect, serving

PARENT = load_graph_dict("feed-triage")
T0 = 1_793_000_000  # 2026-10-27, give or take


def _recorder(tmp_path, server, *, at=T0, feeds=None):
    return archive.Recorder(
        var_dir=tmp_path / "var",
        graph=serve.retarget(PARENT, ["127.0.0.1"]),
        feeds=feeds or (server.url("/rss"), server.url("/atom")),
        clock=lambda: WallTime(at, 0),
    )


def test_a_tick_archives_each_raw_body_and_indexes_it(tmp_path):
    with serving({"/rss": ok(RSS), "/atom": ok(ATOM)}) as server:
        entry = _recorder(tmp_path, server).tick()
    tick_dir = tmp_path / "var" / "archive" / entry["tick"]
    assert [f["ok"] for f in entry["feeds"]] == [True, True]
    assert (tick_dir / archive.feed_file(server.url("/rss"))).read_text() == RSS
    assert (tick_dir / archive.feed_file(server.url("/atom"))).read_text() == ATOM
    assert archive.read_index(tmp_path / "var") == [entry]


def test_a_failed_feed_is_recorded_with_its_reason(tmp_path):
    with serving({"/rss": ok(RSS)}) as server:
        entry = _recorder(tmp_path, server).tick()
    failed = [f for f in entry["feeds"] if not f["ok"]]
    assert len(failed) == 1 and failed[0]["url"].endswith("/atom") and failed[0]["error"]


def test_a_redirect_off_the_allowlist_is_a_failure_and_is_not_followed(tmp_path):
    routes = {"/rss": ok(RSS)}
    with serving(routes) as server:
        routes["/away"] = redirect(server.url("/rss", host="localhost"))
        entry = _recorder(tmp_path, server, feeds=(server.url("/away"),)).tick()
    assert entry["feeds"][0]["ok"] is False
    assert server.requests == ["/away"]


def test_a_feed_outside_the_allowlist_is_refused_before_anything_is_fetched(tmp_path, capsys):
    recorder = archive.Recorder(
        var_dir=tmp_path / "var", graph=PARENT, feeds=("https://evil.example/feed",)
    )
    assert archive.record(recorder, None) == serve.EXIT_CONFIG
    assert not (tmp_path / "var" / "archive" / archive.INDEX_NAME).exists()


def test_the_recorder_calls_no_model(tmp_path, monkeypatch):
    def refuse(*_a, **_k):
        raise AssertionError("the recorder called a model")

    monkeypatch.setattr("poc.llm.ClaudeCLIBackend.generate", refuse)
    monkeypatch.setattr("poc.llm.StubLLM.generate", refuse)
    with serving({"/rss": ok(RSS), "/atom": ok(ATOM)}) as server:
        _recorder(tmp_path, server).tick()


def test_a_second_recorder_is_refused_and_records_nothing(tmp_path, capsys):
    with serving({"/rss": ok(RSS), "/atom": ok(ATOM)}) as server:
        recorder = _recorder(tmp_path, server)
        with serve.Lock(archive.archive_dir(recorder.var_dir), archive.LOCK_NAME):
            assert archive.record(recorder, None) == serve.EXIT_LOCKED
        assert not (archive.archive_dir(recorder.var_dir) / archive.INDEX_NAME).exists()
        assert archive.record(recorder, None) == serve.EXIT_OK


def test_a_recorder_and_a_driver_do_not_exclude_each_other(tmp_path):
    with serving({"/rss": ok(RSS), "/atom": ok(ATOM)}) as server:
        recorder = _recorder(tmp_path, server)
        with serve.Lock(recorder.var_dir):  # the driver's lock
            assert archive.record(recorder, None) == serve.EXIT_OK


def test_the_recorder_reads_the_drivers_subscriptions_without_seeding_them(tmp_path):
    var = tmp_path / "var"
    assert archive.subscriptions(var) == list(serve.DEFAULT_SUBSCRIPTIONS)
    assert not (var / "state").exists()
    (var / "state").mkdir(parents=True)
    (var / "state" / "subscriptions.json").write_text(
        json.dumps({"feeds": "https://lobste.rs/t/plt.rss\n# off\n"})
    )
    assert archive.subscriptions(var) == ["https://lobste.rs/t/plt.rss"]


def test_a_gap_between_ticks_is_reported_not_smoothed(tmp_path):
    hour = 3600
    with serving({"/rss": ok(RSS), "/atom": ok(ATOM)}) as server:
        for at in (T0, T0 + hour, T0 + 2 * hour, T0 + 10 * hour):
            _recorder(tmp_path, server, at=at).tick()
    summary = archive.coverage(archive.read_index(tmp_path / "var"), hour)
    assert summary["ticks"] == 4
    assert summary["span_hours"] == 11.0
    assert summary["covered_fraction"] == round(4 / 11, 3)
    assert [g["hours"] for g in summary["gaps"]] == [8.0]


def test_an_unreadable_index_line_names_no_tick(tmp_path):
    with serving({"/rss": ok(RSS), "/atom": ok(ATOM)}) as server:
        entry = _recorder(tmp_path, server).tick()
    index = tmp_path / "var" / "archive" / archive.INDEX_NAME
    index.write_text(index.read_text() + '{"tick": "half-writ')
    assert archive.read_index(tmp_path / "var") == [entry]


# ── Low priority ──────────────────────────────────────────────────────


def _in_child(code: str) -> str:
    return subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=True
    ).stdout.strip()


def test_lowering_priority_reaches_the_children_spawned_after_it():
    out = _in_child(
        "import os, subprocess, sys\n"
        "from poc.polite import lower_priority\n"
        "applied = lower_priority()\n"
        "child = subprocess.run([sys.executable, '-c', 'import os; print(os.nice(0))'],"
        " capture_output=True, text=True).stdout.strip()\n"
        "print(applied['nice'], child, applied['background'])"
    )
    nice, child, background = out.split()
    assert int(nice) == LOWEST_NICE and int(child) == LOWEST_NICE
    if sys.platform == "darwin":
        assert background == "True"


def test_the_opt_out_changes_nothing():
    before = os.nice(0)
    applied = lower_priority(enabled=False)
    assert applied == {"nice": before, "background": False, "lowered": False}
    assert os.nice(0) == before


@pytest.mark.parametrize("argv", [["--record", "--once", "--no-nice"]])
def test_the_command_line_parses(argv, monkeypatch, tmp_path):
    called = {}
    monkeypatch.setattr(archive, "record", lambda r, i: called.setdefault("interval", i) or 0)
    assert archive.main([*argv, "--var", str(tmp_path)]) == 0
    assert called["interval"] is None
