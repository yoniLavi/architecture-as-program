"""Execution of the security vertical, and prompt-injection attenuation.

Covers the `signal-graph-runtime` spec requirements:
  - Security vertical executes end-to-end
  - Prompt-injection attenuation is demonstrated
"""

from __future__ import annotations

from poc.demo import ADVERSARIAL, BENIGN, STORES
from poc.graph import assemble, load_graph_dict
from poc.llm import StubLLM
from poc.runtime import execute
from poc.values import (
    ConversationContext,
    CustomerQuery,
    CustomerRequest,
    DeliveryConfirmation,
    Intent,
    ModeratedQuery,
    RawMessage,
    Untrusted,
)

VERTICAL = [
    "ReceiveMessage",
    "ParseMessage",
    "ModerateContent",
    "FetchContext",
    "GenerateResponse",
    "SendReply",
]


def run(message: str):
    graph = assemble(load_graph_dict("customer-support"), backend=StubLLM(), stores=STORES)
    return execute(graph, CustomerRequest(session_id="user-session", body=message))


# ── The vertical runs ──────────────────────────────────────────────


def test_benign_message_flows_through_the_vertical_to_a_delivered_reply():
    result = run(BENIGN)
    assert result.order == VERTICAL
    confirmation = result.terminals["SendReply"]
    assert isinstance(confirmation, DeliveryConfirmation)
    assert confirmation.delivered


def test_execution_is_deterministic_offline():
    assert run(BENIGN).order == run(BENIGN).order


def test_moderation_is_load_bearing_in_the_type():
    """`FetchContext` accepts only a `ModeratedQuery` — a distinct type that
    records at the type level that moderation happened."""
    result = run(BENIGN)
    assert isinstance(result.received["FetchContext"], ModeratedQuery)


def test_context_is_assembled_from_the_knowledge_base():
    result = run(BENIGN)
    ctx = result.received["GenerateResponse"]
    assert isinstance(ctx, ConversationContext)
    assert ctx.knowledge, "read-only DB handle should have supplied KB articles"


# ── Prompt-injection attenuation ───────────────────────────────────


def test_trust_is_discharged_at_the_parse_boundary():
    """`ParseMessage` receives `Untrusted[RawMessage]` and emits a plain
    `CustomerQuery`; every node downstream of it sees non-`Untrusted` values."""
    result = run(ADVERSARIAL)

    raw = result.received["ParseMessage"]
    assert isinstance(raw, Untrusted)
    assert isinstance(raw.value, RawMessage)

    for node in ("ModerateContent", "FetchContext", "GenerateResponse", "SendReply"):
        assert not isinstance(result.received[node], Untrusted)


def test_inference_only_nodes_are_never_offered_a_tool():
    """Whatever the adversarial text says, `ParseMessage` and `ModerateContent`
    hold `LLMClient<inference>` — the model is never told a tool exists, and the
    handle exposes no way to call one."""
    backend = StubLLM()
    graph = assemble(load_graph_dict("customer-support"), backend=backend, stores=STORES)
    execute(graph, CustomerRequest(session_id="user-session", body=ADVERSARIAL))

    inference_calls = [c for c in backend.calls if c.task in ("classify", "moderate")]
    assert inference_calls, "parse and moderate should have called the model"
    for call in inference_calls:
        assert call.offered_tools == ()


def test_tool_capable_node_never_receives_the_untrusted_value():
    """`GenerateResponse` receives a `ConversationContext` built from the
    moderated query and KB lookups — the `Untrusted[RawMessage]` object is not
    reachable from its input."""
    result = run(ADVERSARIAL)
    ctx = result.received["GenerateResponse"]
    assert isinstance(ctx, ConversationContext)
    assert not isinstance(ctx, Untrusted)
    assert not isinstance(ctx, RawMessage)


def test_adversarial_input_cannot_widen_the_intent_set():
    """The intent is drawn from a closed enum. Adversarial text may cause a
    *misclassification*, but cannot introduce a new intent."""
    result = run(ADVERSARIAL)
    query = result.received["ModerateContent"]
    assert isinstance(query, CustomerQuery)
    assert query.intent in set(Intent)


def test_adversarial_run_still_completes_without_any_tool_escape():
    """The pipeline completes normally; no CapabilityError escapes, because no
    node ever had the authority the adversarial text tried to invoke."""
    result = run(ADVERSARIAL)
    assert result.order == VERTICAL
    assert isinstance(result.terminals["SendReply"], DeliveryConfirmation)


# ── The residual, asserted honestly ────────────────────────────────


def test_free_text_residual_is_real_and_acknowledged():
    """This test documents a LIMITATION, not a guarantee.

    The bounded `question` field survives parsing, so adversarial text does reach
    the tool-capable node as *data*. The proposal says exactly this. What bounds
    the damage is the capability scope (`LLMClient<[lookup]>`), not the absence
    of the text. If this test ever starts failing because the text no longer
    survives, that is a schema change worth noticing — not a free win."""
    result = run(ADVERSARIAL)
    ctx = result.received["GenerateResponse"]
    assert isinstance(ctx, ConversationContext)
    assert "ignore all previous instructions" in ctx.question.lower()
