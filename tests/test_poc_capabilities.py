"""Capability scoping and assembly-time rejection.

Covers the `signal-graph-runtime` spec requirements:
  - Capability scoping is enforced by handle surface
  - Assembly-time rejection of unsafe wiring
  - Graph loading and node instantiation
"""

from __future__ import annotations

import pytest

from poc.graph import AssemblyError, assemble, load_graph_dict, validate_graph_dict
from poc.handles import (
    AppendDBHandle,
    CapabilityError,
    Caretaker,
    Clock,
    EventEmitter,
    HTTPClient,
    InferenceLLM,
    Notifier,
    ReadDBHandle,
    ReadWriteDBHandle,
    ResponseChannel,
    RevokedCapabilityError,
    Revoker,
    Rotator,
    ToolLLM,
    WallTime,
    manage,
    provision,
    revocable,
    rotatable,
)
from poc.llm import LLMRequest, LLMResponse, StubLLM, ToolCall
from poc.variants import CROSS_GRAPH_VARIANTS, UNSAFE_VARIANTS

STORES = {"knowledge-base": {"billing_question": ["Invoices are issued monthly."]}}


@pytest.fixture
def graph() -> dict:
    return load_graph_dict("customer-support")


# ── Capability scoping ─────────────────────────────────────────────


def test_inference_llm_has_no_tool_calling_method():
    """`LLMClient<inference>` grants model access and nothing else. The absence
    of any tool method is the enforcement — there is no call to refuse."""
    llm = InferenceLLM(StubLLM())
    assert not hasattr(llm, "respond")
    assert not hasattr(llm, "call_tool")
    assert hasattr(llm, "infer")


def test_inference_llm_never_offers_tools_to_the_model():
    """The model is not even told tools exist."""
    backend = StubLLM()
    InferenceLLM(backend).infer(system="s", prompt="p", task="classify")
    assert backend.calls[0].offered_tools == ()


def test_tool_llm_refuses_a_tool_outside_its_scope():
    """`LLMClient<[lookup]>` grants exactly one tool. A request for any other
    is refused by the handle, regardless of what the model asked for."""

    class RogueBackend:
        def generate(self, request: LLMRequest) -> LLMResponse:
            return LLMResponse(tool_calls=(ToolCall("exfiltrate", {"to": "evil"}),))

    llm = ToolLLM(RogueBackend(), frozenset({"lookup"}))
    with pytest.raises(CapabilityError, match="exfiltrate"):
        llm.respond(system="s", prompt="p", tools={"lookup": lambda query: "ok"})


def test_tool_llm_permits_its_own_tool():
    llm = ToolLLM(StubLLM(), frozenset({"lookup"}))
    text = llm.respond(system="s", prompt="p", tools={"lookup": lambda query: "KB hit"})
    assert isinstance(text, str)


def test_read_db_handle_has_no_write_method():
    db = ReadDBHandle("knowledge-base", {"k": ["v"]})
    assert db.read("k") == ["v"]
    assert not hasattr(db, "write")


def test_read_write_db_handle_reads_and_writes():
    """`DBHandle<scope, read-write>` grants both operations; a written record is
    visible to a subsequent read through the same handle."""
    db = ReadWriteDBHandle("billing", {})
    assert db.read("acct-1") == []
    db.write("acct-1", "invoice #42")
    assert db.read("acct-1") == ["invoice #42"]


def test_append_db_handle_has_no_read_method():
    """`DBHandle<scope, append>` is append-only: a node that can write the audit
    log must not be able to read it back. The absence of `read` is the enforcement,
    mirroring `ReadDBHandle` having no `write`."""
    db = AppendDBHandle("audit")
    db.append("outcome recorded")
    assert not hasattr(db, "read")
    assert db.appended == ["outcome recorded"]  # host/test inspection, not a node op


def test_sinks_are_write_only():
    assert not hasattr(ResponseChannel("s"), "read")
    assert not hasattr(EventEmitter("t"), "read")
    assert not hasattr(Notifier("digest"), "read")


# ── I/O handles: clock, outbound HTTP, notification ────────────────


def test_clock_reads_time_and_nothing_else():
    """`Clock` grants exactly one observation: the current wall time. There is
    no setter and no scheduling surface — reading the world's time is the whole
    of the authority."""
    clock = Clock(_source=lambda: WallTime(seconds=1_700_000_000, nanoseconds=42))
    t = clock.now()
    assert (t.seconds, t.nanoseconds) == (1_700_000_000, 42)
    assert not hasattr(clock, "set")
    assert not hasattr(clock, "sleep")


def test_http_client_serves_an_allowlisted_host():
    http = HTTPClient(
        allowlist=frozenset({"feeds.example.com"}),
        _responses={"https://feeds.example.com/a.xml": "<rss/>"},
    )
    assert http.get("https://feeds.example.com/a.xml") == "<rss/>"


def test_http_client_refuses_a_host_outside_its_allowlist():
    """The allowlist is enforced at the handle, exactly as `ToolLLM` refuses an
    out-of-scope tool: the node holds the operation, the handle holds the scope."""
    http = HTTPClient(allowlist=frozenset({"feeds.example.com"}))
    with pytest.raises(CapabilityError, match=r"evil\.example"):
        http.get("https://evil.example/?d=exfiltrated")


