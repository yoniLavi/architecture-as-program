"""Attenuation at the routing point.

A parent may route a sub-graph a handle wider than the one the sub-graph declares:
the cross-graph validator accepts it as capability narrowing (`is_assignable`).
Until task 9.1 of `build-feed-triage-and-generation-experiment`, the runtime then
routed the parent's handle *whole*, so narrowing was checked, not enforced: a child
declaring `HTTPClient<['a']>` could fetch from every host the parent's allowlist
named.

These tests are written against the escapes that gap left open. Each builds a
parent that routes a wider handle than the child declares, runs a child node that
reaches for the parent's wider authority, and asserts that the reach fails. One
group per scope the validator narrows on: an HTTP allowlist, an LLM tool set, a
`DBHandle`/`StateHandle` mode, and the banking kinds' payees, caps, orders and
fields. Then the properties the facade must keep: revocation and rotation still
reach the routed instance through its caretaker, narrowing composes across two
boundaries, the trace keeps the parent's instance label, and a handle routed at its
declared type passes through untouched.

Host-tier honesty, as everywhere in this runtime: the facade's surface is the
enforcement, and a hostile Python body can still reach around the object model.
The facade does not change that, and the confined-tier test at the end is the one
that runs the narrowed handle behind a WIT boundary.
"""

from __future__ import annotations

import copy
from collections.abc import Callable

import pytest

from poc.bank import MemoryBank
from poc.graph import AssembledGraph, assemble, load_graph_dict
from poc.handles import (
    AppendDBHandle,
    CapabilityError,
    HTTPClient,
    ReadDBHandle,
    ReadStateHandle,
    ReadWriteDBHandle,
    RevokedCapabilityError,
    ToolLLM,
    World,
)
from poc.llm import LLMRequest, LLMResponse, StubLLM, ToolCall
from poc.nodes import REGISTRY
from poc.runtime import execute
from poc.sandbox.interfaces import interface_for
from poc.values import CustomerRequest, DeliveryConfirmation, HTTPRoute
from tests.feed_fixtures import ok, redirect, serving

REQUEST = CustomerRequest(session_id="s", body="probe")
DONE = DeliveryConfirmation(session_id="s", delivered=True)


# ── Fixtures: a parent routing `wide` to a child declaring `narrow` ──────────


def _pair(wide: str, narrow: str, *, identity: str | None = None) -> tuple[dict, dict]:
    """A one-node parent whose node `Inner` is a sub-graph, and that sub-graph: one
    leaf `Probe` holding the child's declared capability."""
    child = {
        "name": "Inner",
        "parameters": ["CustomerRequest", narrow],
        "capabilities": [narrow],
        "nodes": [
            {
                "name": "Probe",
                "inputs": ["CustomerRequest", narrow],
                "output": "DeliveryConfirmation",
            }
        ],
        "data_edges": [],
    }
    node: dict = {
        "name": "Inner",
        "inputs": ["CustomerRequest", wide],
        "output": "DeliveryConfirmation",
    }
    if identity:
        node["capability_identities"] = {wide: identity}
    parent = {
        "name": "Outer",
        "parameters": ["CustomerRequest", wide],
        "capabilities": [wide],
        "nodes": [node],
        "data_edges": [],
    }
    return parent, child


def _run(
    wide: str,
    narrow: str,
    probe: Callable[[object], None],
    *,
    monkeypatch: pytest.MonkeyPatch,
    backend=None,
    stores=None,
    world: World | None = None,
):
    """Assemble the pair, run it with `probe` as the child's body, and return the
    assembled parent (so a test can inspect the parent's own handle)."""
    parent, child = _pair(wide, narrow)

    def body(_req, handle):
        probe(handle)
        return DONE

    monkeypatch.setitem(REGISTRY, "Probe", body)
    g = assemble(
        copy.deepcopy(parent),
        backend=backend or StubLLM(),
        stores=stores or {},
        world=world,
    )
    execute(g, REQUEST, graphs={"Inner": child})
    return g


def _refused(exc: type[BaseException], match: str) -> Callable[[Callable[[], object]], None]:
    """An assertion run inside the child: the reach must raise `exc`."""

    def check(reach: Callable[[], object]) -> None:
        with pytest.raises(exc, match=match):
            reach()

    return check


# ── HTTP allowlist ───────────────────────────────────────────────────────────

