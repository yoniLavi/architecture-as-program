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
    """The subtle variant type-checks on the edge, and is still rejected:
    trust cannot be laundered by widening the consumer's input type."""
    unsafe = UNSAFE_VARIANTS["launder_trust"](graph)
    errors = " ".join(validate_graph_dict(unsafe))
    assert "discharges_trust" in errors
    assert "type mismatch" not in errors