def test_http_client_refuses_an_unparseable_host():
    """A URL with no discernible host cannot be checked against the allowlist,
    so it is refused rather than waved through — fail closed."""
    http = HTTPClient(allowlist=frozenset({"feeds.example.com"}))
    with pytest.raises(CapabilityError):
        http.get("not a url")


def test_notifier_is_a_write_only_channel_sink():
    n = Notifier("digest")
    n.notify("3 items today")
    assert n.sent == ["3 items today"]
    assert n.channel == "digest"


# ── Provisioning: capability type string → handle ──────────────────


@pytest.mark.parametrize(
    ("cap", "expected"),
    [
        ("LLMClient<inference>", InferenceLLM),
        ("LLMClient<[lookup]>", ToolLLM),
        ("DBHandle<'knowledge-base', read>", ReadDBHandle),
        ("DBHandle<'billing', read-write>", ReadWriteDBHandle),
        ("DBHandle<'audit', append>", AppendDBHandle),
        ("ResponseChannel<user-session>", ResponseChannel),
        ("EventEmitter<'support-queue'>", EventEmitter),
        ("Clock", Clock),
        ("HTTPClient<['feeds.example.com']>", HTTPClient),
        ("Notifier<'digest'>", Notifier),
    ],
)
def test_provision_builds_the_right_handle(cap, expected):
    handle = provision(cap, backend=StubLLM(), stores=STORES)
    assert isinstance(handle, expected)


def test_provisioned_http_client_carries_exactly_its_declared_allowlist():
    handle = provision(
        "HTTPClient<['feeds.example.com', 'blog.example.net']>",
        backend=StubLLM(),
        stores=STORES,
        web={"https://feeds.example.com/a.xml": "<rss/>"},
    )
    assert isinstance(handle, HTTPClient)
    assert handle.allowlist == frozenset({"feeds.example.com", "blog.example.net"})
    assert handle.get("https://feeds.example.com/a.xml") == "<rss/>"
    with pytest.raises(CapabilityError):
        handle.get("https://evil.example/")


def test_provision_rejects_a_malformed_http_allowlist():
    """An empty or non-literal allowlist grants nothing checkable and is refused
    at provisioning, not discovered at the first request."""
    with pytest.raises(ValueError, match="HTTPClient"):
        provision("HTTPClient<[]>", backend=StubLLM(), stores=STORES)
    with pytest.raises(ValueError, match="HTTPClient"):
        provision("HTTPClient<[bare-name]>", backend=StubLLM(), stores=STORES)


def test_provision_rejects_an_unmodelled_db_mode():
    """A DBHandle mode the runtime does not model fails loudly, naming the modes it
    does know — fail-closed rather than silently picking one."""
    with pytest.raises(ValueError, match="read, read-write, append"):
        provision("DBHandle<'x', truncate>", backend=StubLLM(), stores=STORES)


def test_read_write_provision_does_not_alias_the_shared_stores():
    """The read-write handle owns a private copy of its store slice: a write through
    one assembly's handle does not leak into the shared `stores` or a fresh one."""
    stores = {"billing": {"acct-1": ["opening balance"]}}
    first = provision("DBHandle<'billing', read-write>", backend=StubLLM(), stores=stores)
    assert isinstance(first, ReadWriteDBHandle)
    first.write("acct-1", "charge")

    # The shared mapping is untouched...
    assert stores["billing"]["acct-1"] == ["opening balance"]
    # ...and a fresh provision sees only the original contents, not the write.
    second = provision("DBHandle<'billing', read-write>", backend=StubLLM(), stores=stores)
    assert isinstance(second, ReadWriteDBHandle)
    assert second.read("acct-1") == ["opening balance"]


def test_provisioned_tool_llm_carries_exactly_its_declared_tools():
    handle = provision("LLMClient<[lookup]>", backend=StubLLM(), stores=STORES)
    assert isinstance(handle, ToolLLM)
    assert handle.allowed_tools == frozenset({"lookup"})


# ── Assembly ───────────────────────────────────────────────────────


def test_canonical_graph_assembles(graph):
    g = assemble(graph, backend=StubLLM(), stores=STORES)
    assert g.name == "CustomerSupport"
    assert len(g.nodes) == 9


def test_nodes_receive_only_their_declared_handles(graph):
    """`ParseMessage` gets an inference LLM and nothing else — no DB, no channel."""
    g = assemble(graph, backend=StubLLM(), stores=STORES)
    handles = g.handles_for(g.nodes["ParseMessage"])
    assert [type(h).__name__ for h in handles.values()] == ["InferenceLLM"]

    # The pure node holds no authority at all.
    assert g.handles_for(g.nodes["ReceiveMessage"]) == {}

    # The escalation node can emit, but cannot touch any database.
    escalate = g.handles_for(g.nodes["EscalateToHuman"])
    assert [type(h).__name__ for h in escalate.values()] == ["EventEmitter"]


# ── Capability identity ────────────────────────────────────────────
#
# By default the runtime provisions one handle per capability *type*, shared
# across every node naming it. That aliasing is harmless for read-only handles
# but wrong for stateful ones. These tests cover the opt-in identity surface:
# naming distinct instances of one type at the graph boundary (the assembly API)
# and routing each to a specific node. `ResponseChannel<user-session>` is the
# probe — three nodes hold it, and its `.sent` list makes shared vs distinct
# state directly observable.

RC = "ResponseChannel<user-session>"