WIDE_HTTP = "HTTPClient<['a.example', 'b.example']>"
NARROW_HTTP = "HTTPClient<['a.example']>"
WEB = {"https://a.example/feed": "A", "https://b.example/feed": "B"}


def test_a_child_cannot_fetch_from_the_parents_wider_allowlist(monkeypatch):
    """The escape: `b.example` is on the parent's allowlist and not on the
    child's. Both operations refuse it as an ungranted reach, not as a failed
    fetch, exactly as an off-list host is refused at a bare handle."""
    seen: dict[str, object] = {}

    def probe(http):
        seen["a"] = http.get("https://a.example/feed")
        _refused(CapabilityError, "outside its allowlist")(
            lambda: http.get("https://b.example/feed")
        )
        _refused(CapabilityError, "outside its allowlist")(
            lambda: http.fetch("https://b.example/feed")
        )
        seen["allowlist"] = http.allowlist

    _run(WIDE_HTTP, NARROW_HTTP, probe, monkeypatch=monkeypatch, world=World(web=WEB))
    assert seen["a"] == "A"
    assert seen["allowlist"] == frozenset({"a.example"})


def test_the_parents_own_handle_keeps_its_allowlist(monkeypatch):
    """Attenuation narrows the child's view, not the parent's handle."""
    g = _run(
        WIDE_HTTP, NARROW_HTTP, lambda http: None, monkeypatch=monkeypatch, world=World(web=WEB)
    )
    parents = g.handles[WIDE_HTTP]
    assert isinstance(parents, HTTPClient)
    assert parents.get("https://b.example/feed") == "B"


def test_a_redirect_to_a_host_only_the_parent_may_reach_is_refused(monkeypatch):
    """The subtle escape: the child asks for an allowlisted URL and the server
    bounces it to a host on the parent's list but not the child's. The child's
    allowlist must apply to every hop, so a facade that checked only the first
    URL and forwarded would still leak here."""
    routes = {"/secret": ok("parent-only")}
    with serving(routes) as server:
        routes["/hop"] = redirect(server.url("/secret", host="localhost"))  # type: ignore[index]
        results: list[object] = []

        def probe(http):
            results.append(http.fetch(server.url("/hop")))
            _refused(CapabilityError, "outside its allowlist")(lambda: http.get(server.url("/hop")))

        _run(
            "HTTPClient<['127.0.0.1', 'localhost']>",
            "HTTPClient<['127.0.0.1']>",
            probe,
            monkeypatch=monkeypatch,
            world=World(live_http=True),
        )
        (result,) = results
        assert not result.ok and "redirect refused" in result.error  # type: ignore[attr-defined]
        assert "/secret" not in server.requests


# ── LLM tool set ─────────────────────────────────────────────────────────────

WIDE_LLM = "LLMClient<[lookup, refund]>"
NARROW_LLM = "LLMClient<[lookup]>"


class _AsksFor:
    """A model that requests one named tool, and records what it was offered."""

    def __init__(self, tool: str):
        self.tool = tool
        self.offered: list[tuple[str, ...]] = []

    def generate(self, request: LLMRequest) -> LLMResponse:
        self.offered.append(request.offered_tools)
        if len(self.offered) == 1:
            return LLMResponse(tool_calls=(ToolCall(self.tool, {"query": "q"}),))
        return LLMResponse(text="done")


def test_a_child_cannot_call_a_tool_only_the_parent_holds(monkeypatch):
    """The escape: the model asks for `refund`, which the parent's client grants
    and the child's does not. The child's handle refuses it, and the model was
    never offered it."""
    backend = _AsksFor("refund")
    tools = {"lookup": lambda query: "kb", "refund": lambda query: "refunded"}

    def probe(llm):
        assert llm.allowed_tools == frozenset({"lookup"})
        _refused(CapabilityError, "'refund' outside its LLMClient scope")(
            lambda: llm.respond(system="s", prompt="p", tools=tools)
        )

    _run(WIDE_LLM, NARROW_LLM, probe, monkeypatch=monkeypatch, backend=backend)
    assert backend.offered == [("lookup",)]


