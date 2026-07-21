"""Sub-graph execution: a node whose body is another graph.

The proposal's headline structural claim is hierarchical composition, and until
now it was demonstrated statically (the cross-graph validator checks a sub-graph
reference's signature) and at assembly (capability identity routes across the
boundary) but never *operationally*. These tests cover the runtime half: a
boundary signal enters a sub-graph, the sub-graph runs, and its output comes back
out as the parent node's output.

Two levels are covered. Small purpose-built fixtures isolate each property of the
mechanism (routing, identity, isolation, the guards) without dragging the whole
support platform through every assertion; the shipped `SupportPlatform` then
exercises the same machinery end-to-end, which is the claim that matters.

A note on `ServiceOutcome`, since it used to be a hole and is now closed.
`CustomerSupport` ends at four terminals emitting two types
(`DeliveryConfirmation`, `EscalationTicket`). The `SupportPlatform` node that runs
it declares that union as its boundary output — spelled structurally, because the
graph language has no alias *mechanism* to resolve a bare `ServiceOutcome` name.
Exactly one terminal is reached per run (the branches are exclusive), so the value
handed back is always a member of the union. The cross-graph analysis now checks
the output side too: a sub-graph node's declared boundary type must equal the union
of the referenced graph's terminal outputs, so a node can no longer misdescribe
what it emits. A test below pins that the check accepts the honest spelling and
rejects a narrowed one.

What the runtime does refuse is a sub-graph run reaching *several* terminals at
once: there is then no single boundary value, and picking one would be a guess.

Covers the `signal-graph-runtime` spec requirements added by `add-subgraph-execution`:
  - The runtime executes sub-graph nodes
  - A sub-graph's boundary output is delivered as the parent node's output
"""

from __future__ import annotations

import copy

import pytest

from poc.graph import TIER_GRAPH, assemble, load_graph_dict, validate_graph_dicts
from poc.handles import AppendDBHandle, ResponseChannel
from poc.llm import StubLLM
from poc.nodes import REGISTRY
from poc.runtime import ExecutionError, execute
from poc.values import (
    AuditConfirmation,
    CustomerRequest,
    DeliveryConfirmation,
    HTTPRoute,
    ServiceOutcome,
    Variant,
)

RC = "ResponseChannel<user-session>"


# ── Fixture graphs ───────────────────────────────────────────────────
#
# A child with exactly one node is a child with exactly one terminal, which is the
# single-boundary-output shape the runtime supports.


def _service(graph_name: str, node_name: str) -> dict:
    return {
        "name": graph_name,
        "parameters": ["CustomerRequest", RC],
        "capabilities": [RC],
        "nodes": [
            {
                "name": node_name,
                "inputs": ["CustomerRequest", RC],
                "output": "DeliveryConfirmation",
            }
        ],
        "data_edges": [],
    }


def _parent(node_name: str, identity: str | None) -> dict:
    node: dict = {
        "name": node_name,
        "inputs": ["CustomerRequest", RC],
        "output": "DeliveryConfirmation",
    }
    if identity:
        node["capability_identities"] = {RC: identity}
    return {
        "name": "EchoPlatform",
        "parameters": ["CustomerRequest", RC],
        "capabilities": [RC],
        "nodes": [node],
        "data_edges": [],
    }


SPLIT_PARENT = {
    "name": "SplitPlatform",
    "parameters": ["CustomerRequest", RC],
    "capabilities": [RC],
    "nodes": [
        {
            "name": "Route",
            "inputs": ["CustomerRequest"],
            "output": "left: CustomerRequest | right: CustomerRequest",
        },
        {
            "name": "LeftService",
            "inputs": ["CustomerRequest", RC],
            "output": "DeliveryConfirmation",
            "capability_identities": {RC: "left_session"},
        },
        {
            "name": "RightService",
            "inputs": ["CustomerRequest", RC],
            "output": "DeliveryConfirmation",
            "capability_identities": {RC: "right_session"},
        },
    ],
    "data_edges": [
        {"from": "Route.left", "to": "LeftService"},
        {"from": "Route.right", "to": "RightService"},
    ],
}

# A graph containing a node of its own name: the degenerate self-reference.
LOOP = _service("Loop", "Loop")

INDEX = {
    "EchoService": _service("EchoService", "EchoReply"),
    "LeftService": _service("LeftService", "LeftEcho"),
    "RightService": _service("RightService", "RightEcho"),
    "Loop": LOOP,
}