def test_same_typed_capability_is_shared_by_type_without_identity(graph):
    """The documented default: two nodes naming the same capability type receive
    the *same* object when no identity is declared (harmless for read-only, the
    gap this change makes closable for stateful handles)."""
    g = assemble(graph, backend=StubLLM(), stores=STORES)
    assert g.instances == {}
    send_reply = g.handle_for(g.nodes["SendReply"], RC)
    notify_user = g.handle_for(g.nodes["NotifyUser"], RC)
    assert send_reply is notify_user


def test_distinct_identities_get_distinct_instances_with_independent_state(graph):
    """Two nodes of the same capability type but distinct identity receive
    distinct instances, and stateful mutation of one does not reach the other."""
    g = assemble(
        graph,
        backend=StubLLM(),
        stores=STORES,
        identities={
            "SendReply": {RC: "session_a"},
            "NotifyUser": {RC: "session_b"},
        },
    )
    a = g.handle_for(g.nodes["SendReply"], RC)
    b = g.handle_for(g.nodes["NotifyUser"], RC)
    assert isinstance(a, ResponseChannel) and isinstance(b, ResponseChannel)
    assert a is not b

    a.send("delivered to A")
    assert a.sent == ["delivered to A"]
    assert b.sent == []  # independent state, not shared through one aliased object


def test_shared_identity_label_shares_one_instance(graph):
    """Identity — not node — is the unit: two nodes naming the *same* label bind
    one instance, so a named slot can be deliberately shared."""
    g = assemble(
        graph,
        backend=StubLLM(),
        stores=STORES,
        identities={
            "SendReply": {RC: "primary"},
            "HandleLLMError": {RC: "primary"},
        },
    )
    assert g.handle_for(g.nodes["SendReply"], RC) is g.handle_for(g.nodes["HandleLLMError"], RC)


def test_identity_only_reroutes_the_named_node(graph):
    """Giving one node an identity leaves the others on the shared-by-type
    default — the change is local to the nodes that opt in."""
    g = assemble(
        graph,
        backend=StubLLM(),
        stores=STORES,
        identities={"SendReply": {RC: "session_a"}},
    )
    send_reply = g.handle_for(g.nodes["SendReply"], RC)
    notify_user = g.handle_for(g.nodes["NotifyUser"], RC)
    handle_err = g.handle_for(g.nodes["HandleLLMError"], RC)
    assert send_reply is not notify_user
    assert notify_user is handle_err  # both still on the shared default


@pytest.mark.parametrize(
    ("identities", "match"),
    [
        ({"NoSuchNode": {RC: "x"}}, "unknown node"),
        ({"SendReply": {"DBHandle<'nope', read>": "x"}}, "unknown capability"),
        # ParseMessage holds an inference LLM, not a ResponseChannel.
        ({"ParseMessage": {RC: "x"}}, "does not declare capability"),
    ],
)
def test_identity_for_a_capability_a_node_lacks_is_rejected(graph, identities, match):
    """Misrouted identity declarations fail loudly at assembly rather than
    silently provisioning an instance no node binds."""
    with pytest.raises(AssemblyError, match=match):
        assemble(graph, backend=StubLLM(), stores=STORES, identities=identities)


# ── Capability identity declared in the canonical graph source ─────
#
# Identity is now spelled in the graph JSON (`capability_identities` per node),
# not only in the assembly API. These tests build the declaration into the graph
# dict, assemble *without* any `identities=` argument, and confirm the runtime
# derives its instance routing from the source of truth — so identity, pseudocode,
# and diagrams all agree.


def _with_graph_identity(graph: dict, node: str, cap: str, label: str) -> dict:
    """Return a copy-ish of `graph` with `capability_identities` set on one node.
    Mutates the shared fixture dict's node in place, which is fine per-test since
    the fixture is function-scoped."""
    for n in graph["nodes"]:
        if n["name"] == node:
            n.setdefault("capability_identities", {})[cap] = label
    return graph


def test_graph_declared_identity_routes_distinct_instances(graph):
    """Spec: identity declared in the graph JSON routes distinct instances, exactly
    as if it had been passed to the assembly API — no `identities=` argument."""
    _with_graph_identity(graph, "SendReply", RC, "session_a")
    _with_graph_identity(graph, "NotifyUser", RC, "session_b")

    g = assemble(graph, backend=StubLLM(), stores=STORES)  # no identities= argument

    a = g.handle_for(g.nodes["SendReply"], RC)
    b = g.handle_for(g.nodes["NotifyUser"], RC)
    assert isinstance(a, ResponseChannel) and isinstance(b, ResponseChannel)
    assert a is not b

    a.send("delivered to A")
    assert a.sent == ["delivered to A"]
    assert b.sent == []  # independent state, from the graph source alone


def test_graph_and_argument_identity_agree_on_shared_label(graph):
    """A label shared between the graph and the argument still means one instance —
    the two sources compose rather than fight when they name the same identity."""
    _with_graph_identity(graph, "SendReply", RC, "primary")
    g = assemble(
        graph,
        backend=StubLLM(),
        stores=STORES,
        identities={"HandleLLMError": {RC: "primary"}},  # argument names the same label
    )
    assert g.handle_for(g.nodes["SendReply"], RC) is g.handle_for(g.nodes["HandleLLMError"], RC)


