"""The structured execution trace.

Covers the `signal-graph-runtime` spec requirement added by `add-execution-trace`:
the runtime emits a machine-readable trace recording, per node in execution order,
the enforcement tier, the input/output trust labels, and each capability crossing
(WIT interface + instance name); sub-graph runs nest; the format is schema-pinned
and structurally deterministic.

These tests run on the host tier, so they need no WASM toolchain. The claim that
the confined tier produces a *structurally identical* trace lives in
`tests/test_poc_sandbox.py`, which is where the sandbox tier is exercised.
"""

from __future__ import annotations

from poc.demo import ADVERSARIAL, BENIGN, STORES
from poc.graph import TIER_GRAPH, assemble, load_graph_dict
from poc.llm import StubLLM
from poc.runtime import execute

VERTICAL = [
    "ReceiveMessage",
    "ParseMessage",
    "ModerateContent",
    "FetchContext",
    "GenerateResponse",
    "SendReply",
]


def run(message: str, **kw):
    graph = assemble(load_graph_dict("customer-support"), backend=StubLLM(), stores=STORES)
    return execute(graph, _request(message), **kw)


def _request(body: str):
    from poc.values import CustomerRequest

    return CustomerRequest(session_id="user-session", body=body)


def _node(trace, name):
    return next(n for n in trace.nodes if n.node == name)


# ── Execution order and tier attribution ─────────────────────────────


def test_trace_lists_the_taken_path_in_execution_order():
    trace = run(BENIGN).trace
    assert [n.node for n in trace.nodes] == VERTICAL


def test_trace_names_the_tier_that_ran_each_node():
    trace = run(BENIGN).trace
    assert {n.node: n.tier for n in trace.nodes} == dict.fromkeys(VERTICAL, "host")


def test_trace_validates_against_the_committed_schema():
    from poc.trace import validate_document

    assert validate_document(run(ADVERSARIAL).trace.to_dict()) == []


# ── Trust labels and the discharge point ─────────────────────────────


def test_trust_is_raised_only_at_the_declared_discharge_node():
    """A node raises trust when it turns an untrusted input into a trusted output.
    In the customer-support graph exactly one node does — `ParseMessage`, the node
    the graph marks `discharges_trust`."""
    trace = run(ADVERSARIAL).trace
    raisers = [n.node for n in trace.walk() if n.raises_trust()]
    assert raisers == ["ParseMessage"]

    graph = load_graph_dict("customer-support")
    declared = [n["name"] for n in graph["nodes"] if n.get("discharges_trust")]
    assert raisers == declared


def test_the_entry_node_lowers_into_untrusted_it_does_not_raise():
    """`ReceiveMessage` produces the `Untrusted<_>` value; that is a trusted →
    untrusted step, the opposite of a discharge, and must not be counted as one."""
    receive = _node(run(BENIGN).trace, "ReceiveMessage")
    assert receive.input_trust == "trusted"
    assert receive.output_trust == "untrusted"
    assert not receive.raises_trust()


# ── Capability crossings, attributed to instances ────────────────────


def test_crossings_record_the_wit_interface_and_instance():
    trace = run(BENIGN).trace
    crossings = {
        n.node: sorted((c.interface, c.instance) for c in n.crossings) for n in trace.nodes
    }
    assert crossings["ParseMessage"] == [("aap:caps/inference-llm@0.1.0", "inference")]
    assert crossings["FetchContext"] == [("aap:caps/kb-read@0.1.0", "knowledge-base")]
    assert crossings["SendReply"] == [("aap:caps/response-channel@0.1.0", "user-session")]
    # The tool-capable node crosses two interfaces — the tool LLM and the KB read.
    assert crossings["GenerateResponse"] == [
        ("aap:caps/kb-read@0.1.0", "knowledge-base"),
        ("aap:caps/tool-llm@0.1.0", "lookup"),
    ]


def test_a_pure_node_records_no_crossings():
    assert _node(run(BENIGN).trace, "ReceiveMessage").crossings == []


