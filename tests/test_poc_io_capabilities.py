"""The capabilities the feed-triage service needed and the runtime lacked.

Three kinds, each made real enough to run a service on:

* `StateHandle<'name', read|read-write>` — node-local state as a capability.
* `HTTPClient<[hosts]>` performing bounded real fetches, canned by default.
* `Notifier<'digest'>` bound to a local file.

Covers the `signal-graph-runtime` requirements added by
`build-feed-triage-and-generation-experiment`:
  - Node-local state is a typed capability
  - Outbound HTTP performs bounded real fetches

No test here touches the network: live fetches go to a server on 127.0.0.1.
"""

from __future__ import annotations

import json

import pytest
from type_parser import CAPABILITY_HEADS, is_assignable, parse_type

from poc import digest
from poc.graph import validate_graph_dicts
from poc.handles import (
    CapabilityError,
    FetchError,
    HTTPClient,
    Notifier,
    ReadStateHandle,
    ReadWriteStateHandle,
    StateStore,
    World,
    provision,
)
from poc.llm import StubLLM
from poc.sandbox.interfaces import (
    CAPABILITY_INTERFACES,
    CAPABILITY_KINDS,
    PAPER2_INTERFACES,
    PAPER2_KINDS,
    STATE_READ,
    STATE_RW,
    interface_for,
)
from tests.feed_fixtures import ok, redirect, serving, slow


def _assignable(actual: str, target: str) -> bool:
    return is_assignable(parse_type(actual), parse_type(target))


# ── StateHandle: the type ────────────────────────────────────────────


def test_state_handle_is_a_capability_kind():
    assert "StateHandle" in CAPABILITY_HEADS
    assert "StateHandle" in CAPABILITY_KINDS


def test_read_write_narrows_to_read_and_never_the_reverse():
    assert _assignable("StateHandle<'seen', read-write>", "StateHandle<'seen', read>")
    assert not _assignable("StateHandle<'seen', read>", "StateHandle<'seen', read-write>")
    assert _assignable("StateHandle<'seen', read>", "StateHandle<'seen', read>")


def test_a_handle_for_another_store_is_not_assignable():
    assert not _assignable("StateHandle<'other', read-write>", "StateHandle<'seen', read>")


def test_each_mode_maps_to_its_own_interface():
    assert interface_for("StateHandle<'seen', read>") == STATE_READ
    assert interface_for("StateHandle<'seen', read-write>") == STATE_RW


def test_paper_2s_vocabulary_is_unmoved_by_the_new_kind():
    """Paper 2 counts seven kinds and eight interfaces. State came later and is
    counted apart, so a figure in a paper that never exercised it cannot move."""
    assert len(PAPER2_KINDS) == 7 and "StateHandle" not in PAPER2_KINDS
    assert len(PAPER2_INTERFACES) == 8
    assert {STATE_READ, STATE_RW} == CAPABILITY_INTERFACES - PAPER2_INTERFACES


def _composition(parent_cap: str, child_cap: str) -> list[str]:
    """Validate a parent routing `parent_cap` into a child declaring `child_cap`."""
    child = {
        "name": "Child",
        "parameters": ["Req", child_cap],
        "capabilities": [child_cap],
        "nodes": [{"name": "Leaf", "inputs": ["Req", child_cap], "output": "Done"}],
        "data_edges": [],
    }
    parent = {
        "name": "Parent",
        "parameters": ["Req", parent_cap],
        "capabilities": [parent_cap],
        "nodes": [{"name": "Child", "inputs": ["Req", parent_cap], "output": "Done"}],
        "data_edges": [],
    }
    return validate_graph_dicts([parent, child])


def test_validation_accepts_a_read_write_handle_routed_to_a_read_slot():
    assert _composition("StateHandle<'seen', read-write>", "StateHandle<'seen', read>") == []


def test_validation_rejects_a_handle_for_a_different_store():
    errors = _composition("StateHandle<'other', read-write>", "StateHandle<'seen', read>")
    assert any("not assignable" in e for e in errors), errors


def test_validation_rejects_a_read_handle_routed_to_a_read_write_slot():
    errors = _composition("StateHandle<'seen', read>", "StateHandle<'seen', read-write>")
    assert any("not assignable" in e for e in errors), errors


# ── StateHandle: the handles ─────────────────────────────────────────