def test_argument_overrides_graph_identity_per_slot(graph):
    """Precedence (design decision): the `identities=` argument overrides the graph
    at the (node, capability) granularity. The graph shares one instance between
    two nodes; overriding one node's slot splits them, leaving the other's
    graph-declared identity intact."""
    _with_graph_identity(graph, "SendReply", RC, "shared")
    _with_graph_identity(graph, "NotifyUser", RC, "shared")

    # Without the override both share; assert the graph baseline first.
    baseline = assemble(graph, backend=StubLLM(), stores=STORES)
    assert baseline.handle_for(baseline.nodes["SendReply"], RC) is baseline.handle_for(
        baseline.nodes["NotifyUser"], RC
    )

    # The argument retargets only SendReply's slot; NotifyUser keeps "shared".
    g = assemble(
        graph,
        backend=StubLLM(),
        stores=STORES,
        identities={"SendReply": {RC: "override"}},
    )
    assert g.handle_for(g.nodes["SendReply"], RC) is not g.handle_for(g.nodes["NotifyUser"], RC)


def test_graph_declared_identity_and_validator_agree_on_unheld_capability():
    """Spec: an identity for a capability a node does not hold is rejected both by
    the validator (validation time) and by `assemble` (assembly time)."""
    g = load_graph_dict("customer-support")
    # ParseMessage holds an inference LLM, not a ResponseChannel.
    _with_graph_identity(g, "ParseMessage", RC, "x")

    assert validate_graph_dict(g), "validator should reject an unheld-capability identity"
    with pytest.raises(AssemblyError):
        assemble(g, backend=StubLLM(), stores=STORES)


def test_revocable_targets_a_graph_declared_identity(graph):
    """Revocation still targets an instance whose identity is declared in the graph
    (not the argument) — the two features layer cleanly."""
    _with_graph_identity(graph, "SendReply", RC, "session_a")
    g = assemble(
        graph,
        backend=StubLLM(),
        stores=STORES,
        revocable_instances=[(RC, "session_a")],  # names a graph-declared identity
    )
    handle = g.handle_for(g.nodes["SendReply"], RC)
    assert handle.send("before").delivered
    g.revoke(RC, "session_a")
    with pytest.raises(RevokedCapabilityError):
        handle.send("after")


# ── Identity routed across a sub-graph boundary ────────────────────
#
# A node whose signature matches another graph is a sub-graph reference. The
# parent declares `capability_identities` on that node to bind a *named* instance
# to the sub-graph's capability slot, so composition carries identity, not merely
# capability type. (The runtime does not recursively execute sub-graphs, so this
# is exercised at the parent-graph assembly level — the one composition level this
# change carries identity across.)


def _platform_with_subgraphs() -> dict:
    """A parent graph that routes distinct `ResponseChannel` instances into two
    sub-graph-reference nodes via graph-declared identity."""
    return {
        "name": "Platform",
        "parameters": ["PlatformRequest", RC],
        "capabilities": [RC],
        "nodes": [
            {
                "name": "Dispatch",
                "inputs": ["PlatformRequest"],
                "output": "sub: SubRequest | sibling: SiblingRequest",
            },
            {
                "name": "SubService",
                "inputs": ["SubRequest", RC],
                "output": "Outcome",
                "capability_identities": {RC: "sub_session"},
            },
            {
                "name": "SiblingService",
                "inputs": ["SiblingRequest", RC],
                "output": "Outcome",
                "capability_identities": {RC: "sibling_session"},
            },
        ],
        "data_edges": [
            {"from": "Dispatch.sub", "to": "SubService"},
            {"from": "Dispatch.sibling", "to": "SiblingService"},
        ],
    }


def test_parent_routes_a_distinct_instance_into_a_sub_graph_node():
    """Spec: a parent binds a named instance to a sub-graph's capability slot; the
    sub-graph node receives that instance and a sibling instance the parent did not
    route to it is not visible."""
    g = assemble(_platform_with_subgraphs(), backend=StubLLM(), stores=STORES)

    sub = g.handle_for(g.nodes["SubService"], RC)
    sibling = g.handle_for(g.nodes["SiblingService"], RC)
    assert isinstance(sub, ResponseChannel) and isinstance(sibling, ResponseChannel)
    assert sub is not sibling  # distinct instances routed across the boundary

    # Routing derives from the graph source, recorded in `instances`.
    assert g.instances[("SubService", RC)] is sub
    assert g.instances[("SiblingService", RC)] is sibling

    sub.send("to the routed sub-graph")
    assert sub.sent == ["to the routed sub-graph"]
    assert sibling.sent == []  # the sibling's instance is not visible to SubService


def test_shipped_support_platform_assembles_and_routes_identity():
    """Spec: the canonical `SupportPlatform` graph now assembles end-to-end — every
    capability it declares (including `read-write` and `append` DB handles) is
    provisionable — and its graph-declared `ResponseChannel<user-session>`
    identities route distinct instances to `CustomerSupport` and `BillingService`.
    This exercises capability-identity routing across a sub-graph boundary on the
    *shipped* graph, not a synthetic stand-in."""
    platform = load_graph_dict("support-platform")
    g = assemble(platform, backend=StubLLM(), stores=STORES)

    assert g.name == "SupportPlatform"
    # Every declared capability was provisioned (assembly did not skip any).
    assert set(g.handles) == set(platform["capabilities"])

    customer = g.handle_for(g.nodes["CustomerSupport"], RC)
    billing = g.handle_for(g.nodes["BillingService"], RC)
    assert isinstance(customer, ResponseChannel) and isinstance(billing, ResponseChannel)
    assert customer is not billing  # distinct instances routed across the boundary
    # Each matches the identity declared for it in the graph source.
    assert g.instances[("CustomerSupport", RC)] is customer
    assert g.instances[("BillingService", RC)] is billing

    customer.send("reply to the customer")
    assert billing.sent == []  # billing's channel is not visible to customer support


