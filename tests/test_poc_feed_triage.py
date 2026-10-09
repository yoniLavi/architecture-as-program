"""The feed-triage service: the graph's shape, and one tick of it.

The shape is asserted here as well as drawn, because it carries the security
argument: one node holds outbound HTTP and no model is upstream of it; each item
is triaged in a run of its own; nothing downstream of a model can fetch.

Covers the `feed-triage-service` requirements added by
`build-feed-triage-and-generation-experiment`, and the driver requirement of
`signal-graph-runtime`. Everything runs on the stub backend; live fetches go to a
server on 127.0.0.1.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from type_parser import TApp, parse_type

from poc import serve
from poc.feed_nodes import MAX_PER_RUN, limit_batch, parse_verdict, render_digest
from poc.feed_values import (
    Category,
    Digest,
    FeedItem,
    Importance,
    ItemVerdict,
    RunReport,
    Tick,
)
from poc.graph import REPO_ROOT, assemble, load_graph_dict, validate_graph_dicts
from poc.handles import WallTime, World
from poc.llm import LLMRequest, LLMResponse, StubLLM, UsageLimitReached
from poc.runtime import execute
from poc.serve import Config
from poc.trace import validate_document
from poc.values import Untrusted
from tests.feed_fixtures import ATOM, RSS, ok, serving

PARENT = load_graph_dict("feed-triage")
CHILD = load_graph_dict("triage-item")
FIXED = WallTime(seconds=1791547200, nanoseconds=0)  # 2026-10-09T12:00:00Z


def _head(cap: str) -> str:
    ast = parse_type(cap)
    return ast.head if isinstance(ast, TApp) else getattr(ast, "name", "")


def _holders(graph: dict, head: str) -> list[str]:
    caps = set(graph["capabilities"])
    return [
        n["name"]
        for n in graph["nodes"]
        if any(i in caps and _head(i) == head for i in n["inputs"])
    ]


def _upstream(graph: dict, node: str) -> set[str]:
    """Every node with a path to `node`."""
    parents: dict[str, set[str]] = {}
    for e in graph["data_edges"]:
        parents.setdefault(e["to"], set()).add(e["from"].split(".")[0])
    found: set[str] = set()
    frontier = [node]
    while frontier:
        for p in parents.get(frontier.pop(), ()):
            if p not in found:
                found.add(p)
                frontier.append(p)
    return found


# ── The shape ────────────────────────────────────────────────────────


def test_the_graphs_validate_together():
    assert validate_graph_dicts([PARENT, CHILD]) == []


def test_exactly_one_node_holds_outbound_http():
    assert _holders(PARENT, "HTTPClient") == ["FetchFeeds"]
    assert _holders(CHILD, "HTTPClient") == []


def test_no_model_is_upstream_of_the_fetch():
    """No node holding an `LLMClient` has a path to `FetchFeeds`, so no model
    output can reach a fetch: the exfiltration attack has no wiring to travel on."""
    models = set(_holders(PARENT, "LLMClient"))
    assert models == {"TriageItem", "ComposeDigest"}
    assert not models & _upstream(PARENT, "FetchFeeds")


def test_no_node_holds_a_tool_scoped_client():
    for graph in (PARENT, CHILD):
        assert all("LLMClient<[" not in cap for cap in graph["capabilities"])


def test_fetched_content_is_labelled_untrusted_where_it_enters():
    fetch = next(n for n in PARENT["nodes"] if n["name"] == "FetchFeeds")
    assert fetch["output"] == "Untrusted<FeedBatch>"


def test_trust_is_discharged_only_inside_the_per_item_child():
    assert [n["name"] for n in PARENT["nodes"] if n.get("discharges_trust")] == ["TriageItem"]
    assert [n["name"] for n in CHILD["nodes"] if n.get("discharges_trust")] == ["ClassifyItem"]
    triage = next(n for n in PARENT["nodes"] if n["name"] == "TriageItem")
    assert triage["each"] is True


def test_only_the_last_node_can_write_the_seen_store():
    writers = [
        n["name"] for n in PARENT["nodes"] if "StateHandle<'seen', read-write>" in n["inputs"]
    ]
    assert writers == ["RecordSeen"]
    assert not [e for e in PARENT["data_edges"] if e["from"].startswith("RecordSeen")]


def test_the_default_subscriptions_are_inside_the_graphs_allowlist():
    serve.check_subscriptions(serve.DEFAULT_SUBSCRIPTIONS, PARENT)
    with pytest.raises(serve.ConfigError, match=r"evil\.example"):
        serve.check_subscriptions(["https://evil.example/feed"], PARENT)


# ── One tick, canned ─────────────────────────────────────────────────

FEEDS = {
    "https://lobste.rs/t/plt.rss": RSS,
    "https://simonwillison.net/atom/everything/": ATOM,
}


def _world(sent: list[str], web: dict[str, str] | None = None) -> World:
    world = World(
        web=FEEDS if web is None else web, publishers={"digest": sent.append}, clock=lambda: FIXED
    )
    world.store("subscriptions").put(
        "feeds", "\n".join(FEEDS) + "\nhttps://rss.arxiv.org/rss/cs.PL\n"
    )
    return world


def test_one_tick_fetches_triages_and_publishes():
    sent: list[str] = []
    world = _world(sent)
    backend = StubLLM()
    result = execute(assemble(PARENT, backend=backend, world=world), Tick())

    assert result.terminals == {"RecordSeen": RunReport(date="2026-10-09", recorded=5)}
    batch = result.received["ParseFeeds"].value
    assert [f.url for f in batch.failures] == ["https://rss.arxiv.org/rss/cs.PL"]  # one dead feed
    assert len(result.elements["TriageItem"]) == 5

    (digest,) = sent
    assert digest.startswith("# Feed digest — 2026-10-09\n")
    assert "## Must read" in digest and "## Worth a look" in digest
    assert "[A capability model for WebAssembly components]" in digest
    assert "Weekend photos" not in digest and "gardening" not in digest  # triaged out
    assert len(world.store("seen").keys()) == 5  # dropped items are recorded too


def test_each_item_is_triaged_alone():
    """No node in any child run receives more than one item, and no model call
    made for one item contains another item's text."""
    backend = StubLLM()
    result = execute(assemble(PARENT, backend=backend, world=_world([])), Tick())
    titles = [u.value.title for u in result.received["TriageItem"]]
    for run in result.elements["TriageItem"]:
        own = run.received["ClassifyItem"].value.title
        assert isinstance(run.received["ClassifyItem"], Untrusted)
        assert all(not isinstance(v, list | tuple) for v in run.received.values())
        others = [t for t in titles if t != own]
        per_item = [
            c for c in backend.calls if c.task in ("triage", "summarise") and own in c.prompt
        ]
        assert per_item and all(o not in c.prompt for c in per_item for o in others)


