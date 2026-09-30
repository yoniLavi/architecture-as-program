"""Unsafe rewirings of the customer-support graph.

These exist to be *rejected*. Each is a plausible mistake an author (or an agent)
could make, and each is caught at assembly time by the project's graph validator
— not by a runtime check, a lint rule, or a code review. This is the concrete
form of the proposal's claim that the dangerous shape is ill-typed.
"""

from __future__ import annotations

import copy


def bypass_pipeline(graph: dict) -> dict:
    """Wire raw untrusted input straight into the tool-capable node.

    `ReceiveMessage` emits `Untrusted<RawMessage>`; `GenerateResponse` wants a
    `ConversationContext`. Rejected on edge type-compatibility."""
    g = copy.deepcopy(graph)
    for edge in g["data_edges"]:
        if edge["from"] == "FetchContext" and edge["to"] == "GenerateResponse":
            edge["from"] = "ReceiveMessage"
    return g


def launder_trust(graph: dict) -> dict:
    """The subtler mistake: make the tool-capable node *accept* untrusted input.

    Here the author "fixes" the type error above by widening `GenerateResponse`'s
    input to `Untrusted<RawMessage>` — so the edge now type-checks. It is still
    rejected, by trust propagation: the node consumes an `Untrusted<_>` input and
    emits a non-`Untrusted` output without declaring `discharges_trust`. Trust
    cannot be laundered by relabelling the consumer."""
    g = copy.deepcopy(graph)
    for node in g["nodes"]:
        if node["name"] == "GenerateResponse":
            node["inputs"] = [
                "Untrusted<RawMessage>" if i == "ConversationContext" else i for i in node["inputs"]
            ]
    for edge in g["data_edges"]:
        if edge["from"] == "FetchContext" and edge["to"] == "GenerateResponse":
            edge["from"] = "ReceiveMessage"
    return g


def launder_trust_via_variant(graph: dict) -> dict:
    """`launder_trust`, disguised by a sum type.

    The tool-capable node again accepts the raw `Untrusted<RawMessage>`, but now
    marks *one* variant of its output `Untrusted<_>` (its `error` branch, relabelled
    through `HandleLLMError`). A check that took the whole sum's trust as that of
    its least-trusted variant saw an untrusted output and passed the node, while
    its `ok` variant left on its own port as a clean `AgentResponse` — laundering
    through the one variant nobody looked at. Each variant leaves on its own port,
    so each is checked on its own, and the node is rejected as upward coercion."""
    g = launder_trust(graph)
    for node in g["nodes"]:
        if node["name"] == "GenerateResponse":
            node["output"] = "ok: AgentResponse | error: Untrusted<LLMError>"
        if node["name"] == "HandleLLMError":
            node["inputs"] = [
                "Untrusted<LLMError>" if i == "LLMError" else i for i in node["inputs"]
            ]
            node["output"] = "Untrusted<DeliveryConfirmation>"
    return g


def launder_trust_by_declaration(graph: dict) -> dict:
    """`launder_trust`, excused by declaring the tool-capable consumer a discharger.

    Declaring `discharges_trust` is the licence to raise trust, so marking the
    consumer itself as one made the laundering graph pass every lattice check. A
    node holding a tool-scoped client cannot be its own discharger: the sink rule
    rejects it."""
    g = launder_trust(graph)
    for node in g["nodes"]:
        if node["name"] == "GenerateResponse":
            node["discharges_trust"] = True
    return g


def untrusted_into_tool_node(graph: dict) -> dict:
    """Raw untrusted input into the tool-capable node, labelled consistently.

    `launder_trust` again, but the node's outputs — and everything downstream —
    stay `Untrusted<_>`, so no node *raises* trust. The lattice constrains raising
    trust, not consuming it, so this passed: the adversarial message reached the
    tool-holding model directly. The sink rule rejects it: a node holding a
    tool-scoped client may not consume `Untrusted<_>` at all."""
    g = launder_trust(graph)
    for node in g["nodes"]:
        if node["name"] == "GenerateResponse":
            node["output"] = "ok: Untrusted<AgentResponse> | error: Untrusted<LLMError>"
        if node["name"] == "SendReply":
            node["inputs"] = [
                "Untrusted<AgentResponse>" if i == "AgentResponse" else i for i in node["inputs"]
            ]
            node["output"] = "Untrusted<DeliveryConfirmation>"
        if node["name"] == "HandleLLMError":
            node["inputs"] = [
                "Untrusted<LLMError>" if i == "LLMError" else i for i in node["inputs"]
            ]
            node["output"] = "Untrusted<DeliveryConfirmation>"
    return g