# ── Capability revocation ──────────────────────────────────────────
#
# Revocation withdraws one *named* capability instance's authority at runtime, on
# the host tier, via the ocap caretaker pattern: the node holds a forwarding proxy
# and a separate revoker severs it. It layers on identity — only instances a node
# binds by (capability type, identity label) can be made revocable — and is opt-in,
# so un-revoked provisioning is byte-for-byte unchanged. `ResponseChannel` is again
# the probe: its `.send` is an observable use that must succeed then fail.


def test_caretaker_forwards_the_wrapped_surface_until_revoked():
    """Before revocation a caretaker is indistinguishable from the bare handle:
    the same operation runs and reaches the underlying resource."""
    channel = ResponseChannel("s")
    caretaker, _revoker = revocable(channel)
    assert isinstance(caretaker, Caretaker)
    conf = caretaker.send("hello")
    assert conf.delivered
    assert channel.sent == ["hello"]  # forwarded to the real handle


def test_caretaker_forwards_method_absence():
    """`__getattr__` delegation forwards *absence* too: a caretaker over an
    inference LLM has no `respond`, just like the handle it wraps — so a node
    cannot distinguish the proxy through the capability surface."""
    caretaker, _ = revocable(InferenceLLM(StubLLM()))
    assert hasattr(caretaker, "infer")
    assert not hasattr(caretaker, "respond")
    assert not hasattr(caretaker, "call_tool")


def test_revoked_caretaker_raises_on_use():
    """After the revoker severs it, every operation raises — loud failure, not a
    silent no-op — and the underlying resource is never reached."""
    channel = ResponseChannel("s")
    caretaker, revoker = revocable(channel)
    revoker.revoke()
    with pytest.raises(RevokedCapabilityError, match="ResponseChannel"):
        caretaker.send("hello")
    assert channel.sent == []  # authority withdrawn before the resource was touched


def test_revocation_is_idempotent():
    caretaker, revoker = revocable(ResponseChannel("s"))
    revoker.revoke()
    revoker.revoke()  # no error, still severed
    assert revoker.revoked
    with pytest.raises(RevokedCapabilityError):
        caretaker.send("x")


def test_revoke_then_use_through_the_assembled_graph(graph):
    """End-to-end (spec: revocation severs authority): a node's instance works
    before revocation and fails after, driven through the assembly API."""
    g = assemble(
        graph,
        backend=StubLLM(),
        stores=STORES,
        identities={"SendReply": {RC: "session_a"}},
        revocable_instances=[(RC, "session_a")],
    )
    handle = g.handle_for(g.nodes["SendReply"], RC)
    assert handle.send("before").delivered  # succeeds before revocation

    g.revoke(RC, "session_a")
    with pytest.raises(RevokedCapabilityError):
        handle.send("after")


def test_revocation_is_targeted_to_one_instance(graph):
    """Spec: revoking one instance leaves its distinct-identity sibling — and the
    shared-by-type default — fully usable."""
    g = assemble(
        graph,
        backend=StubLLM(),
        stores=STORES,
        identities={
            "SendReply": {RC: "session_a"},
            "NotifyUser": {RC: "session_b"},
        },
        revocable_instances=[(RC, "session_a")],
    )
    revoked = g.handle_for(g.nodes["SendReply"], RC)
    sibling = g.handle_for(g.nodes["NotifyUser"], RC)  # distinct identity
    type_default = g.handles[RC]  # shared-by-type default

    g.revoke(RC, "session_a")

    with pytest.raises(RevokedCapabilityError):
        revoked.send("nope")
    assert sibling.send("ok").delivered  # untouched
    assert type_default.send("ok").delivered  # untouched


def test_nodes_never_receive_revoke_authority(graph):
    """Spec: the revoke authority is held only by the host. A node receives a
    caretaker with no revoke operation; the paired revoker lives on the graph."""
    g = assemble(
        graph,
        backend=StubLLM(),
        stores=STORES,
        identities={"SendReply": {RC: "session_a"}},
        revocable_instances=[(RC, "session_a")],
    )
    handle = g.handle_for(g.nodes["SendReply"], RC)
    # The caretaker exposes the capability surface but no way to revoke.
    assert not hasattr(handle, "revoke")
    assert not isinstance(handle, Revoker)
    # The authority to revoke lives on the assembled graph, which no node holds.
    assert isinstance(g.revokers[(RC, "session_a")], Revoker)


def test_revocable_must_name_a_declared_identity(graph):
    """An instance is revocable only if some node binds it — declaring an unbound
    (capability, identity) revocable fails loudly rather than protecting nothing."""
    with pytest.raises(AssemblyError, match="not a declared identity"):
        assemble(
            graph,
            backend=StubLLM(),
            stores=STORES,
            identities={"SendReply": {RC: "session_a"}},
            revocable_instances=[(RC, "session_b")],  # no node binds session_b
        )


def test_revoking_an_unprovisioned_instance_raises(graph):
    g = assemble(graph, backend=StubLLM(), stores=STORES)
    with pytest.raises(KeyError, match="no revocable instance"):
        g.revoke(RC, "session_a")