def _provision(cap: str, world: World):
    return provision(cap, backend=StubLLM(), stores={}, world=world)


def test_a_read_handle_has_no_way_to_write():
    handle = _provision("StateHandle<'seen', read>", World())
    assert isinstance(handle, ReadStateHandle)
    assert not hasattr(handle, "put") and not hasattr(handle, "delete")


def test_a_reader_and_a_writer_of_one_name_reach_the_same_state():
    world = World()
    writer = _provision("StateHandle<'seen', read-write>", world)
    reader = _provision("StateHandle<'seen', read>", world)
    assert isinstance(writer, ReadWriteStateHandle)
    assert reader.get("k") is None
    writer.put("k", "v")
    assert reader.get("k") == "v"
    writer.delete("k")
    assert reader.get("k") is None


def test_stores_of_different_names_are_separate():
    world = World()
    _provision("StateHandle<'seen', read-write>", world).put("k", "v")
    assert _provision("StateHandle<'subscriptions', read>", world).get("k") is None


def test_state_survives_a_restart(tmp_path):
    """A value put by one process is read back by the next: a fresh `World` over
    the same directory stands in for the restart."""
    _provision("StateHandle<'seen', read-write>", World(state_dir=tmp_path)).put(
        "item", "2026-10-09"
    )
    reborn = _provision("StateHandle<'seen', read>", World(state_dir=tmp_path))
    assert reborn.get("item") == "2026-10-09"
    assert json.loads((tmp_path / "seen.json").read_text()) == {"item": "2026-10-09"}


def test_a_write_replaces_the_file_atomically(tmp_path):
    store = StateStore("seen", tmp_path / "seen.json")
    store.put("a", "1")
    store.put("b", "2")
    assert sorted(p.name for p in tmp_path.iterdir()) == ["seen.json"]  # no temp file left
    assert StateStore("seen", tmp_path / "seen.json").keys() == ["a", "b"]


@pytest.mark.parametrize("name", ["../escape", "Seen", "a/b", "", "x" * 80])
def test_a_store_name_that_is_not_a_safe_filename_is_refused(name):
    with pytest.raises(ValueError):
        World().store(name)


def test_an_unknown_state_mode_is_refused():
    with pytest.raises(ValueError, match="mode"):
        _provision("StateHandle<'seen', append>", World())


# ── HTTPClient: canned by default ────────────────────────────────────


def test_the_default_mode_performs_no_network_io():
    client = HTTPClient(frozenset({"feeds.example.com"}), {"https://feeds.example.com/a": "body"})
    assert not client.live
    assert client.get("https://feeds.example.com/a") == "body"
    assert client.fetch("https://feeds.example.com/a").body == "body"
    missing = client.fetch("https://feeds.example.com/missing")
    assert not missing.ok and missing.error


def test_fetch_refuses_an_off_list_host_by_raising_not_by_returning():
    """A transport failure is a value; a reach outside the allowlist is not."""
    client = HTTPClient(frozenset({"feeds.example.com"}))
    with pytest.raises(CapabilityError, match="outside its allowlist"):
        client.fetch("https://evil.example/")


# ── HTTPClient: live, against a local server ─────────────────────────


def _live(*hosts: str, **kwargs) -> HTTPClient:
    return HTTPClient(frozenset(hosts), live=True, **kwargs)


def test_a_live_fetch_returns_the_body():
    with serving({"/feed": ok("<rss/>")}) as server:
        assert _live("127.0.0.1").get(server.url("/feed")) == "<rss/>"


def test_a_live_fetch_of_an_off_list_host_makes_no_request():
    with serving({"/feed": ok("<rss/>")}) as server:
        with pytest.raises(CapabilityError, match="outside its allowlist"):
            _live("feeds.example.com").get(server.url("/feed"))
        assert server.requests == []


def test_a_redirect_that_leaves_the_allowlist_is_refused_at_the_handle():
    """`127.0.0.1` is allowlisted and bounces to `localhost` — the same machine,
    a different host, and not one the graph named."""
    routes = {"/secret": ok("should not be fetched")}
    with serving(routes) as server:
        routes["/hop"] = redirect(server.url("/secret", host="localhost"))  # type: ignore[index]
        with pytest.raises(CapabilityError, match="outside its allowlist"):
            _live("127.0.0.1").get(server.url("/hop"))
        with pytest.raises(CapabilityError, match="outside its allowlist"):
            _live("127.0.0.1").fetch(server.url("/hop"))
        assert "/secret" not in server.requests


