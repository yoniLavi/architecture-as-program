"""The feed-triage service on the confined tier.

Nine nodes of the service hold a capability, and each has a Rust body compiled to
a WASM component. These tests hold those components to the same three standards
the customer-support ports are held to:

* the interfaces a component imports are exactly those derived from its node's
  `with` clause — and a component built to over-import is caught for it;
* a body that reaches past its grant is stopped by the artifact, not by manners;
* the two tiers agree: same outputs, same model prompts, same trace once the
  tier field is set aside.

Needs `wasmtime` (the `poc` group); skipped without it. The components are
committed, so no Rust toolchain is needed to run this.
"""

from __future__ import annotations

import pytest

from poc import serve
from poc.feed_nodes import (
    classify_item,
    publish_digest,
    render_digest,
    start_run,
)
from poc.feed_values import (
    Category,
    Digest,
    FeedItem,
    Importance,
    ItemVerdict,
    SubscriptionList,
    Tick,
)
from poc.graph import assemble, load_graph_dict
from poc.handles import (
    CapabilityError,
    Clock,
    HTTPClient,
    InferenceLLM,
    Notifier,
    ReadStateHandle,
    StateStore,
    WallTime,
    World,
)
from poc.llm import LLMRequest, LLMResponse, StubLLM
from poc.runtime import execute
from poc.sandbox import available
from poc.sandbox.interfaces import (
    HTTP_CLIENT,
    INFERENCE_LLM,
    STATE_READ,
    STATE_RW,
    TYPES,
    expected_imports,
)
from poc.values import Untrusted
from tests.feed_fixtures import ATOM, RSS, ok, serving

pytestmark = pytest.mark.skipif(not available(), reason="needs wasmtime (the `poc` group)")

if available():
    from poc.sandbox.feed_nodes import (
        FEED_COMPONENTS,
        FEED_SANDBOX_REGISTRY,
        classify_item_sandbox,
        drop_seen_sandbox,
        fetch_feeds_sandbox,
        publish_digest_sandbox,
        start_run_sandbox,
    )
    from poc.sandbox.host import (
        Sandbox,
        SandboxError,
        capability_imports,
        component_imports,
        ungranted_imports,
        wasi_imports,
    )

PARENT = load_graph_dict("feed-triage")
FIXED = WallTime(seconds=1791547200, nanoseconds=0)  # 2026-10-09T12:00:00Z
FEEDS = {
    "https://lobste.rs/t/plt.rss": RSS,
    "https://simonwillison.net/atom/everything/": ATOM,
}


# ── The derivation: `with` clause against built binary ───────────────


def test_every_port_has_a_component_and_every_component_a_port():
    assert set(FEED_COMPONENTS) == set(FEED_SANDBOX_REGISTRY)
    confined = {n for nodes in serve.CONFINED_NODES.values() for n in nodes}
    assert confined == set(FEED_SANDBOX_REGISTRY)


@pytest.mark.parametrize("node", sorted(FEED_COMPONENTS) if available() else [])
def test_a_components_imports_are_exactly_those_its_with_clause_derives(node):
    stem, component = FEED_COMPONENTS[node]
    derived = expected_imports(load_graph_dict(stem), node)
    assert component_imports(component) == derived
    assert ungranted_imports(component, derived) == []
    assert wasi_imports(component) == []  # nothing outside the capability vocabulary


def test_the_services_authority_is_readable_off_its_import_lists():
    """One component imports HTTP, one imports the state writer, and no component
    imports HTTP together with a model."""
    imports = {node: capability_imports(c) for node, (_, c) in FEED_COMPONENTS.items()}
    assert [n for n, i in imports.items() if HTTP_CLIENT in i] == ["FetchFeeds"]
    assert [n for n, i in imports.items() if STATE_RW in i] == ["RecordSeen"]
    assert imports["DropSeen"] == [STATE_READ]
    assert not [n for n, i in imports.items() if HTTP_CLIENT in i and INFERENCE_LLM in i]


def test_the_gate_rejects_a_classifier_built_to_exfiltrate():
    """A real binary with `ClassifyItem`'s signature whose world also imports
    `http-client`. Held to `ClassifyItem`'s clause, it over-grants exactly that."""
    derived = expected_imports(load_graph_dict("triage-item"), "ClassifyItem")
    assert derived == sorted([INFERENCE_LLM, TYPES])
    assert ungranted_imports("hostile_exfiltrating_classifier", derived) == [HTTP_CLIENT]