def test_a_child_may_call_the_tool_it_declares(monkeypatch):
    backend = _AsksFor("lookup")
    replies: list[str] = []
    _run(
        WIDE_LLM,
        NARROW_LLM,
        lambda llm: replies.append(
            llm.respond(system="s", prompt="p", tools={"lookup": lambda query: "kb"})
        ),
        monkeypatch=monkeypatch,
        backend=backend,
    )
    assert replies == ["done"]
    assert backend.offered == [("lookup",), ("lookup",)]


# ── Mode: DBHandle and StateHandle ───────────────────────────────────────────


def test_a_read_child_cannot_write_through_a_read_write_handle(monkeypatch):
    """The escape: the parent holds `read-write`, the child declares `read`. The
    child sees the store's contents, and has no `write` and no route to the
    parent's handle's private data."""
    stores = {"kb": {"k": ["v"]}}
    seen: dict[str, object] = {}

    def probe(db):
        seen["read"] = db.read("k")
        seen["write"] = hasattr(db, "write")
        seen["_data"] = hasattr(db, "_data")
        _refused(AttributeError, "write")(lambda: db.write("k", "forged"))

    g = _run(
        "DBHandle<'kb', read-write>",
        "DBHandle<'kb', read>",
        probe,
        monkeypatch=monkeypatch,
        stores=stores,
    )
    assert seen == {"read": ["v"], "write": False, "_data": False}
    parents = g.handles["DBHandle<'kb', read-write>"]
    assert isinstance(parents, ReadWriteDBHandle) and parents.read("k") == ["v"]


def test_a_read_child_sees_the_parents_writes(monkeypatch):
    """A facade, not a copy: what the parent's store holds when the child runs is
    what the child reads."""
    stores = {"kb": {"k": ["v"]}}
    parent, child = _pair("DBHandle<'kb', read-write>", "DBHandle<'kb', read>")
    seen: list[list[str]] = []

    def body(_req, db):
        seen.append(db.read("k"))
        return DONE

    monkeypatch.setitem(REGISTRY, "Probe", body)
    g = assemble(parent, backend=StubLLM(), stores=stores)
    g.handles["DBHandle<'kb', read-write>"].write("k", "w")  # type: ignore[attr-defined]
    execute(g, REQUEST, graphs={"Inner": child})
    assert seen == [["v", "w"]]


def test_an_append_child_cannot_read_through_a_read_write_handle(monkeypatch):
    """`read-write` covers `append`; the narrowed child may append and may not
    read back. Appended records land in the parent's store, under the store's own
    name as key."""
    seen: dict[str, object] = {}

    def probe(db):
        db.append("entry")
        seen["read"] = hasattr(db, "read")
        seen["write"] = hasattr(db, "write")

    g = _run(
        "DBHandle<'audit', read-write>",
        "DBHandle<'audit', append>",
        probe,
        monkeypatch=monkeypatch,
        stores={"audit": {}},
    )
    assert seen == {"read": False, "write": False}
    assert g.handles["DBHandle<'audit', read-write>"].read("audit") == ["entry"]  # type: ignore[attr-defined]


def test_a_read_child_cannot_change_the_parents_state_store(monkeypatch):
    """The escape, for node-local state: the parent's `StateHandle` may write
    `'seen'`, the child's may only read it. The child has no `put` or `delete`,
    and no route to the store object behind the parent's handle."""
    world = World()
    world.store("seen").put("x", "1")
    seen: dict[str, object] = {}

    def probe(state):
        seen["get"] = state.get("x")
        seen["ops"] = {op for op in ("put", "delete", "_store") if hasattr(state, op)}
        _refused(AttributeError, "put")(lambda: state.put("x", "forged"))

    _run(
        "StateHandle<'seen', read-write>",
        "StateHandle<'seen', read>",
        probe,
        monkeypatch=monkeypatch,
        world=world,
    )
    assert seen == {"get": "1", "ops": set()}
    assert world.store("seen").get("x") == "1"


# ── The banking kinds ────────────────────────────────────────────────────────


def _bank() -> MemoryBank:
    return MemoryBank(
        scheduled=[
            {
                "id": 1,
                "sender": "me",
                "recipient": "R",
                "amount": 10.0,
                "subject": "rent",
                "date": "2026-01-01",
                "recurring": True,
            },
            {
                "id": 2,
                "sender": "me",
                "recipient": "S",
                "amount": 9.0,
                "subject": "spotify",
                "date": "2026-01-01",
                "recurring": True,
            },
        ],
        user={"first_name": "A", "last_name": "B", "street": "C", "city": "D"},
    )