def test_a_redirect_within_the_allowlist_is_followed():
    routes = {"/final": ok("arrived")}
    with serving(routes) as server:
        routes["/hop"] = redirect(server.url("/final"))  # type: ignore[index]
        assert _live("127.0.0.1").get(server.url("/hop")) == "arrived"


def test_an_oversized_response_fails_and_returns_no_partial_body():
    with serving({"/big": ok("x" * 5000)}) as server:
        client = _live("127.0.0.1", max_bytes=1000)
        with pytest.raises(FetchError, match="cap"):
            client.get(server.url("/big"))
        result = client.fetch(server.url("/big"))
        assert not result.ok and result.body == "" and "cap" in result.error


def test_a_slow_response_times_out_as_a_value_from_fetch():
    with serving({"/slow": slow(1.5)}) as server:
        result = _live("127.0.0.1", timeout=0.2).fetch(server.url("/slow"))
        assert not result.ok and result.body == ""


def test_an_error_status_is_a_failed_fetch_not_a_capability_error():
    with serving({}) as server:
        result = _live("127.0.0.1").fetch(server.url("/missing"))
        assert not result.ok and "404" in result.error
        with pytest.raises(FetchError, match="404"):
            _live("127.0.0.1").get(server.url("/missing"))


@pytest.mark.parametrize("url", ["file:///etc/passwd", "ftp://127.0.0.1/x", "gopher://127.0.0.1/"])
def test_only_http_and_https_are_http(url):
    with pytest.raises(CapabilityError):
        _live("127.0.0.1", "").get(url)


def test_the_world_decides_whether_http_is_live():
    assert not _provision("HTTPClient<['a.example']>", World()).live
    assert _provision("HTTPClient<['a.example']>", World(live_http=True)).live


# ── Notifier: the local digest ───────────────────────────────────────


def test_a_notifier_only_records_unless_the_world_binds_it():
    notifier = _provision("Notifier<'digest'>", World())
    assert isinstance(notifier, Notifier)
    notifier.notify("hello")
    assert notifier.sent == ["hello"]


def test_the_digest_notifier_writes_dated_markdown_and_html(tmp_path):
    world = World(publishers={"digest": digest.publisher(tmp_path, lambda: "2026-10-09")})
    _provision("Notifier<'digest'>", world).notify("# Feed digest — 2026-10-09\n\n- one\n")
    assert (tmp_path / "2026-10-09.md").read_text().startswith("# Feed digest")
    page = (tmp_path / "2026-10-09.html").read_text()
    assert "<h1>Feed digest — 2026-10-09</h1>" in page and "<li>one</li>" in page
    assert digest.latest(tmp_path) == tmp_path / "2026-10-09.html"


def test_a_second_notification_the_same_day_appends(tmp_path):
    digest.publish(tmp_path, "2026-10-09", "# First\n")
    digest.publish(tmp_path, "2026-10-09", "# Second\n")
    text = (tmp_path / "2026-10-09.md").read_text()
    assert text.index("# First") < text.index("---") < text.index("# Second")
    assert sorted(p.name for p in tmp_path.iterdir()) == ["2026-10-09.html", "2026-10-09.md"]


def test_the_page_escapes_markup_an_item_planted():
    page = digest.render_html(
        "- <script>alert(1)</script> <img src=x onerror=alert(1)>\n", title="<t>"
    )
    assert "<script>" not in page and "<img" not in page
    assert "&lt;script&gt;" in page and "<title>&lt;t&gt;</title>" in page


def test_only_http_links_become_anchors():
    page = digest.render_html(
        "- [ok](https://a.example/x) [bad](javascript:alert(1)) [data](data:text/html,x)\n",
        title="t",
    )
    assert '<a href="https://a.example/x"' in page
    assert "javascript:" in page and 'href="javascript:' not in page
    assert 'href="data:' not in page


def test_a_link_cannot_break_out_of_its_attribute():
    page = digest.render_html('- [x](https://a.example/"onmouseover="alert(1))\n', title="t")
    assert 'onmouseover="alert' not in page


def test_a_digest_date_must_be_a_date(tmp_path):
    with pytest.raises(ValueError):
        digest.publish(tmp_path, "../../etc", "x")