def delegate_via_edge(graph: dict) -> dict:
    """Pass a capability along a data edge.

    `FetchContext` returns its knowledge-base handle, wrapped, as its output, and
    `GenerateResponse` receives it on the edge instead of through its `with`
    clause. Object discipline permits this reference passing; the signal graph
    gives it up so the authority topology stays statically analysable. A
    capability type in a data position is rejected."""
    g = copy.deepcopy(graph)
    carried = "Grant<DBHandle<'knowledge-base', read>>"
    for node in g["nodes"]:
        if node["name"] == "FetchContext":
            node["output"] = carried
        if node["name"] == "GenerateResponse":
            node["inputs"] = [carried if i == "ConversationContext" else i for i in node["inputs"]]
    return g


def route_tool_into_inference_slot(platform: dict) -> dict:
    """Route the platform's tool-scoped client into `CustomerSupport`'s
    inference-only slot.

    `LLMClient<[lookup]>` is assignable where `LLMClient<inference>` is expected
    (narrowing), and the handle is routed whole. The child's `ParseMessage` —
    declared inference-only, and a discharger consuming `Untrusted<_>` — would then
    hold a tool client the sink rule, which reads declared clauses, never saw."""
    g = copy.deepcopy(platform)
    for node in g["nodes"]:
        if node["name"] == "CustomerSupport":
            node["inputs"] = [
                "LLMClient<[lookup]>" if i == "LLMClient<inference>" else i for i in node["inputs"]
            ]
    # The platform's inference client is now held by no node; drop it, so the only
    # fault left is the routing, not an unused capability.
    still_used = any("LLMClient<inference>" in n["inputs"] for n in g["nodes"])
    if not still_used:
        g["parameters"] = [p for p in g["parameters"] if p != "LLMClient<inference>"]
        g["capabilities"] = [c for c in g["capabilities"] if c != "LLMClient<inference>"]
    return g


def launder_via_duplicate_role(graph: dict) -> dict:
    """Two variants under one role label.

    `ReceiveMessage` declares `ok: ConversationContext | ok: Untrusted<RawMessage>`
    and its `ok` port is wired straight to the tool-capable node. The runtime routes
    by role, so both variants leave on that port, but the edge check resolved the
    role to the first variant only — a clean `ConversationContext` — and the raw
    untrusted message reached `GenerateResponse`. A port must name one variant, so
    a repeated role is rejected when the type is parsed."""
    g = copy.deepcopy(graph)
    for node in g["nodes"]:
        if node["name"] == "ReceiveMessage":
            node["output"] = "ok: ConversationContext | ok: Untrusted<RawMessage>"
    g["data_edges"] = [e for e in g["data_edges"] if e["from"] != "ReceiveMessage"]
    g["data_edges"].append({"from": "ReceiveMessage.ok", "to": "GenerateResponse"})
    return g


def hide_branch_behind_whole_edge(graph: dict) -> dict:
    """Consume a labelled sum on an unported edge.

    `NotifyUser` takes `ModerateContent`'s whole `ok | violation | escalation` sum on
    an edge with no port, and the per-variant `violation` and `escalation` edges are
    removed. The validator once read an unported edge as covering every variant;
    the runtime routes a variant by its role and never sends one along it, so a
    policy violation was swallowed with no notification, no escalation, no error."""
    g = copy.deepcopy(graph)
    whole = "ok: ModeratedQuery | violation: PolicyViolation | escalation: EscalationRequest"
    for node in g["nodes"]:
        if node["name"] == "NotifyUser":
            node["inputs"] = [whole if i == "PolicyViolation" else i for i in node["inputs"]]
    g["data_edges"] = [
        e
        for e in g["data_edges"]
        if e["from"] not in ("ModerateContent.violation", "ModerateContent.escalation")
    ]
    g["data_edges"].append({"from": "ModerateContent", "to": "NotifyUser"})
    return g