def test_no_revocable_declaration_leaves_provisioning_unchanged(graph):
    """Spec: revocation is opt-in. With no revocable declaration, no caretaker is
    introduced and no revoker exists — provisioning is exactly as before."""
    g = assemble(
        graph,
        backend=StubLLM(),
        stores=STORES,
        identities={"SendReply": {RC: "session_a"}},
    )
    handle = g.handle_for(g.nodes["SendReply"], RC)
    assert isinstance(handle, ResponseChannel)  # bare handle, not a caretaker
    assert g.revokers == {}


# ── Capability rotation ────────────────────────────────────────────
#
# Rotation re-points a named instance at a new backing handle at runtime, reusing
# the same caretaker the node holds — same identity, new target. Like revocation
# it is host-tier, opt-in, targeted, and administered by a separate authority; the
# two are granted independently. Distinct backing `ResponseChannel` objects (with
# their own `.sent` lists) make the re-point observable.


def test_rotator_re_points_the_caretaker_target():
    """The node's use is served by the original handle before rotation and the new
    one after — same caretaker object throughout."""
    first, second = ResponseChannel("a"), ResponseChannel("b")
    caretaker, rotator = rotatable(first)
    caretaker.send("to first")
    rotator.rotate(second)
    caretaker.send("to second")
    assert first.sent == ["to first"]
    assert second.sent == ["to second"]  # served by the new target after rotation


def test_rotation_preserves_capability_kind():
    """A caretaker promised the node a fixed surface; rotating to a different kind
    would break it, so the Rotator refuses."""
    _caretaker, rotator = rotatable(ResponseChannel("a"))
    with pytest.raises(CapabilityError, match="preserves capability kind"):
        rotator.rotate(ReadDBHandle("kb", {}))


def test_manage_mints_authorities_independently():
    """`manage` grants revoke and rotate independently — least authority."""
    _, revoker, rotator = manage(ResponseChannel("a"), rotatable=True)
    assert rotator is not None
    assert revoker is None  # not requested


def test_rotate_then_use_through_the_assembled_graph(graph):
    """End-to-end (spec: rotation re-points authority): a node bound to a rotatable
    instance is served by the new handle after the host rotates it."""
    g = assemble(
        graph,
        backend=StubLLM(),
        stores=STORES,
        identities={"SendReply": {RC: "session_a"}},
        rotatable_instances=[(RC, "session_a")],
    )
    handle = g.handle_for(g.nodes["SendReply"], RC)
    handle.send("before")

    replacement = ResponseChannel("rotated-in")
    g.rotate(RC, "session_a", replacement)
    handle.send("after")

    assert replacement.sent == ["after"]  # new target serves subsequent use


def test_rotation_is_targeted_to_one_instance(graph):
    """Rotating one instance leaves its distinct-identity sibling and the
    shared-by-type default unchanged."""
    g = assemble(
        graph,
        backend=StubLLM(),
        stores=STORES,
        identities={"SendReply": {RC: "session_a"}, "NotifyUser": {RC: "session_b"}},
        rotatable_instances=[(RC, "session_a")],
    )
    sibling = g.handle_for(g.nodes["NotifyUser"], RC)
    replacement = ResponseChannel("rotated-in")
    g.rotate(RC, "session_a", replacement)

    g.handle_for(g.nodes["SendReply"], RC).send("to new")
    sibling.send("to sibling")
    assert replacement.sent == ["to new"]
    # Sibling untouched — its own object, not the replacement, and never saw "to new".
    assert sibling.sent == ["to sibling"]


def test_nodes_never_receive_rotate_authority(graph):
    """The rotate authority is held only by the host; the node's caretaker exposes
    no rotate operation and is not a Rotator."""
    g = assemble(
        graph,
        backend=StubLLM(),
        stores=STORES,
        identities={"SendReply": {RC: "session_a"}},
        rotatable_instances=[(RC, "session_a")],
    )
    handle = g.handle_for(g.nodes["SendReply"], RC)
    assert not hasattr(handle, "rotate")
    assert not isinstance(handle, Rotator)
    assert isinstance(g.rotators[(RC, "session_a")], Rotator)


def test_revocable_and_rotatable_compose_on_one_instance(graph):
    """An instance can be both: rotate re-points it, revoke severs it, and severed
    wins (a revoked instance stays revoked after a rotate)."""
    g = assemble(
        graph,
        backend=StubLLM(),
        stores=STORES,
        identities={"SendReply": {RC: "session_a"}},
        revocable_instances=[(RC, "session_a")],
        rotatable_instances=[(RC, "session_a")],
    )
    handle = g.handle_for(g.nodes["SendReply"], RC)
    replacement = ResponseChannel("rotated-in")
    g.rotate(RC, "session_a", replacement)
    handle.send("served by new target")
    assert replacement.sent == ["served by new target"]

    g.revoke(RC, "session_a")
    with pytest.raises(RevokedCapabilityError):
        handle.send("nope")
    # Severed wins even over a further rotation.
    g.rotate(RC, "session_a", ResponseChannel("another"))
    with pytest.raises(RevokedCapabilityError):
        handle.send("still nope")