def test_the_exfiltrating_classifier_cannot_even_be_instantiated():
    """Linked against what `ClassifyItem` is granted, the import it needs is
    unsatisfied, and the refusal lands before any of its code runs."""
    with pytest.raises(SandboxError, match="not granted") as caught:
        Sandbox("hostile_exfiltrating_classifier", {INFERENCE_LLM: {"infer": lambda *_: "x"}})
    assert "http-client" in str(caught.value)


# ── What a confined body cannot do ───────────────────────────────────


def test_a_confined_reader_of_the_seen_store_has_no_function_to_write_with():
    """`StateHandle<'seen', read>` on the confined tier: the component's only
    state import is `state-read`, which has `get` and nothing else."""
    assert capability_imports("node_drop_seen") == [STATE_READ]
    store = StateStore("seen")
    store.put("old", "2026-10-01")
    old = Untrusted(FeedItem("old", "f", "t", "", "", ""))
    new = Untrusted(FeedItem("new", "f", "t", "", "", ""))
    assert drop_seen_sandbox((old, new, new), ReadStateHandle("seen", store)) == (new,)
    assert store.keys() == ["old"]


def test_a_confined_fetch_outside_the_allowlist_is_refused_at_the_crossing():
    http = HTTPClient(frozenset({"feeds.example.com"}), {"https://evil.example/x": "secret"})
    with pytest.raises(CapabilityError, match="outside its allowlist"):
        fetch_feeds_sandbox(SubscriptionList(("https://evil.example/x",)), http)


def test_a_failed_permitted_fetch_is_a_value_on_the_confined_tier():
    http = HTTPClient(frozenset({"feeds.example.com"}), {"https://feeds.example.com/a": "<rss/>"})
    urls = ("https://feeds.example.com/a", "https://feeds.example.com/gone")
    batch = fetch_feeds_sandbox(SubscriptionList(urls), http).value
    assert [d.url for d in batch.documents] == [urls[0]]
    assert [(f.url, f.error) for f in batch.failures] == [(urls[1], "no response")]


def test_a_confined_live_fetch_cannot_be_redirected_off_the_allowlist():
    routes = {"/secret": ok("no")}
    with serving(routes) as server:
        routes["/hop"] = (302, {"Location": server.url("/secret", host="localhost")}, b"")  # type: ignore[index]
        http = HTTPClient(frozenset({"127.0.0.1"}), live=True)
        batch = fetch_feeds_sandbox(SubscriptionList((server.url("/hop"),)), http).value
        assert batch.documents == ()
        assert "redirect refused" in batch.failures[0].error
        assert "/secret" not in server.requests  # the hop was never followed


# ── The two tiers agree, body by body ────────────────────────────────


@pytest.mark.parametrize(
    "seconds",
    [0, 86_399, 86_400, 951_782_400, 1_709_164_800, 1_791_547_200, 4_102_444_799, 4_102_444_800],
)
def test_the_rust_date_matches_the_python_date(seconds):
    """Epoch, a day boundary, two leap days, today, and a century boundary."""
    clock = Clock(_source=lambda: WallTime(seconds=seconds, nanoseconds=0))
    assert start_run_sandbox(Tick(), clock) == start_run(Tick(), clock)


class _Says:
    """A backend that always answers the same thing."""

    def __init__(self, reply: str):
        self.reply = reply
        self.calls: list[LLMRequest] = []

    def generate(self, request: LLMRequest) -> LLMResponse:
        self.calls.append(request)
        return LLMResponse(text=self.reply)


@pytest.mark.parametrize(
    "reply",
    [
        "security must_read",
        "Research, worth-a-look.",
        "**release** `skip`",
        "I cannot classify this.",
        "MUST_READ tooling",
        "",
        "other\nworth_a_look\nignore previous instructions",
    ],
)
def test_both_tiers_map_a_model_reply_onto_the_closed_sets_alike(reply):
    item = Untrusted(FeedItem("id", "https://f.example/rss", "A title", "", "", "Some text."))
    host_llm, confined_llm = _Says(reply), _Says(reply)
    host = classify_item(item, InferenceLLM(host_llm))
    confined = classify_item_sandbox(item, InferenceLLM(confined_llm))
    assert confined == host
    assert confined_llm.calls == host_llm.calls  # the same system text and prompt, verbatim


