"""Domain value types that flow along the customer-support signal graph.

These are the runtime inhabitants of the graph's data types. They are plain
dataclasses; the security-relevant property is *structural*: a node downstream of
`ParseMessage` receives a `CustomerQuery` (intent + bounded fields), never the
original `Untrusted[RawMessage]` value. The raw adversarial text is consumed at
the parse boundary and is not reachable from the structured representation.

`Untrusted[T]` is modelled as a thin wrapper so the runtime can mirror the
proposal's `Untrusted<T>` trust marker at the value level, and so tests can
assert that an untrusted value never reaches a node that expects a clean type.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class Untrusted(Generic[T]):
    """Trust marker. Wraps a value entering from an untrusted source. The
    only legitimate way to remove the wrapper is a trust-discharging node
    (in this graph, `ParseMessage`)."""

    value: T


# ── Boundary input ─────────────────────────────────────────────────


@dataclass(frozen=True)
class CustomerRequest:
    """Domain entry type — a narrowed representation of inbound HTTP traffic."""

    session_id: str
    body: str


@dataclass(frozen=True)
class RawMessage:
    """Free-text customer message, before any parsing. Always handled wrapped
    in `Untrusted[...]`."""

    text: str


# ── Structured, post-parse representation ──────────────────────────


class Intent(Enum):
    """Finite, closed set of customer intents. `ParseMessage` classifies the
    raw message into exactly one of these — adversarial free text cannot widen
    this set."""

    BILLING_QUESTION = "billing_question"
    TECHNICAL_SUPPORT = "technical_support"
    ACCOUNT_CHANGE = "account_change"
    GENERAL_INQUIRY = "general_inquiry"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class CustomerQuery:
    """Constrained representation produced by `ParseMessage`. The original raw
    text is discarded; what remains is a classified intent, extracted entity
    references, and a single bounded question field.

    The `question` field is, deliberately, the place where free text survives —
    the proposal is explicit that most real schemas retain a free-text field for
    the question itself, and that this field must be treated as adversarial at
    every point where it reaches an LLM-capable node. The PoC carries it so the
    demonstration can be honest about residual exposure rather than pretending
    free text vanishes entirely."""

    intent: Intent
    entities: tuple[str, ...]
    question: str  # bounded, but still adversarial data — see GenerateResponse

    MAX_QUESTION_LEN: int = field(default=512, compare=False)


@dataclass(frozen=True)
class ModeratedQuery:
    """A `CustomerQuery` that has passed content moderation. The distinct type
    records, at the type level, that moderation has occurred — downstream nodes
    accept only `ModeratedQuery`, so a wiring that bypasses moderation is
    ill-typed."""

    query: CustomerQuery


@dataclass(frozen=True)
class PolicyViolation:
    reason: str


@dataclass(frozen=True)
class EscalationRequest:
    query: CustomerQuery
    reason: str


# ── Response side ──────────────────────────────────────────────────


@dataclass(frozen=True)
class ConversationContext:
    """Assembled from a `ModeratedQuery` plus knowledge-base lookups. This is the
    sole input to the tool-capable `GenerateResponse` node — note it is built
    from the *moderated query*, never from `Untrusted[RawMessage]`."""

    intent: Intent
    question: str
    knowledge: tuple[str, ...]


@dataclass(frozen=True)
class AgentResponse:
    text: str


@dataclass(frozen=True)
class LLMError:
    message: str


@dataclass(frozen=True)
class DeliveryConfirmation:
    session_id: str
    delivered: bool


@dataclass(frozen=True)
class EscalationTicket:
    ticket_id: str


# ── Composition-level types (the SupportPlatform boundary) ─────────
#
# These exist at the *platform* altitude: the types `SupportPlatform` wires
# between its service sub-graphs, as distinct from the types flowing inside any
# one of them.


@dataclass(frozen=True)
class HTTPRoute:
    """`HTTPRoute<'platform:*'>` — inbound traffic at the platform boundary.

    The platform's data parameter, before dispatch has decided which service owns
    it. `RouteRequest` narrows it to a domain request type; no service graph ever
    sees this type, which is the point — `CustomerSupport` takes a
    `CustomerRequest` and so serves both a standalone deployment (a direct HTTP
    adaptor) and this composed one without signature churn."""

    path: str
    session_id: str
    body: str


@dataclass(frozen=True)
class AgentRequest:
    session_id: str
    body: str


@dataclass(frozen=True)
class BillingRequest:
    session_id: str
    body: str


@dataclass(frozen=True)
class AuditConfirmation:
    record_id: str


# `ServiceOutcome` is the boundary output every service sub-graph presents to the
# platform, and it is a *type alias for the union of that sub-graph's terminal
# types* — option (i) of Technical Note A's "sub-graph output aggregation", which
# the proposal names as the working convention of the composition example.
# `CustomerSupport` terminates at `DeliveryConfirmation` (its three reply paths) or
# `EscalationTicket` (its escalation path), and exactly one of those is reached per
# run, so the value the boundary hands back is always a member of this union.
#
# It is an alias rather than a wrapper deliberately: no aggregation node exists in
# the graph, and inventing a runtime wrapper here would encode a design decision
# (option iii) the proposal has not made. The cost is that nothing checks the
# alias — the graph language has no alias mechanism, so `ServiceOutcome` is a name
# the JSON asserts and the tooling cannot relate to the terminals it abbreviates.
# That gap is real and remains open in Technical Note A.
ServiceOutcome = DeliveryConfirmation | EscalationTicket


# ── Variant tagging for sum-typed node outputs ─────────────────────


@dataclass(frozen=True)
class Variant:
    """A tagged output value for nodes whose output is a sum type, e.g.
    `ModerateContent` emitting `ok: ModeratedQuery | violation: ... `. The
    `role` selects which outgoing edge (`Node.role`) the runtime follows."""

    role: str
    value: object