def test_repeated_use_of_one_instance_is_a_single_structural_crossing():
    """`GenerateResponse` calls its KB read several times through the tool loop; the
    trace records one crossing of `kb-read`, because multiplicity is a timing fact,
    not a structural one — which is exactly what lets the two tiers agree."""
    gen = _node(run(BENIGN).trace, "GenerateResponse")
    kb = [c for c in gen.crossings if c.interface == "aap:caps/kb-read@0.1.0"]
    assert len(kb) == 1


# ── Determinism ──────────────────────────────────────────────────────


def test_trace_structure_is_deterministic_across_runs():
    assert run(ADVERSARIAL).trace.structural() == run(ADVERSARIAL).trace.structural()


def test_structural_form_excludes_timing():
    """Timing, when recorded, lives in an optional field that structural comparison
    drops — so a timed run and an untimed run are structurally identical, and the
    schema still accepts both."""
    from poc.trace import validate_document

    timed = run(BENIGN, record_timing=True).trace
    untimed = run(BENIGN).trace

    assert any(n.timing_us is not None for n in timed.nodes)
    assert timed.structural() == untimed.structural()
    assert validate_document(timed.to_dict()) == []


# ── Sub-graph nesting and identity routing across the boundary ───────

PLATFORM_STORES = {
    "knowledge-base": {"billing_question": ["Duplicate charges clear in 3-5 days."]},
    "billing": {},
    "audit": {},
}


def _platform_run():
    from poc.values import HTTPRoute

    graph = assemble(load_graph_dict("support-platform"), backend=StubLLM(), stores=PLATFORM_STORES)
    traffic = HTTPRoute(path="/customer/message", session_id="user-session", body=BENIGN)
    return execute(graph, traffic)


def test_a_sub_graph_run_nests_under_its_node():
    trace = _platform_run().trace
    assert [n.node for n in trace.nodes] == ["RouteRequest", "CustomerSupport", "RecordAudit"]

    cs = _node(trace, "CustomerSupport")
    assert cs.tier == TIER_GRAPH
    assert cs.crossings == [], "the sub-graph node itself crosses nothing; its children do"
    assert cs.subgraph is not None
    assert [n.node for n in cs.subgraph.nodes] == VERTICAL


def test_the_nested_trace_carries_its_own_tiers_and_crossings():
    cs = _node(_platform_run().trace, "CustomerSupport")
    assert cs.subgraph is not None
    inner_parse = next(n for n in cs.subgraph.nodes if n.node == "ParseMessage")
    assert inner_parse.tier == "host"
    assert inner_parse.crossings[0].interface == "aap:caps/inference-llm@0.1.0"


def test_a_routed_identity_is_visible_in_the_nested_crossing():
    """The point of instance-name attribution: the platform declares a distinct
    `customer_session` instance for `CustomerSupport`, and the reply node *inside*
    the sub-graph records its crossing against that declared identity — not the bare
    `user-session` scope it would carry standalone."""
    cs = _node(_platform_run().trace, "CustomerSupport")
    assert cs.subgraph is not None
    inner_send = next(n for n in cs.subgraph.nodes if n.node == "SendReply")
    assert [(c.interface, c.instance) for c in inner_send.crossings] == [
        ("aap:caps/response-channel@0.1.0", "customer_session")
    ]


def test_the_nested_trace_validates_against_the_schema():
    from poc.trace import validate_document

    assert validate_document(_platform_run().trace.to_dict()) == []


def test_a_host_only_capability_names_itself_when_it_has_no_wit_interface():
    """`RecordAudit` holds an append-mode `DBHandle`, which the confined tier does
    not model as a WIT interface. Its crossing still records — the interface field
    falls back to the capability type — rather than being silently dropped."""
    audit = _node(_platform_run().trace, "RecordAudit")
    assert [(c.interface, c.instance) for c in audit.crossings] == [
        ("DBHandle<'audit', append>", "audit")
    ]