def test_a_child_cannot_pay_a_payee_or_amount_only_the_parent_may(monkeypatch):
    bank = _bank()

    def probe(pay):
        pay.send("GB1", 10.0, "ok", "2026-01-02")
        _refused(CapabilityError, "outside the handle's payees")(
            lambda: pay.send("GB2", 10.0, "x", "2026-01-02")
        )
        _refused(CapabilityError, "exceeds the handle's cap of 50")(
            lambda: pay.send("GB1", 75.0, "x", "2026-01-02")
        )

    _run(
        "Payments<['GB1', 'GB2'], '100'>",
        "Payments<['GB1'], '50'>",
        probe,
        monkeypatch=monkeypatch,
        world=World(bank=bank),
    )
    assert [w[1]["recipient"] for w in bank.writes] == ["GB1"]


def test_a_child_cannot_change_an_order_or_field_only_the_parent_may(monkeypatch):
    bank = _bank()

    def probe(sched):
        sched.update(1, amount=11.0)
        _refused(CapabilityError, "outside the handle's orders")(
            lambda: sched.update(2, amount=1.0)
        )
        _refused(CapabilityError, "outside the handle's fields")(
            lambda: sched.update(1, recipient="X")
        )

    _run(
        "ScheduledPayments<['rent', 'spotify'], [amount, recipient]>",
        "ScheduledPayments<['rent'], [amount]>",
        probe,
        monkeypatch=monkeypatch,
        world=World(bank=bank),
    )
    assert bank.writes == [("update_scheduled_transaction", {"id": 1, "amount": 11.0})]


def test_a_child_cannot_change_a_profile_field_only_the_parent_may(monkeypatch):
    bank = _bank()

    def probe(profile):
        profile.update(city="E")
        _refused(CapabilityError, "outside the handle's fields")(lambda: profile.update(street="F"))

    _run(
        "UserProfile<[street, city]>",
        "UserProfile<[city]>",
        probe,
        monkeypatch=monkeypatch,
        world=World(bank=bank),
    )
    assert bank.user["street"] == "C" and bank.user["city"] == "E"


# ── Revocation and rotation still reach the routed instance ──────────────────


def _revocable(wide: str, narrow: str, label: str, body) -> tuple[AssembledGraph, dict]:
    parent, child = _pair(wide, narrow, identity=label)
    REGISTRY["Probe"] = body
    g = assemble(
        parent,
        backend=StubLLM(),
        stores={"kb": {"k": ["v"]}},
        world=World(web=WEB),
        revocable_instances=[(wide, label)],
        rotatable_instances=[(wide, label)],
    )
    return g, child


def test_revoking_the_parents_instance_reaches_the_attenuated_child(monkeypatch):
    """The facade keeps the caretaker rather than the handle behind it, so a
    revocation at the parent severs the child's narrowed view too. A facade that
    unwrapped the caretaker would keep working after the revoke."""
    results: list[str] = []

    def body(_req, http):
        results.append(http.get("https://a.example/feed"))
        return DONE

    monkeypatch.setitem(REGISTRY, "Probe", body)
    g, child = _revocable(WIDE_HTTP, NARROW_HTTP, "feeds", body)
    execute(g, REQUEST, graphs={"Inner": child})
    assert results == ["A"]

    g.revoke(WIDE_HTTP, "feeds")
    with pytest.raises(RevokedCapabilityError, match="attempted use of 'get'"):
        execute(g, REQUEST, graphs={"Inner": child})


def test_rotating_the_parents_instance_reaches_the_attenuated_child(monkeypatch):
    """Rotation re-points the caretaker; the child, still narrowed, follows it."""
    results: list[str] = []

    def body(_req, http):
        results.append(http.get("https://a.example/feed"))
        _refused(CapabilityError, "outside its allowlist")(
            lambda: http.get("https://b.example/feed")
        )
        return DONE

    monkeypatch.setitem(REGISTRY, "Probe", body)
    g, child = _revocable(WIDE_HTTP, NARROW_HTTP, "feeds", body)
    g.rotate(
        WIDE_HTTP,
        "feeds",
        HTTPClient(
            allowlist=frozenset({"a.example", "b.example"}),
            _responses={"https://a.example/feed": "A2", "https://b.example/feed": "B2"},
        ),
    )
    execute(g, REQUEST, graphs={"Inner": child})
    assert results == ["A2"]


