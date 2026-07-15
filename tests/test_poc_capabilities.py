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
    CapabilityError,
    Caretaker,
    EventEmitter,
    InferenceLLM,
    ReadDBHandle,
    ResponseChannel,
    RevokedCapabilityError,
    Revoker,
    Rotator,
    ToolLLM,
    manage,
    provision,
    revocable,
    rotatable,
)
from poc.llm import LLMRequest, LLMResponse, StubLLM, ToolCall
from poc.variants import UNSAFE_VARIANTS

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


def test_sinks_are_write_only():
    assert not hasattr(ResponseChannel("s"), "read")
    assert not hasattr(EventEmitter("t"), "read")


# ── Provisioning: capability type string → handle ──────────────────


@pytest.mark.parametrize(
    ("cap", "expected"),
    [
        ("LLMClient<inference>", InferenceLLM),
        ("LLMClient<[lookup]>", ToolLLM),
        ("DBHandle<'knowledge-base', read>", ReadDBHandle),
        ("ResponseChannel<user-session>", ResponseChannel),
        ("EventEmitter<'support-queue'>", EventEmitter),
    ],
)
def test_provision_builds_the_right_handle(cap, expected):
    handle = provision(cap, backend=StubLLM(), stores=STORES)
    assert isinstance(handle, expected)


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


@pytest.mark.parametrize("variant", sorted(UNSAFE_VARIANTS))
def test_unsafe_variants_are_rejected_at_assembly(graph, variant):
    """Neither unsafe rewiring can be assembled — the runtime refuses to run it."""
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
