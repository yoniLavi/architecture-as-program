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
from .handles import AppendDBHandle, InferenceLLM, ReadDBHandle, ResponseChannel, ToolLLM
from .values import (
    AgentRequest,
    AgentResponse,
    AuditConfirmation,
    BillingRequest,
    ConversationContext,
    CustomerRequest,
    DeliveryConfirmation,
    EscalationRequest,
    EscalationTicket,
    HTTPRoute,
    LLMError,
    ModeratedQuery,
    PolicyViolation,
    RawMessage,
    ServiceOutcome,
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


# ── SupportPlatform's own leaves ────────────────────────────────────
#
# The composition graph's service nodes (`CustomerSupport`, `AgentDashboard`,
# `BillingService`) need no implementations: a node whose name resolves to a graph
# *is* that graph, and the runtime executes it by nested assembly. Only the
# platform's own leaf nodes need bodies, and only those on a path actually taken —
# `AgentDashboard` and `BillingService` are not graphs in this repository and have
# no implementations here, so the agent and billing branches do not run. That is a
# deliberate scope boundary of the composition demonstration, not an oversight:
# neither is needed to show that a boundary signal crosses into a sub-graph and its
# output crosses back.


def route_request(route: HTTPRoute) -> Variant:
    """Dispatch inbound platform traffic to the service that owns it.

    The narrowing step that lets `CustomerSupport` keep a domain entry type: the
    platform's `HTTPRoute` never reaches a service graph."""
    if route.path.startswith("/agent"):
        return Variant(
            role="agent", value=AgentRequest(session_id=route.session_id, body=route.body)
        )
    if route.path.startswith("/billing"):
        return Variant(
            role="billing", value=BillingRequest(session_id=route.session_id, body=route.body)
        )
    return Variant(
        role="customer", value=CustomerRequest(session_id=route.session_id, body=route.body)
    )


def record_audit(outcome: ServiceOutcome, audit: AppendDBHandle) -> AuditConfirmation:
    """Append a service's outcome to the audit log.

    Its `DBHandle<'audit', append>` has no `read`, so the node that records
    outcomes cannot read the log back — the append/read incomparability of the mode
    lattice, at the composition altitude.

    `outcome` is a `ServiceOutcome`: the union of whichever terminal type the
    service sub-graph actually reached. Both members are matched explicitly rather
    than stringified, so a third terminal type appearing in a service graph fails
    here instead of being silently audited as its `repr`."""
    if isinstance(outcome, DeliveryConfirmation):
        record = f"delivered to {outcome.session_id} (ok={outcome.delivered})"
        key = outcome.session_id
    elif isinstance(outcome, EscalationTicket):
        record = f"escalated as {outcome.ticket_id}"
        key = outcome.ticket_id
    else:
        raise TypeError(
            f"not a ServiceOutcome: {type(outcome).__name__}. The boundary type is the "
            f"union of the service sub-graph's terminal types (research agenda, "
            f"sub-graph output aggregation)."
        )
    audit.append(record)
    return AuditConfirmation(record_id=f"AUD-{abs(hash(key)) % 100000:05d}")


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
    # SupportPlatform's leaves (the service nodes are sub-graphs, not entries here).
    "RouteRequest": route_request,
    "RecordAudit": record_audit,
}
