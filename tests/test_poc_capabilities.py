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
    EventEmitter,
    InferenceLLM,
    ReadDBHandle,
    ResponseChannel,
    ToolLLM,
    provision,
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
