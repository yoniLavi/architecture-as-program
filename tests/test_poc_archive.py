"""The feed recorder: raw bodies archived through the graph's own allowlist, no
model called, failures recorded, one recorder at a time, gaps visible.

Every fetch here goes to the loopback fixture server; nothing touches the network.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import UTC, datetime

import pytest

from poc import serve
from poc.feeds import archive
from poc.graph import load_graph_dict
from poc.handles import WallTime
from poc.llm import StubLLM
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


# ── Replay ────────────────────────────────────────────────────────────


def _archive(tmp_path, hours=(0, 1, 2), *, atom_from=1):
    """Record ticks an hour apart: RSS in each, ATOM from tick `atom_from` on (so
    the first tick records ATOM as a failure). RSS repeats its items every tick."""
    routes = {"/rss": ok(RSS)}
    with serving(routes) as server:
        feeds = (server.url("/rss"), server.url("/atom"))
        for i, h in enumerate(hours):
            if i == atom_from:
                routes["/atom"] = ok(ATOM)
            _recorder(tmp_path, server, at=T0 + h * 3600, feeds=feeds).tick()
    return tmp_path / "var"


def _replay_config(out):
    return serve.Config(
        var_dir=out,
        backend=StubLLM(),
        graph=serve.retarget(PARENT, ["127.0.0.1"]),
    )


def _records(out):
    runs = sorted((out / "runs").glob("*/run.json"))
    return [{k: v for k, v in json.loads(p.read_text()).items() if k != "seconds"} for p in runs]


def _digests(out):
    return {p.name: p.read_text() for p in sorted((out / "digests").glob("*.md"))}


def test_a_replay_is_deterministic_on_the_stub(tmp_path):
    archived = _archive(tmp_path)
    one, two = tmp_path / "replay-1", tmp_path / "replay-2"
    assert serve.replay(_replay_config(one), archived) == serve.EXIT_OK
    assert serve.replay(_replay_config(two), archived) == serve.EXIT_OK
    assert _records(one) == _records(two) and len(_records(one)) == 3
    assert _digests(one) == _digests(two) and _digests(one)


def test_an_item_in_consecutive_snapshots_is_triaged_once(tmp_path):
    archived = _archive(tmp_path, atom_from=99)  # RSS only, the same items every tick
    out = tmp_path / "replay"
    serve.replay(_replay_config(out), archived)
    triaged = [r["counts"]["items_triaged"] for r in _records(out)]
    assert triaged[0] > 0 and triaged[1:] == [0, 0]


def test_a_feed_that_failed_when_recorded_fails_in_the_replay(tmp_path):
    archived = _archive(tmp_path)
    out = tmp_path / "replay"
    serve.replay(_replay_config(out), archived)
    records = _records(out)
    assert [r["counts"]["fetch_failures"] for r in records] == [1, 0, 0]
    assert records[0]["fetch_failures"][0]["url"].endswith("/atom")


def test_each_replayed_tick_runs_at_its_recorded_time(tmp_path):
    archived = _archive(tmp_path)
    out = tmp_path / "replay"
    serve.replay(_replay_config(out), archived)
    started = [r["started"] for r in _records(out)]
    expected = [
        datetime.fromtimestamp(T0 + h * 3600, tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        for h in (0, 1, 2)
    ]
    assert started == expected


def test_a_replay_window_selects_its_ticks(tmp_path):
    archived = _archive(tmp_path)
    out = tmp_path / "replay"
    start = datetime.fromtimestamp(T0 + 3600, tz=UTC)
    serve.replay(_replay_config(out), archived, start=start, label={"backend": "stub"})
    assert len(_records(out)) == 2
    meta = json.loads((out / "replay.json").read_text())
    assert meta["archive_ticks"] == 2 and meta["backend"] == "stub"
    assert serve.report(out)["replay"] == meta


def test_a_replay_never_writes_into_the_live_service(tmp_path, capsys):
    config = _replay_config(serve.VAR_DIR)
    assert serve.replay(config, tmp_path / "nothing") == serve.EXIT_CONFIG
    assert "live service" in capsys.readouterr().err


def test_a_live_run_log_carries_no_replay_label(tmp_path):
    assert serve.report(tmp_path / "var")["replay"] is None


def test_the_command_line_routes_a_replay_to_its_own_directory(tmp_path, monkeypatch):
    seen = {}
    monkeypatch.setattr(
        serve, "replay", lambda config, archive, **kw: seen.update(var=config.var_dir, **kw) or 0
    )
    monkeypatch.setattr("poc.polite.lower_priority", lambda on: {})
    assert serve.main(["--replay", str(tmp_path), "--backend", "stub", "--tier", "confined"]) == 0
    assert seen["var"] == serve.VAR_DIR / "replays" / "stub-confined"
    assert seen["label"] == {"backend": "stub", "tier": "confined", "model": None}


def test_coverage_is_exported_for_the_build(tmp_path):
    archived = _archive(tmp_path)
    out = tmp_path / "recording.json"
    archive.main(["--coverage", "--var", str(archived), "--export", str(out)])
    exported = json.loads(out.read_text())
    assert exported["ticks"] == 3 and exported["interval_hours"] == 1.0
    [(url, reasons)] = exported["failures"].items()  # ATOM, 404 on the first tick
    assert url.endswith("/atom") and sum(reasons.values()) == 1


def test_the_evaluation_keeps_recording_replay_and_live_apart(tmp_path):
    """The `evaluation` scenario: three sources, three sections; a replay is
    labelled with what it was replayed on and is never called operation."""
    from poc import evaluate_feed

    archived = _archive(tmp_path, hours=(0, 1, 5))
    out = tmp_path / "replay"
    serve.replay(
        _replay_config(out), archived, label={"backend": "stub", "tier": "host", "model": None}
    )
    recording = {
        **archive.coverage(archive.read_index(archived), 3600),
        "interval_hours": 1.0,
        "failures": archive.failures(archive.read_index(archived)),
    }
    recording_text = "\n".join(evaluate_feed._render_recording(recording))
    assert "## The recording period" in recording_text
    assert f"**{100 * recording['covered_fraction']:.1f}% is covered**" in recording_text
    assert "| 4.0 |" in recording_text  # the four-hour gap, listed

    replay_text = "\n".join(evaluate_feed._render_replays([serve.report(out)]))
    assert "## Replayed history" in replay_text and "A replay is not operation" in replay_text
    assert "| stub | — | host | 3 | 3 |" in replay_text

    assert "No recording" in "\n".join(evaluate_feed._render_recording(None))
    assert "No replay" in "\n".join(evaluate_feed._render_replays([]))


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