def test_rotatable_but_not_revocable_exposes_only_rotate(graph):
    """Authorities are granted independently: a rotatable-only instance has a
    rotator but no revoker."""
    g = assemble(
        graph,
        backend=StubLLM(),
        stores=STORES,
        identities={"SendReply": {RC: "session_a"}},
        rotatable_instances=[(RC, "session_a")],
    )
    assert (RC, "session_a") in g.rotators
    assert (RC, "session_a") not in g.revokers
    with pytest.raises(KeyError, match="no revocable instance"):
        g.revoke(RC, "session_a")


def test_rotatable_must_name_a_declared_identity(graph):
    with pytest.raises(AssemblyError, match=r"rotatable instance .* not a declared identity"):
        assemble(
            graph,
            backend=StubLLM(),
            stores=STORES,
            identities={"SendReply": {RC: "session_a"}},
            rotatable_instances=[(RC, "session_b")],
        )


def test_rotating_an_unprovisioned_instance_raises(graph):
    g = assemble(graph, backend=StubLLM(), stores=STORES)
    with pytest.raises(KeyError, match="no rotatable instance"):
        g.rotate(RC, "session_a", ResponseChannel("x"))


def test_no_rotatable_declaration_leaves_provisioning_unchanged(graph):
    """Opt-in: with no rotatable declaration, no caretaker and no rotator."""
    g = assemble(
        graph,
        backend=StubLLM(),
        stores=STORES,
        identities={"SendReply": {RC: "session_a"}},
    )
    handle = g.handle_for(g.nodes["SendReply"], RC)
    assert isinstance(handle, ResponseChannel)
    assert g.rotators == {}


@pytest.mark.parametrize("variant", sorted(set(UNSAFE_VARIANTS) - CROSS_GRAPH_VARIANTS))
def test_unsafe_variants_are_rejected_at_assembly(graph, variant):
    """Every intra-graph unsafe rewiring is refused when assembled alone. (Cross-graph
    variants rewrite the platform and need the referenced graph present; they are
    covered where that batch is available — see `test_poc_subgraph` and the evaluation
    corpus.)"""
    unsafe = UNSAFE_VARIANTS[variant](graph)
    assert validate_graph_dict(unsafe), "variant should not validate"
    with pytest.raises(AssemblyError):
        assemble(unsafe, backend=StubLLM(), stores=STORES)


def test_bypass_is_rejected_for_a_type_mismatch(graph):
    unsafe = UNSAFE_VARIANTS["bypass_pipeline"](graph)
    errors = " ".join(validate_graph_dict(unsafe))
    assert "type mismatch" in errors
    assert "Untrusted<RawMessage>" in errors


def test_laundering_trust_is_rejected_by_trust_propagation(graph):
    """The subtle variant type-checks on every edge, and is still rejected —
    now as a *trust-lattice* violation rather than by a separate side-condition.
    Widening the tool-capable node's input to `Untrusted<_>` makes the wire
    well-typed, but the node then raises trust (untrusted in, clean out) without
    being a declared discharger, which the lattice forbids as upward coercion."""
    unsafe = UNSAFE_VARIANTS["launder_trust"](graph)
    errors = " ".join(validate_graph_dict(unsafe))
    # Caught for a lattice reason: upward coercion / laundering, keyed on the
    # discharger marker — not by edge data-type incompatibility.
    assert "upward coercion" in errors
    assert "laundering" in errors
    assert "discharges_trust" in errors
    assert "type mismatch" not in errors


# ── Scoped capability lifetime ────────────────────────────────────────
#
# Borrowed from Effect's `Scope`: a resource acquired in a scope is finalised
# when the scope exits, so release is structural rather than remembered. Here
# the scope is the assembly itself, and what it finalises is granted authority.


def test_leaving_the_scope_severs_a_revocable_instance(graph):
    """Spec: authority granted for a run does not outlive the run. The handle is
    usable inside the scope and inert after it, with no explicit revoke call."""
    with assemble(
        graph,
        backend=StubLLM(),
        stores=STORES,
        identities={"SendReply": {RC: "session_a"}},
        revocable_instances=[(RC, "session_a")],
    ) as g:
        handle = g.handle_for(g.nodes["SendReply"], RC)
        assert handle.send("inside").delivered

    with pytest.raises(RevokedCapabilityError):
        handle.send("after the scope closed")


def test_scope_exit_severs_even_when_the_body_raises(graph):
    """A run that failed part-way is the case where leaked authority matters most,
    so the sever happens on the exception path too."""
    boom = RuntimeError("node blew up")
    try:
        with assemble(
            graph,
            backend=StubLLM(),
            stores=STORES,
            identities={"SendReply": {RC: "session_a"}},
            revocable_instances=[(RC, "session_a")],
        ) as g:
            handle = g.handle_for(g.nodes["SendReply"], RC)
            raise boom
    except RuntimeError as exc:
        assert exc is boom  # the scope re-raises rather than swallowing

    with pytest.raises(RevokedCapabilityError):
        handle.send("after the failed run")


def test_scope_exit_does_not_reach_a_bare_instance(graph):
    """The honest limit, pinned as a test so the paper cannot overstate it: an
    instance provisioned *without* `revocable_instances` has no caretaker to
    sever, so it survives the scope. Closing this gap would mean a proxy on every
    capability crossing, which is a design decision and not this change."""
    with assemble(
        graph,
        backend=StubLLM(),
        stores=STORES,
        identities={"SendReply": {RC: "session_a"}},
        # note: no revocable_instances — provisioned bare
    ) as g:
        bare = g.handle_for(g.nodes["SendReply"], RC)

    assert bare.send("still works").delivered  # outlives the scope, by design