# ── Composition: two boundaries, the trace, and the unnarrowed case ──────────


def test_narrowing_composes_across_two_boundaries(monkeypatch):
    """Top routes three hosts to Middle, which declares two and routes them to
    Leaf, which declares one. Leaf is bound by the narrowest of the three."""
    top, middle = _pair(
        "HTTPClient<['a.example', 'b.example', 'c.example']>",
        "HTTPClient<['a.example', 'b.example']>",
    )
    middle["name"] = "Inner"
    middle["nodes"] = [
        {
            "name": "Leaf",
            "inputs": ["CustomerRequest", "HTTPClient<['a.example', 'b.example']>"],
            "output": "DeliveryConfirmation",
        }
    ]
    leaf = {
        "name": "Leaf",
        "parameters": ["CustomerRequest", NARROW_HTTP],
        "capabilities": [NARROW_HTTP],
        "nodes": [
            {
                "name": "Probe",
                "inputs": ["CustomerRequest", NARROW_HTTP],
                "output": "DeliveryConfirmation",
            }
        ],
        "data_edges": [],
    }
    reached: list[str] = []

    def body(_req, http):
        reached.append(http.get("https://a.example/feed"))
        for host in ("b.example", "c.example"):
            _refused(CapabilityError, "outside its allowlist")(
                lambda h=host: http.get(f"https://{h}/feed")
            )
        return DONE

    monkeypatch.setitem(REGISTRY, "Probe", body)
    web = {**WEB, "https://c.example/feed": "C"}
    g = assemble(top, backend=StubLLM(), stores={}, world=World(web=web))
    execute(g, REQUEST, graphs={"Inner": middle, "Leaf": leaf})
    assert reached == ["A"]


def test_the_trace_keeps_the_parents_instance_label(monkeypatch):
    """A routed crossing is named by the instance the parent declared, as before
    attenuation; its interface is the one the child declared, which is the
    interface the crossing now goes through."""
    parent, child = _pair("DBHandle<'kb', read-write>", "DBHandle<'kb', read>", identity="kb_main")

    def body(_req, db):
        db.read("k")
        return DONE

    monkeypatch.setitem(REGISTRY, "Probe", body)
    g = assemble(parent, backend=StubLLM(), stores={"kb": {"k": ["v"]}})
    result = execute(g, REQUEST, graphs={"Inner": child})
    inner = result.trace.nodes[0].subgraph
    assert inner is not None
    probe = inner.nodes[0]
    kb_read = interface_for("DBHandle<'kb', read>")
    assert kb_read.endswith("/kb-read@0.1.0")
    assert [(c.interface, c.instance) for c in probe.crossings] == [(kb_read, "kb_main")]


def test_a_handle_routed_at_its_declared_type_passes_through_untouched(monkeypatch):
    """No narrowing, no facade: the child holds the parent's instance itself (behind
    the trace's recording proxy), as it did before attenuation existed."""
    got: list[object] = []

    def probe(db):
        got.append(object.__getattribute__(db, "_target"))

    g = _run(
        "DBHandle<'kb', read>",
        "DBHandle<'kb', read>",
        probe,
        monkeypatch=monkeypatch,
        stores={"kb": {}},
    )
    assert got == [g.handles["DBHandle<'kb', read>"]]
    assert isinstance(got[0], ReadDBHandle)


def test_every_narrowing_the_validator_accepts_has_a_facade():
    """The facade table and `is_assignable` must agree, or a composition the
    validator accepts would fail at the routing point. Each pair below is accepted
    by the validator and differs from its target."""
    from poc.attenuate import attenuate

    world = World(web=WEB, bank=_bank())
    from poc.handles import provision

    pairs = [
        (WIDE_HTTP, NARROW_HTTP),
        (WIDE_LLM, NARROW_LLM),
        (WIDE_LLM, "LLMClient<inference>"),
        ("DBHandle<'kb', read-write>", "DBHandle<'kb', read>"),
        ("DBHandle<'kb', read-write>", "DBHandle<'kb', append>"),
        ("StateHandle<'seen', read-write>", "StateHandle<'seen', read>"),
        ("Payments<['GB1', 'GB2'], '100'>", "Payments<['GB1'], '50'>"),
        ("Payments<[any], uncapped, recurring>", "Payments<['GB1'], '5', recurring>"),
        ("ScheduledPayments<['rent'], [amount, date]>", "ScheduledPayments<['rent'], [amount]>"),
        ("UserProfile<[street, city]>", "UserProfile<[city]>"),
    ]
    for wide, narrow in pairs:
        handle = provision(wide, backend=StubLLM(), stores={"kb": {}}, world=world)
        assert attenuate(handle, wide, narrow) is not handle, (wide, narrow)