@pytest.fixture(autouse=True)
def _impls(monkeypatch):
    """Host-tier bodies for the fixture leaf nodes."""

    def echo(label: str):
        def impl(req: CustomerRequest, channel: ResponseChannel) -> DeliveryConfirmation:
            return channel.send(f"{label}: {req.body}")

        return impl

    def route(req: CustomerRequest) -> Variant:
        return Variant(role="right" if req.body.startswith("right") else "left", value=req)

    for name, impl in [
        ("EchoReply", echo("echo")),
        ("LeftEcho", echo("left")),
        ("RightEcho", echo("right")),
        ("Route", route),
    ]:
        monkeypatch.setitem(REGISTRY, name, impl)


def _assemble(graph: dict, **kw):
    return assemble(copy.deepcopy(graph), backend=StubLLM(), stores={}, **kw)


REQUEST = CustomerRequest(session_id="user-session", body="why was I charged twice?")


# ── The mechanism ────────────────────────────────────────────────────


def test_a_parent_executes_through_a_sub_graph_node():
    """The boundary signal enters the sub-graph, it runs, and its output returns."""
    g = _assemble(_parent("EchoService", identity=None))
    result = execute(g, REQUEST, graphs=INDEX)

    assert result.order == ["EchoService"]
    assert isinstance(result.terminals["EchoService"], DeliveryConfirmation)
    # The nested run is visible at its own altitude.
    assert result.subgraphs["EchoService"].order == ["EchoReply"]
    assert result.subgraphs["EchoService"].received["EchoReply"] is REQUEST


def test_a_sub_graph_node_reports_no_enforcement_tier():
    """Its body is a graph, so no tier ran it; the nodes inside report their own."""
    g = _assemble(_parent("EchoService", identity=None))
    result = execute(g, REQUEST, graphs=INDEX)

    assert result.tiers["EchoService"] == TIER_GRAPH
    assert result.subgraphs["EchoService"].tiers["EchoReply"] == "host"


def test_the_sub_graphs_output_routes_on_the_parents_edges():
    """The child's boundary value becomes the parent node's output and flows on."""
    parent = _parent("EchoService", identity=None)
    parent["nodes"].append(
        {"name": "RecordIt", "inputs": ["DeliveryConfirmation"], "output": "AuditConfirmation"}
    )
    parent["data_edges"] = [{"from": "EchoService", "to": "RecordIt"}]

    seen: list[object] = []
    REGISTRY["RecordIt"] = lambda confirmation: seen.append(confirmation) or "audited"
    try:
        result = execute(_assemble(parent), REQUEST, graphs=INDEX)
    finally:
        del REGISTRY["RecordIt"]

    assert result.order == ["EchoService", "RecordIt"]
    assert isinstance(seen[0], DeliveryConfirmation)
    assert result.terminals == {"RecordIt": "audited"}


# ── Capability routing across the boundary ───────────────────────────


def test_a_routed_identity_is_the_instance_the_sub_graph_uses():
    """The point of the change: assembly-time identity routing now has an
    executable consequence. The parent declares a distinct `ResponseChannel`
    instance for the sub-graph node, and the node *inside* the sub-graph must send
    on that instance — not on the shared-by-type default."""
    g = _assemble(_parent("EchoService", identity="routed_session"))
    routed = g.handle_for(g.nodes["EchoService"], RC)
    shared = g.handles[RC]
    assert routed is not shared

    execute(g, REQUEST, graphs=INDEX)

    assert isinstance(routed, ResponseChannel)
    assert routed.sent == ["echo: why was I charged twice?"]
    assert isinstance(shared, ResponseChannel)
    assert shared.sent == [], "the sub-graph used the shared default, not the routed instance"


def test_a_sub_graph_cannot_provision_authority_of_its_own():
    """`execute` holds no backend, so a child can only exercise handles the parent
    routed to it. A sub-graph declaring a capability the parent does not supply
    fails loudly rather than quietly minting one."""
    child = _service("EchoService", "EchoReply")
    child["parameters"].append("EventEmitter<'support-queue'>")
    child["capabilities"].append("EventEmitter<'support-queue'>")

    g = _assemble(_parent("EchoService", identity=None))
    with pytest.raises(ExecutionError, match="arity"):
        execute(g, REQUEST, graphs={"EchoService": child})


# ── Sibling isolation ────────────────────────────────────────────────