def test_closing_is_idempotent_and_leaves_the_assembly_inspectable(graph):
    """Spec: `close()` twice is a no-op, and severing authority does not destroy
    the assembly — the graph stays readable for inspection afterwards."""
    g = assemble(
        graph,
        backend=StubLLM(),
        stores=STORES,
        identities={"SendReply": {RC: "session_a"}},
        revocable_instances=[(RC, "session_a")],
    )
    g.close()
    g.close()  # no raise

    assert "SendReply" in g.nodes  # still inspectable
    assert g.identities["SendReply"][RC] == "session_a"


def test_assembling_without_a_scope_is_unchanged(graph):
    """The bound is opt-in at the call site: every existing caller that does not
    use `with` keeps its previous behaviour."""
    g = assemble(
        graph,
        backend=StubLLM(),
        stores=STORES,
        identities={"SendReply": {RC: "session_a"}},
        revocable_instances=[(RC, "session_a")],
    )
    handle = g.handle_for(g.nodes["SendReply"], RC)
    assert handle.send("no scope, no sever").delivered


# ── Principal binding ────────────────────────────────────────────────────────
#
# The confused-deputy argument depends on capabilities being bound to the calling
# user and propagated downstream. These pin what the runtime now records, so the
# claim is checkable rather than asserted in prose. Shape follows RFC 8693: the
# principal is who the work is for, `acting_as` is the chain acting on their behalf.


def _principal_graph():
    """The canonical graph with its trust-discharging node also declared a
    principal binder — it holds an LLM capability, so it has authority to scope."""
    import copy

    from poc.graph import load_graph_dict

    g = copy.deepcopy(load_graph_dict("customer-support"))
    for n in g["nodes"]:
        if n["name"] == "ParseMessage":
            n["binds_principal"] = True
    return g


def _customer_request(body: str):
    from poc.values import CustomerRequest

    return CustomerRequest(session_id="user-session", body=body)


def test_a_run_without_a_principal_records_none(graph):
    """The feature is opt-in: a graph assembled without a principal behaves and
    serialises exactly as before."""
    from poc.demo import BENIGN
    from poc.runtime import execute

    g = assemble(graph, backend=StubLLM(), stores=STORES)
    trace = execute(g, _customer_request(BENIGN)).trace
    assert all(n.principal is None for n in trace.walk())
    assert all("principal" not in d for d in trace.to_dict()["nodes"])


def test_every_crossing_runs_on_the_bound_principal():
    """Spec: no node anywhere in a run acts outside the principal bound at entry."""
    from poc.demo import BENIGN
    from poc.runtime import execute

    g = assemble(_principal_graph(), backend=StubLLM(), stores=STORES, principal="alice")
    trace = execute(g, _customer_request(BENIGN)).trace
    seen = [n for n in trace.walk()]
    assert seen, "the run executed nodes"
    assert all(n.principal == "alice" for n in seen)


def test_only_a_declared_binder_extends_the_delegation_chain():
    """Spec: the acting-on-behalf-of hop happens where the graph says it does.
    Nodes before the binder carry an empty chain; nodes downstream carry it."""
    from poc.demo import BENIGN
    from poc.runtime import execute

    g = assemble(_principal_graph(), backend=StubLLM(), stores=STORES, principal="alice")
    trace = execute(g, _customer_request(BENIGN)).trace
    by_name = {n.node: n for n in trace.walk()}

    assert by_name["ReceiveMessage"].acting_as == [], "upstream of the binder"
    assert by_name["ParseMessage"].acting_as == [], "the binder itself acts as the principal"
    downstream = by_name.get("ModerateContent") or by_name.get("FetchContext")
    assert downstream is not None
    assert downstream.acting_as == ["ParseMessage"], "the binder delegates downstream"


def test_the_principal_crosses_the_composition_boundary():
    """Spec: a sub-graph acts on behalf of whoever the parent acts for, at every
    altitude — the child cannot provision a principal of its own."""
    from poc.demo import BENIGN
    from poc.runtime import execute
    from poc.values import HTTPRoute

    platform_stores = {
        "knowledge-base": {"billing_question": ["Duplicate charges clear in 3-5 days."]},
        "billing": {},
        "audit": {},
    }
    platform = assemble(
        load_graph_dict("support-platform"),
        backend=StubLLM(),
        stores=platform_stores,
        principal="alice",
    )
    traffic = HTTPRoute(path="/customer/message", session_id="user-session", body=BENIGN)
    trace = execute(platform, traffic).trace
    nested = [n for n in trace.walk() if n.subgraph is None]
    assert any(n.principal == "alice" for n in nested)
    assert all(n.principal == "alice" for n in trace.walk())


def test_a_binder_holding_no_capability_is_rejected(graph):
    """Spec: a binder with no authority to scope binds nothing, so the validator
    rejects it — the same class of error as a discharge with no untrusted input."""
    import copy

    g = copy.deepcopy(graph)
    for n in g["nodes"]:
        if n["name"] == "ReceiveMessage":  # pure node, holds no capability
            n["binds_principal"] = True
    with pytest.raises(AssemblyError) as excinfo:
        assemble(g, backend=StubLLM(), stores=STORES)
    assert "binds_principal" in str(excinfo.value)
    assert "no authority to scope" in str(excinfo.value) or "binds nothing" in str(excinfo.value)
