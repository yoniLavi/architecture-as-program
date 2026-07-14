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


UNSAFE_VARIANTS = {
    "bypass_pipeline": bypass_pipeline,
    "launder_trust": launder_trust,
}