def test_a_siblings_handles_are_untouched_by_another_sub_graphs_run():
    g = _assemble(SPLIT_PARENT)
    left = g.handle_for(g.nodes["LeftService"], RC)
    right = g.handle_for(g.nodes["RightService"], RC)
    assert left is not right

    result = execute(g, REQUEST, graphs=INDEX)

    assert result.order == ["Route", "LeftService"]
    assert "RightService" not in result.subgraphs
    assert isinstance(left, ResponseChannel) and left.sent == ["left: why was I charged twice?"]
    assert isinstance(right, ResponseChannel) and right.sent == []


def test_each_sibling_runs_on_its_own_routed_instance():
    """Same graph, the other branch: the isolation is symmetric, not an artefact of
    which branch happens to run first."""
    g = _assemble(SPLIT_PARENT)
    left = g.handle_for(g.nodes["LeftService"], RC)
    right = g.handle_for(g.nodes["RightService"], RC)

    execute(g, CustomerRequest(session_id="user-session", body="right, please"), graphs=INDEX)

    assert isinstance(right, ResponseChannel) and right.sent == ["right: right, please"]
    assert isinstance(left, ResponseChannel) and left.sent == []


# ── Guards ───────────────────────────────────────────────────────────


def test_a_self_referential_sub_graph_is_rejected():
    g = _assemble(LOOP)
    with pytest.raises(ExecutionError, match="references itself"):
        execute(g, REQUEST, graphs=INDEX)


def test_a_sub_graph_error_names_the_boundary_it_happened_behind():
    """A bare node name from two altitudes down is not comprehensible at the
    composition altitude, so the message names the sub-graph."""
    child = _service("EchoService", "MissingImpl")
    g = _assemble(_parent("EchoService", identity=None))
    with pytest.raises(ExecutionError, match=r"in sub-graph 'EchoService'.*MissingImpl"):
        execute(g, REQUEST, graphs={"EchoService": child})


def test_multi_terminal_aggregation_is_refused_not_guessed():
    """The scope boundary, pinned. A sub-graph that *reaches* more than one terminal
    has no single boundary output; the runtime must say so rather than pick one and
    let the parent's declared output type become fiction. This is the shape the
    shipped `CustomerSupport` graph has, which is why it is not run end-to-end here.

    The fan-out node emits a plain (non-variant) output, so the runtime follows every
    unported edge and both terminals are genuinely reached."""
    child = {
        "name": "EchoService",
        "parameters": ["CustomerRequest", RC],
        "capabilities": [RC],
        "nodes": [
            {"name": "Fan", "inputs": ["CustomerRequest"], "output": "CustomerRequest"},
            {
                "name": "EchoReply",
                "inputs": ["CustomerRequest", RC],
                "output": "DeliveryConfirmation",
            },
            {
                "name": "AlsoEcho",
                "inputs": ["CustomerRequest", RC],
                "output": "DeliveryConfirmation",
            },
        ],
        "data_edges": [
            {"from": "Fan", "to": "EchoReply"},
            {"from": "Fan", "to": "AlsoEcho"},
        ],
    }
    REGISTRY["Fan"] = lambda req: req
    REGISTRY["AlsoEcho"] = lambda _req, channel: channel.send("also")
    try:
        g = _assemble(_parent("EchoService", identity=None))
        with pytest.raises(ExecutionError, match="aggregation"):
            execute(g, REQUEST, graphs={"EchoService": child})
    finally:
        del REGISTRY["Fan"]
        del REGISTRY["AlsoEcho"]


# ── The shipped composition graph, end to end ────────────────────────

PLATFORM_STORES = {
    "knowledge-base": {"billing_question": ["Duplicate charges clear in 3-5 days."]},
    "billing": {},
    "audit": {},
}

CUSTOMER_TRAFFIC = HTTPRoute(
    path="/customer/message",
    session_id="user-session",
    body="Why was I charged twice on my latest invoice?",
)


@pytest.fixture
def platform():
    return assemble(load_graph_dict("support-platform"), backend=StubLLM(), stores=PLATFORM_STORES)