def test_a_second_tick_publishes_no_item_twice():
    sent: list[str] = []
    world = _world(sent)
    graph = assemble(PARENT, backend=StubLLM(), world=world)
    execute(graph, Tick())
    second = execute(graph, Tick())
    assert len(sent) == 1
    assert second.terminals == {"RecordSeen": RunReport(date="2026-10-09", recorded=0)}
    assert second.elements["TriageItem"] == []  # nothing new, so no child run and no model call


def test_a_quiet_run_makes_no_digest_call_and_publishes_nothing():
    sent: list[str] = []
    backend = StubLLM()
    quiet = "<rss><channel><item><title>Weekend photos</title><guid>1</guid></item></channel></rss>"
    world = _world(sent, web={"https://lobste.rs/t/plt.rss": quiet})
    result = execute(assemble(PARENT, backend=backend, world=world), Tick())
    assert sent == []
    assert [c.task for c in backend.calls] == ["triage"]
    assert result.terminals["RecordSeen"].recorded == 1  # considered, so not triaged again


def test_nothing_is_recorded_if_a_model_call_fails():
    """`RecordSeen` is last: a failure upstream leaves the store untouched, and
    the next run considers the same items again."""

    class Failing:
        def generate(self, request: LLMRequest) -> LLMResponse:
            raise UsageLimitReached("window exhausted")

    world = _world([])
    with pytest.raises(Exception, match="element 0 of per-item node 'TriageItem' failed"):
        execute(assemble(PARENT, backend=Failing(), world=world), Tick())
    assert world.store("seen").keys() == []


def test_the_run_trace_is_schema_valid_and_shows_the_join_and_the_map():
    result = execute(assemble(PARENT, backend=StubLLM(), world=_world([])), Tick())
    document = result.trace.to_dict()
    assert validate_document(document) == []
    nodes = {n["node"]: n for n in document["nodes"]}
    assert len(nodes["TriageItem"]["elements"]) == 5
    assert result.received["ComposeDigest"][1].date == "2026-10-09"  # the join's second position
    fetch = nodes["FetchFeeds"]
    assert (fetch["input_trust"], fetch["output_trust"]) == ("trusted", "untrusted")
    assert [c["interface"] for c in nodes["DropSeen"]["crossings"]] == ["aap:caps/state-read@0.1.0"]
    assert [c["interface"] for c in nodes["RecordSeen"]["crossings"]] == ["aap:caps/state-rw@0.1.0"]


