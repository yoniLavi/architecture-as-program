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


UNSAFE_VARIANTS = {
    "bypass_pipeline": bypass_pipeline,
    "launder_trust": launder_trust,
    "mislabel_subgraph_output": mislabel_subgraph_output,
}

# Variants whose fault is only visible with a *second* graph in the validation
# batch (a sub-graph reference to another graph). They rewrite `support-platform`,
# not `customer-support`, and must be validated together with the referenced graph
# — so a single-graph rejection test does not apply to them. The evaluation corpus
# (`poc/evaluate.py`) and `tests/test_poc_subgraph.py` cover them with the child
# graph present.
CROSS_GRAPH_VARIANTS = frozenset({"mislabel_subgraph_output"})