def test_support_platform_executes_a_customer_request_end_to_end(platform):
    """The headline: the composition graph does not merely assemble, it runs. A
    customer request enters at the platform boundary, is dispatched, crosses into
    the nine-node `CustomerSupport` graph, and its outcome crosses back out and
    lands in the audit log."""
    result = execute(platform, CUSTOMER_TRAFFIC)

    assert result.order == ["RouteRequest", "CustomerSupport", "RecordAudit"]
    assert result.tiers["CustomerSupport"] == TIER_GRAPH

    # The sub-graph really ran; this is the standalone pipeline, one level down.
    inner = result.subgraphs["CustomerSupport"]
    assert inner.order == [
        "ReceiveMessage",
        "ParseMessage",
        "ModerateContent",
        "FetchContext",
        "GenerateResponse",
        "SendReply",
    ]

    # The outcome crossed back out and was audited.
    audit = platform.handles["DBHandle<'audit', append>"]
    assert isinstance(audit, AppendDBHandle)
    assert audit.appended == ["delivered to user-session (ok=True)"]
    assert isinstance(result.terminals["RecordAudit"], AuditConfirmation)


def test_the_boundary_value_is_a_member_of_the_service_outcome_union(platform):
    """`ServiceOutcome` is the union alias of the sub-graph's terminal types, so the
    value crossing the boundary must be one of its members — here the
    `DeliveryConfirmation` from the reply path."""
    result = execute(platform, CUSTOMER_TRAFFIC)
    outcome = result.subgraphs["CustomerSupport"].terminals["SendReply"]

    assert isinstance(outcome, DeliveryConfirmation)
    assert isinstance(outcome, ServiceOutcome)


def test_the_platform_routes_its_declared_identity_into_the_sub_graph(platform):
    """On the shipped graph, not a fixture: `SupportPlatform` declares a distinct
    `customer_session` instance for `CustomerSupport` in the canonical JSON, and the
    reply node *inside* that sub-graph must send on that instance."""
    routed = platform.handle_for(platform.nodes["CustomerSupport"], RC)
    shared = platform.handles[RC]
    assert routed is not shared

    execute(platform, CUSTOMER_TRAFFIC)

    assert isinstance(routed, ResponseChannel) and len(routed.sent) == 1
    assert isinstance(shared, ResponseChannel) and shared.sent == []


def test_the_untaken_service_branches_need_no_implementations(platform):
    """A stated scope boundary, pinned rather than left implicit: `AgentDashboard`
    and `BillingService` are neither graphs in this repository nor registered
    implementations. The customer path does not reach them, and it does not need
    to in order to show a signal crossing a composition boundary."""
    assert "AgentDashboard" not in REGISTRY
    assert "BillingService" not in REGISTRY

    result = execute(platform, CUSTOMER_TRAFFIC)
    assert "AgentDashboard" not in result.order
    assert "BillingService" not in result.order

    # Routed at the platform's own boundary, they would fail loudly, not silently.
    with pytest.raises(ExecutionError, match="no host-tier implementation"):
        execute(platform, HTTPRoute(path="/agent/queue", session_id="s", body="hi"))


def test_the_output_side_of_composition_is_checked():
    """The gap, now closed. `CustomerSupport`'s terminals emit
    `DeliveryConfirmation | EscalationTicket`, and `SupportPlatform` declares exactly
    that union as the sub-graph node's boundary output. The cross-graph analysis now
    relates the two: the honest spelling validates, and a narrowed declaration —
    claiming only `DeliveryConfirmation`, hiding the escalation path — is rejected
    with a reason that names the output side, not an edge type mismatch."""
    child = load_graph_dict("customer-support")
    sources = {e["from"].split(".")[0] for e in child["data_edges"]}
    terminals = {n["output"] for n in child["nodes"] if n["name"] not in sources}
    assert terminals == {"DeliveryConfirmation", "EscalationTicket"}

    parent = load_graph_dict("support-platform")
    node = next(n for n in parent["nodes"] if n["name"] == "CustomerSupport")
    # The boundary output is spelled as the structural union, not a bare alias name
    # the language cannot resolve.
    assert node["output"] == "DeliveryConfirmation | EscalationTicket"

    # Honest spelling: the canonical pair validates.
    assert validate_graph_dicts([parent, child]) == []

    # Narrow the declaration (and its consumers, so every *edge* still type-checks):
    # the mistake is now invisible to the edge analysis and visible only to the
    # output-side check.
    narrowed = copy.deepcopy(parent)
    for n in narrowed["nodes"]:
        if n["name"] in ("CustomerSupport", "AgentDashboard", "BillingService"):
            n["output"] = "DeliveryConfirmation"
        if n["name"] == "RecordAudit":
            n["inputs"][0] = "DeliveryConfirmation"
    errors = validate_graph_dicts([narrowed, child])
    assert any("declared output" in e and "terminal output types" in e for e in errors)
    assert not any("type mismatch" in e for e in errors)