# ── Node bodies worth pinning on their own ───────────────────────────


@pytest.mark.parametrize(
    ("reply", "expected"),
    [
        ("security must_read", (Category.SECURITY, Importance.MUST_READ)),
        ("Research, worth-a-look.", (Category.RESEARCH, Importance.WORTH_A_LOOK)),
        ("**release** `skip`", (Category.RELEASE, Importance.SKIP)),
        ("I cannot classify this.", (Category.OTHER, Importance.SKIP)),
        ("urgent top_priority", (Category.OTHER, Importance.SKIP)),  # not in either closed set
        ("", (Category.OTHER, Importance.SKIP)),
    ],
)
def test_a_model_reply_maps_onto_the_closed_sets(reply, expected):
    assert parse_verdict(reply) == expected


def test_the_batch_limit_is_round_robin_across_feeds():
    def item(feed: str, n: int) -> Untrusted[FeedItem]:
        return Untrusted(FeedItem(f"{feed}{n}", feed, "t", "", "", ""))

    busy = [item("busy", n) for n in range(100)]
    quiet = [item("quiet", n) for n in range(3)]
    taken = limit_batch((*busy, *quiet))
    assert len(taken) == MAX_PER_RUN
    assert sum(1 for t in taken if t.value.feed == "quiet") == 3  # not starved


def test_an_items_text_cannot_add_structure_to_the_digest():
    hostile = ItemVerdict(
        id="1",
        feed="f",
        title="x](https://evil.example) [click\n# Injected heading",
        link="https://a.example/p",
        category=Category.OTHER,
        importance=Importance.MUST_READ,
        summary="fine\n\n## Another heading\n- another item",
        kept=True,
    )
    text = render_digest(Digest("2026-10-09", "over\n# view", (hostile,), ("1",)))
    lines = text.splitlines()
    assert [line for line in lines if line.startswith("#")] == [
        "# Feed digest — 2026-10-09",
        "## Must read",
    ]
    assert sum(line.startswith("- ") for line in lines) == 1
    assert "](https://evil.example)" not in text


# ── The driver ───────────────────────────────────────────────────────


def _config(tmp_path: Path, server, **kw) -> Config:
    return Config(
        var_dir=tmp_path / "var",
        backend=StubLLM(),
        graph=serve.retarget(PARENT, ["127.0.0.1"]),
        subscriptions=(server.url("/rss"), server.url("/atom")),
        clock=lambda: FIXED,
        **kw,
    )


ROUTES = {"/rss": ok(RSS), "/atom": ok(ATOM)}


def test_one_tick_against_the_fixture_server(tmp_path):
    """The `feed-triage-service` scenario: a digest is written, the seen-store
    records the new items, and a second tick writes no item twice."""
    with serving(ROUTES) as server:
        config = _config(tmp_path, server)
        assert serve.run_once(config) == serve.EXIT_OK
        var = tmp_path / "var"
        digest = (var / "digests" / "2026-10-09.md").read_text()
        assert "A capability model for WebAssembly components" in digest
        assert (var / "digests" / "2026-10-09.html").exists()
        assert len(json.loads((var / "state" / "seen.json").read_text())) == 5

        assert serve.run_once(config) == serve.EXIT_OK
        assert (var / "digests" / "2026-10-09.md").read_text() == digest
        runs = sorted(p.name for p in (var / "runs").iterdir())
        assert len(runs) == 2
        first = json.loads((var / "runs" / runs[0] / "run.json").read_text())
        second = json.loads((var / "runs" / runs[1] / "run.json").read_text())
        assert first["outcome"] == "ok" and first["counts"]["items_triaged"] == 5
        assert first["counts"]["published"] == 1 and first["digest"] == "digests/2026-10-09.md"
        assert second["counts"]["items_new"] == 0 and second["counts"]["published"] == 0
        assert second["counts"]["model_calls"] == 0
        assert (
            validate_document(json.loads((var / "runs" / runs[0] / "trace.json").read_text())) == []
        )


def test_every_file_a_run_writes_is_under_var(tmp_path):
    with serving(ROUTES) as server:
        serve.run_once(_config(tmp_path, server))
    assert [p.name for p in tmp_path.iterdir()] == ["var"]
    assert sorted(p.name for p in (tmp_path / "var").iterdir()) == [
        "digests",
        "runs",
        "serve.lock",
        "state",
    ]


def test_the_default_var_directory_is_inside_the_repository_and_ignored():
    assert serve.VAR_DIR == REPO_ROOT / "var"
    ignored = subprocess.run(
        ["git", "check-ignore", "-q", "var/state/seen.json"], cwd=REPO_ROOT, check=False
    )
    assert ignored.returncode == 0