def hide_branch_behind_unlabelled_variant(graph: dict) -> dict:
    """Drop one variant's role in a labelled sum.

    `ModerateContent` declares `ok: ModeratedQuery | PolicyViolation | escalation:
    EscalationRequest` and its `violation` edge is removed. Variant completeness
    swept the roles, so the unlabelled variant was never checked; the unported edge
    that could carry it is refused for a labelled sum; and the runtime, finding no
    edge for it at a node that is not a terminal, dropped it — the policy violation
    `hide_branch_behind_whole_edge` swallowed, spelled differently. A sum is labelled
    throughout or not at all."""
    g = copy.deepcopy(graph)
    for node in g["nodes"]:
        if node["name"] == "ModerateContent":
            node["output"] = "ok: ModeratedQuery | PolicyViolation | escalation: EscalationRequest"
    g["data_edges"] = [e for e in g["data_edges"] if e["from"] != "ModerateContent.violation"]
    return g


def mislabel_subgraph_output(platform: dict) -> dict:
    """Make a sub-graph node lie about what it emits at its boundary.

    Operates on `support-platform`, not `customer-support`: the mistake this catches
    lives at a *composition* boundary. `CustomerSupport` terminates at
    `DeliveryConfirmation` (its reply paths) or `EscalationTicket` (its escalation
    path), so its honest boundary output is the union of the two. Here every service
    node — and the `RecordAudit` input that consumes them — is relabelled to claim
    only `DeliveryConfirmation`, hiding the escalation path. Every *edge* still
    type-checks (the relabelling is internally consistent), so the blunt edge check
    sees nothing wrong. It is caught only by the cross-graph *output-side* check,
    which relates a sub-graph node's declared output to the union of the referenced
    graph's terminal types — the check that closed the `ServiceOutcome` gap. Must be
    validated together with `customer-support`, since the cross-graph analysis needs
    the referenced graph present."""
    g = copy.deepcopy(platform)
    for node in g["nodes"]:
        if node["name"] in ("CustomerSupport", "AgentDashboard", "BillingService"):
            node["output"] = "DeliveryConfirmation"
        if node["name"] == "RecordAudit":
            node["inputs"] = [
                "DeliveryConfirmation" if i == "DeliveryConfirmation | EscalationTicket" else i
                for i in node["inputs"]
            ]
    return g


def unevaluatable_contract(graph: dict) -> dict:
    """Attach a contract the closed vocabulary cannot express.

    A different *kind* of fault from the other three: not an unsafe wiring but an
    unevaluatable specification. It is in the corpus because the contract layer's
    whole claim rests on the vocabulary having a ceiling — a predicate that quietly
    evaluated to false instead of being rejected would make every contract's
    silence ambiguous, which is worse than having no contracts at all."""
    g = copy.deepcopy(graph)
    for node in g["nodes"]:
        if node["name"] == "ParseMessage":
            node["requires"] = ["forall x. x > 0"]
    return g


UNSAFE_VARIANTS = {
    "bypass_pipeline": bypass_pipeline,
    "launder_trust": launder_trust,
    "launder_trust_via_variant": launder_trust_via_variant,
    "launder_trust_by_declaration": launder_trust_by_declaration,
    "untrusted_into_tool_node": untrusted_into_tool_node,
    "delegate_via_edge": delegate_via_edge,
    "route_tool_into_inference_slot": route_tool_into_inference_slot,
    "launder_via_duplicate_role": launder_via_duplicate_role,
    "hide_branch_behind_whole_edge": hide_branch_behind_whole_edge,
    "hide_branch_behind_unlabelled_variant": hide_branch_behind_unlabelled_variant,
    "mislabel_subgraph_output": mislabel_subgraph_output,
    "unevaluatable_contract": unevaluatable_contract,
}

# Variants whose fault is only visible with a *second* graph in the validation
# batch (a sub-graph reference to another graph). They rewrite `support-platform`,
# not `customer-support`, and must be validated together with the referenced graph
# — so a single-graph rejection test does not apply to them. The evaluation corpus
# (`poc/evaluate.py`) and `tests/test_poc_subgraph.py` cover them with the child
# graph present.
CROSS_GRAPH_VARIANTS = frozenset({"mislabel_subgraph_output", "route_tool_into_inference_slot"})