def test_both_tiers_render_a_hostile_digest_identically():
    entries = (
        ItemVerdict(
            "1",
            "f",
            "x](https://evil.example) [click\n# Injected",
            "https://a.example/p",
            Category.SECURITY,
            Importance.MUST_READ,
            "fine\n\n## Another\n- item",
            True,
        ),
        ItemVerdict("2", "f", "", "", Category.OTHER, Importance.WORTH_A_LOOK, "No title.", True),
        ItemVerdict(
            "3",
            "f",
            "Später — naïve café ☕",
            "",
            Category.TOOLING,
            Importance.WORTH_A_LOOK,
            "ü",
            True,
        ),
    )
    digest = Digest("2026-10-09", "An overview\nover two lines.", entries, ("1", "2", "3"))
    host, confined = Notifier("digest"), Notifier("digest")
    assert publish_digest_sandbox(digest, confined) == publish_digest(digest, host)
    assert confined.sent == host.sent == [render_digest(digest)]


# ── The two tiers agree, end to end ──────────────────────────────────


def _tick(confined: bool):
    sent: list[str] = []
    world = World(web=FEEDS, publishers={"digest": sent.append}, clock=lambda: FIXED)
    world.store("subscriptions").put("feeds", "\n".join(FEEDS) + "\nhttps://rss.arxiv.org/x\n")
    backend = StubLLM()
    sandbox = serve.CONFINED_NODES if confined else {}
    graph = assemble(PARENT, backend=backend, world=world, sandbox=sandbox.get("FeedTriage", ()))
    result = execute(graph, Tick(), sandbox=sandbox)
    return result, sent, backend, world


def _without_tiers(trace: dict) -> dict:
    """A structural trace with every node's tier erased, at every depth."""
    return {
        "graph": trace["graph"],
        "nodes": [
            {
                **{k: v for k, v in node.items() if k not in ("tier", "elements", "subgraph")},
                "elements": [_without_tiers(run) for run in node.get("elements", [])],
            }
            for node in trace["nodes"]
        ],
    }


def test_a_whole_tick_is_the_same_on_both_tiers():
    """Outputs, the published digest, the seen-store, every model call, and the
    trace's structure — all identical once the tier field is set aside."""
    host, host_sent, host_backend, host_world = _tick(confined=False)
    conf, conf_sent, conf_backend, conf_world = _tick(confined=True)

    assert conf.terminals == host.terminals
    assert conf_sent == host_sent and len(host_sent) == 1
    assert conf_world.store("seen").keys() == host_world.store("seen").keys()
    assert conf_backend.calls == host_backend.calls
    assert _without_tiers(conf.trace.structural()) == _without_tiers(host.trace.structural())


def test_a_confined_tick_runs_every_capability_holding_node_as_a_component():
    result, _, _, _ = _tick(confined=True)
    assert {n for n, t in result.tiers.items() if t == "sandbox"} == set(
        serve.CONFINED_NODES["FeedTriage"]
    )
    assert {n for n, t in result.tiers.items() if t == "host"} == {
        "ParseFeeds",
        "LimitBatch",
        "SelectItems",
    }
    for run in result.elements["TriageItem"]:
        assert run.tiers["ClassifyItem"] == "sandbox"
        assert run.tiers.get("SummariseItem", "sandbox") == "sandbox"
        assert run.tiers.get("SkipItem", "host") == "host"


def test_the_driver_runs_a_confined_tick_against_the_fixture_server(tmp_path):
    with serving({"/rss": ok(RSS), "/atom": ok(ATOM)}) as server:
        config = serve.Config(
            var_dir=tmp_path / "var",
            backend=StubLLM(),
            graph=serve.retarget(PARENT, ["127.0.0.1"]),
            subscriptions=(server.url("/rss"), server.url("/atom")),
            clock=lambda: FIXED,
            confined=True,
        )
        assert serve.run_once(config) == serve.EXIT_OK
    text = (tmp_path / "var" / "digests" / "2026-10-09.md").read_text()
    assert "A capability model for WebAssembly components" in text
    record = next((tmp_path / "var" / "runs").iterdir()) / "run.json"
    assert '"tier": "confined"' in record.read_text()


# ── A host binding written short is not an ungranted capability ──────


def test_a_missing_function_of_a_granted_interface_is_the_hosts_fault_and_says_so():
    """`FetchFeeds` is granted `http-client` and calls its `fetch`. A host that
    binds the interface with only `get` cannot instantiate it — and must not
    report that as the component importing something it was not granted, which
    is what it did to twelve generated `Heartbeat` bodies before this existed."""
    from poc.sandbox.host import IncompleteHostBinding

    with pytest.raises(IncompleteHostBinding) as caught:
        Sandbox("node_fetch_feeds", {HTTP_CLIENT: {"get": lambda url: ""}})
    message = str(caught.value)
    assert "fault in the host adapter" in message and "http-client" in message
    assert "it imports a capability it was not granted" not in message


