"""Node implementations for the customer-support graph.

Each implementation has the uniform shape ``impl(data_value, *capability_handles)``
where the handles appear in the same order as the node's capability inputs in the
graph JSON. The runtime treats these as opaque: it wires the upstream value and
the declared handles in, and routes the output onward. A node can only reach
external authority through the handles it is passed.

`ParseMessage` is the AI-generated node (see `poc/generated/`); the copy here is
imported from that module so the generated artifact is the one that actually runs.
"""

from __future__ import annotations

from collections.abc import Callable

from .generated.parse_message import parse_message
from .handles import InferenceLLM, ReadDBHandle, ResponseChannel, ToolLLM
from .values import (
    AgentResponse,
    ConversationContext,
    CustomerRequest,
    DeliveryConfirmation,
    EscalationRequest,
    EscalationTicket,
    LLMError,
    ModeratedQuery,
    PolicyViolation,
    RawMessage,
    Untrusted,
    Variant,
)

# A node implementation: takes its data value plus its capability handles.
NodeImpl = Callable[..., object]


def receive_message(req: CustomerRequest) -> Untrusted[RawMessage]:
    """Pure node — narrows the inbound request to a raw, untrusted message."""
    return Untrusted(RawMessage(text=req.body))


# parse_message: the AI-generated trust-discharging node, imported above.


def moderate_content(query, llm: InferenceLLM) -> Variant:
    """Inference-only moderation. Holding `LLMClient<inference>`, this node can be
    influenced by adversarial text but cannot act on it. Emits a three-way sum."""
    verdict = (
        llm.infer(
            system="You are a content-moderation classifier. Reply with exactly one of: "
            "ok, violation, escalation.",
            prompt=query.question,
            task="moderate",
        )
        .strip()
        .lower()
    )
    if verdict == "violation":
        return Variant("violation", PolicyViolation(reason="content policy"))
    if verdict == "escalation":
        return Variant("escalation", EscalationRequest(query=query, reason="ambiguous"))
    return Variant("ok", ModeratedQuery(query=query))


def fetch_context(mq: ModeratedQuery, db: ReadDBHandle) -> ConversationContext:
    """Read-only knowledge-base lookup. No write authority."""
    knowledge = tuple(db.read(mq.query.intent.value))
    return ConversationContext(
        intent=mq.query.intent,
        question=mq.query.question,
        knowledge=knowledge,
    )


def generate_response(ctx: ConversationContext, llm: ToolLLM, db: ReadDBHandle) -> Variant:
    """Tool-capable response generation. The LLM is scoped to exactly one tool
    (`lookup`); any attempt to call another tool raises `CapabilityError` inside
    the handle. The input is a `ConversationContext` assembled from the moderated
    query — the `Untrusted[RawMessage]` value never reaches here."""

    def lookup(query: str) -> str:
        hits = db.read(query) or db.read(ctx.intent.value)
        return "; ".join(hits) if hits else "no knowledge-base match"

    try:
        text = llm.respond(
            system="You are a helpful customer-support agent. Use the lookup tool if needed.",
            prompt=ctx.question,
            tools={"lookup": lookup},
        )
    except Exception as e:
        return Variant("error", LLMError(message=str(e)))
    return Variant("ok", AgentResponse(text=text))


def send_reply(resp: AgentResponse, channel: ResponseChannel) -> DeliveryConfirmation:
    return channel.send(resp.text)


def handle_llm_error(err: LLMError, channel: ResponseChannel) -> DeliveryConfirmation:
    return channel.send(f"Sorry — we hit an error: {err.message}")


def notify_user(violation: PolicyViolation, channel: ResponseChannel) -> DeliveryConfirmation:
    return channel.send(f"Your message could not be processed: {violation.reason}")


def escalate_to_human(req: EscalationRequest, emitter) -> EscalationTicket:
    ticket_id = f"ESC-{abs(hash(req.query.question)) % 100000:05d}"
    emitter.emit(f"{ticket_id}: {req.reason}")
    return EscalationTicket(ticket_id=ticket_id)


# Registry keyed by the graph's node names.
REGISTRY: dict[str, NodeImpl] = {
    "ReceiveMessage": receive_message,
    "ParseMessage": parse_message,
    "ModerateContent": moderate_content,
    "FetchContext": fetch_context,
    "GenerateResponse": generate_response,
    "SendReply": send_reply,
    "HandleLLMError": handle_llm_error,
    "NotifyUser": notify_user,
    "EscalateToHuman": escalate_to_human,
}