def test_a_widening_is_refused_at_the_routing_point():
    """The validator refuses a widening before anything runs; the facade refuses
    it too, rather than minting authority if the validator were ever bypassed."""
    from poc.attenuate import AttenuationError, attenuate

    handle = HTTPClient(allowlist=frozenset({"a.example"}))
    with pytest.raises(AttenuationError, match="not a narrowing"):
        attenuate(handle, NARROW_HTTP, WIDE_HTTP)


# ── On the shipped composition, both tiers ───────────────────────────────────


def _wide_platform() -> dict:
    """`SupportPlatform` with its tool client widened to `[lookup, refund]`: the
    platform now holds a tool `CustomerSupport` does not declare."""
    g = load_graph_dict("support-platform")
    wide = "LLMClient<[lookup, refund]>"

    def swap(types: list[str]) -> list[str]:
        return [wide if t == NARROW_LLM else t for t in types]

    g["parameters"] = swap(g["parameters"])
    g["capabilities"] = swap(g["capabilities"])
    for n in g["nodes"]:
        n["inputs"] = swap(n["inputs"])
    return g


TRAFFIC = HTTPRoute(
    path="/customer/message",
    session_id="user-session",
    body="Why was I charged twice on my latest invoice?",
)
STORES = {
    "knowledge-base": {"billing_question": ["Duplicate charges clear in 3-5 days."]},
    "billing": {},
    "audit": {},
}


def _offered(sandbox) -> set[tuple[str, ...]]:
    backend = StubLLM()
    g = assemble(_wide_platform(), backend=backend, stores=STORES)
    execute(g, TRAFFIC, sandbox=sandbox)
    return {c.offered_tools for c in backend.calls if c.task == "respond"}


def test_the_platforms_wider_tool_is_never_offered_inside_customer_support():
    """End to end on the shipped composition, host tier: the platform holds
    `refund`, `CustomerSupport` declares only `lookup`, and the model behind
    `GenerateResponse` is offered `lookup` alone."""
    assert _offered(sandbox=None) == {("lookup",)}


def test_the_wider_tool_is_not_offered_on_the_confined_tier_either():
    """The same composition with `GenerateResponse` running as a component: its
    host adapter reads the handle's tool set, which is the child's."""
    from poc.sandbox.host import available

    if not available():
        pytest.skip("component tier unavailable: wasmtime not installed")
    assert _offered(sandbox={"CustomerSupport": ["GenerateResponse"]}) == {("lookup",)}


def test_tool_llm_still_refuses_outside_its_own_scope():
    """The `within` bound only narrows: a caller cannot widen a handle with it."""
    llm = ToolLLM(_AsksFor("refund"), frozenset({"lookup"}))
    with pytest.raises(CapabilityError, match="outside its LLMClient scope"):
        llm.respond(
            system="s",
            prompt="p",
            tools={"refund": lambda query: ""},
            within=(frozenset({"lookup", "refund"}),),
        )


def test_the_append_facade_has_no_log_inspection_surface():
    """`AppendDBHandle.appended` is the host's view of a log; an append facade over
    a read-write store exposes no such field to the node."""
    from poc.attenuate import attenuate

    inner = ReadWriteDBHandle("audit", {})
    facade = attenuate(inner, "DBHandle<'audit', read-write>", "DBHandle<'audit', append>")
    assert not isinstance(facade, AppendDBHandle)
    assert not hasattr(facade, "appended")


def test_a_read_state_facade_is_not_a_read_write_handle():
    from poc.attenuate import attenuate

    world = World()
    from poc.handles import ReadWriteStateHandle

    inner = ReadWriteStateHandle("seen", world.store("seen"))
    facade = attenuate(inner, "StateHandle<'seen', read-write>", "StateHandle<'seen', read>")
    assert not isinstance(facade, ReadWriteStateHandle | ReadStateHandle)
    assert facade.name == "seen"