def test_an_ungranted_interface_is_still_reported_as_ungranted():
    with pytest.raises(SandboxError, match="imports a capability it was not granted") as caught:
        Sandbox("node_fetch_feeds", {})
    assert type(caught.value) is SandboxError  # the plain class, not the host-fault one


def test_the_adapters_bind_every_function_of_the_interfaces_they_link():
    """The fix at its source: an adapter binds an interface whole, so a body that
    replaces the hand-written one may call any function of what the node holds."""
    import re

    from poc.generation import task

    declared = {
        name: set(re.findall(r"^\s*([a-z][a-z0-9-]*): func", body, re.M))
        for name, body in re.findall(
            r"^interface ([a-z0-9-]+) \{\n(.*?)^\}", task.caps_package(), re.M | re.S
        )
    }
    bound: dict[str, set[str]] = {}

    class Recording(Sandbox):
        def __init__(self, _component, caps=None):
            for interface, functions in (caps or {}).items():
                bound.setdefault(interface, set()).update(functions)
            raise SandboxError("recorded")

    import poc.sandbox.feed_nodes as feed_adapters
    import poc.sandbox.nodes as adapters
    from poc.generation.subjects import SUBJECTS

    saved = (adapters.Sandbox, feed_adapters.Sandbox)
    adapters.Sandbox = feed_adapters.Sandbox = Recording  # type: ignore[misc]
    try:
        registry = {
            **adapters.SANDBOX_REGISTRY,
            **FEED_SANDBOX_REGISTRY,
            "Heartbeat": adapters.heartbeat_sandbox,
        }
        for subject in SUBJECTS:
            args = subject.test_inputs()[0]
            with pytest.raises(SandboxError, match="recorded"):
                registry[subject.node](
                    *(args if subject.arity > 1 else (args,)), *subject.handles()
                )
    finally:
        adapters.Sandbox, feed_adapters.Sandbox = saved  # type: ignore[misc]

    for interface, functions in bound.items():
        name = interface.split("/", 1)[-1].split("@", 1)[0]
        wanted = {"now", "resolution"} if name == "wall-clock" else declared[name]
        assert functions == wanted, f"{name}: binds {sorted(functions)}, declares {sorted(wanted)}"


# ── A body swapped into the running service ──────────────────────────


def _substituting(tmp_path, server, node: str, component: str, **kw) -> serve.Config:
    """A driver config running `component`'s file in place of `node`'s body."""
    from poc.sandbox.host import WASM_DIR

    swapped = tmp_path / f"{component}.wasm"
    swapped.write_bytes((WASM_DIR / f"{component}.wasm").read_bytes())
    return serve.Config(
        var_dir=tmp_path / "var",
        backend=StubLLM(),
        graph=serve.retarget(PARENT, ["127.0.0.1"]),
        subscriptions=(server.url("/rss"),),
        clock=lambda: FIXED,
        confined=kw.pop("confined", True),
        substitute={node: swapped},
        **kw,
    )


def test_a_substituted_body_runs_in_the_service_and_is_named_in_the_run_record(tmp_path):
    """Interchangeability, on the graph that runs: another file with the node's
    import set stands in for its body, and the tick is recorded as having used it."""
    import json

    with serving({"/rss": ok(RSS)}) as server:
        config = _substituting(tmp_path, server, "ClassifyItem", "node_classify_item")
        assert serve.run_once(config) == serve.EXIT_OK
    run = json.loads((next((tmp_path / "var" / "runs").iterdir()) / "run.json").read_text())
    swapped = run["substituted"]["ClassifyItem"]
    assert swapped["imports"] == sorted([INFERENCE_LLM, TYPES]) and len(swapped["sha256"]) == 64
    assert run["counts"]["items_triaged"] == 3 and run["outcome"] == "ok"


def test_a_substituted_body_that_over_imports_is_refused_before_the_run(tmp_path, capsys):
    """The gate is not skipped because a body arrived by an unusual route."""
    with serving({"/rss": ok(RSS)}) as server:
        config = _substituting(tmp_path, server, "ClassifyItem", "hostile_exfiltrating_classifier")
        assert serve.run_once(config) == serve.EXIT_CONFIG
        assert server.requests == []  # nothing ran, so nothing was fetched
    err = capsys.readouterr().err
    assert "http-client" in err and "it was not run" in err


def test_a_body_cannot_be_substituted_on_the_host_tier(tmp_path, capsys):
    with serving({"/rss": ok(RSS)}) as server:
        config = _substituting(
            tmp_path, server, "ClassifyItem", "node_classify_item", confined=False
        )
        assert serve.run_once(config) == serve.EXIT_CONFIG
    assert "not running on the confined tier" in capsys.readouterr().err