def test_a_second_driver_is_refused_while_one_holds_the_lock(tmp_path, capsys):
    with serving(ROUTES) as server:
        config = _config(tmp_path, server)
        with serve.Lock(config.var_dir):
            assert serve.run_once(config) == serve.EXIT_LOCKED
        assert "another driver holds" in capsys.readouterr().err
        assert not (config.var_dir / "runs").exists()  # it ran nothing
        assert serve.run_once(config) == serve.EXIT_OK  # released, so the next one runs


def test_a_subscription_outside_the_allowlist_is_a_configuration_error(tmp_path, capsys):
    with serving(ROUTES) as server:
        config = _config(tmp_path, server)
        config.subscriptions = ("https://evil.example/feed",)
        assert serve.run_once(config) == serve.EXIT_CONFIG
        assert "evil.example" in capsys.readouterr().err
        assert server.requests == []


def test_a_failed_tick_is_recorded_and_marks_nothing_seen(tmp_path):
    class Failing:
        calls = ()

        def generate(self, request):
            raise RuntimeError("model unavailable")

    with serving(ROUTES) as server:
        config = _config(tmp_path, server)
        config.backend = Failing()
        assert serve.run_once(config) == serve.EXIT_FAILED
        (run,) = (config.var_dir / "runs").iterdir()
        record = json.loads((run / "run.json").read_text())
        assert record["outcome"] == "failed" and "model unavailable" in record["error"]
        assert (run / "error.txt").exists()
        assert not (config.var_dir / "state" / "seen.json").exists()


def test_a_usage_limit_has_its_own_outcome_and_exit_code(tmp_path):
    class Limited:
        calls = ()

        def generate(self, request):
            raise UsageLimitReached("seven_day window at 95%")

    with serving(ROUTES) as server:
        config = _config(tmp_path, server)
        config.backend = Limited()
        assert serve.run_once(config) == serve.EXIT_USAGE_LIMIT
        (run,) = (config.var_dir / "runs").iterdir()
        assert json.loads((run / "run.json").read_text())["outcome"] == "usage-limit"


def test_the_interval_loop_ticks_repeatedly_under_one_lock(tmp_path, capsys):
    with serving(ROUTES) as server:
        config = _config(tmp_path, server)
        assert serve.run_every(config, 0.0, limit=3) == serve.EXIT_OK
        assert len(list((config.var_dir / "runs").iterdir())) == 3
        assert capsys.readouterr().out.count("ok in") == 3


def test_the_report_summarises_the_recorded_runs(tmp_path):
    with serving(ROUTES) as server:
        config = _config(tmp_path, server)
        serve.run_every(config, 0.0, limit=2)
    summary = serve.report(config.var_dir)
    assert summary["runs"] == 2 and summary["outcomes"] == {"ok": 2}
    assert summary["totals"]["items_triaged"] == 5 and summary["totals"]["published"] == 1
    assert summary["digests"] == ["2026-10-09.md"]
    assert summary["backends"] == ["StubLLM"] and summary["tiers"] == ["host"]


def test_the_command_line_runs_a_stub_tick(tmp_path):
    """`--once` end to end through the CLI, offline: an empty subscriptions store
    means nothing is fetched, and the stub means no model is called."""
    var = tmp_path / "var"
    (var / "state").mkdir(parents=True)
    (var / "state" / "subscriptions.json").write_text(json.dumps({"feeds": "# none yet\n"}))
    done = subprocess.run(
        [sys.executable, "-m", "poc.serve", "--once", "--backend", "stub", "--var", str(var)],
        cwd=REPO_ROOT,
        env={"PYTHONPATH": f"{REPO_ROOT / 'scripts'}:{REPO_ROOT}", "PATH": "/usr/bin:/bin"},
        capture_output=True,
        text=True,
        check=False,
    )
    assert done.returncode == 0, done.stderr
    assert "0/0 feeds" in done.stdout and "quiet" in done.stdout


def test_retargeting_rewrites_the_capability_type_everywhere_it_appears():
    retargeted = serve.retarget(PARENT, ["b.example", "a.example"])
    new = "HTTPClient<['a.example', 'b.example']>"
    assert new in retargeted["parameters"] and new in retargeted["capabilities"]
    fetch = next(n for n in retargeted["nodes"] if n["name"] == "FetchFeeds")
    assert new in fetch["inputs"]
    assert serve.allowlist(retargeted) == {"a.example", "b.example"}
    assert "simonwillison.net" in json.dumps(PARENT)  # the canonical graph is untouched
    assert validate_graph_dicts([retargeted, CHILD]) == []
