"""The hostile-node suite and the component execution tier.

This suite is the deliverable of the component-model change, not the tier itself.
Its spine is a set of *attacks*: a node body that actively tries to escape its
capability set. Each attack is asserted twice —

  * on the **host tier**, where it **succeeds** (host discipline cannot stop a
    node from `import os` / opening a socket / reading the environment), so the
    known gap is recorded as a test rather than as prose; and
  * on the **component tier**, where it **fails**, because the node runs as a WASM
    component whose import set contains exactly its declared capability interfaces
    and nothing else.

The previous (core-wasm) tier established that confinement result, and the rule
for this port was that it must not regress: every escape denied then must be
denied now. It is — and the *mechanism* is stronger, which the structural tests
below assert directly:

  * `test_no_component_imports_any_wasi_function` — the old tier's modules imported
    `fd_write`, `environ_get` and friends, rendered powerless by an empty
    `WasiConfig`. These components do not import them at all. "No ambient
    authority" became a property of the artifact rather than of the host's config.
  * `test_component_imports_match_the_graph_signature` — a component's import set
    is checked against the capability set derived from `graphs/customer-support.json`,
    so a world that over-grants fails here rather than shipping quietly.
  * `test_type_mismatched_value_is_rejected_at_the_boundary` — the typed boundary
    refuses a malformed value instead of reinterpreting bytes.

Covers the `signal-graph-runtime` spec requirements added/modified by
`add-wasm-component-model` and `add-wasi-node-sandbox`:
  - Capability boundaries are typed WIT interfaces
  - A component node imports no ambient WASI functions
  - Nodes execute with no ambient authority
  - A hostile node cannot exceed its injected capabilities
  - Host and component tiers compose within one graph
  - Capability-crossing overhead is measured
  - Prompt-injection attenuation, disclosed per tier

If wasmtime or the built artifacts are absent, the whole module skips with a clear
reason rather than failing.
"""

from __future__ import annotations

import os
import socket
from pathlib import Path

import pytest

from poc.graph import load_graph_dict
from poc.sandbox import (
    INFERENCE_LLM,
    KB_READ,
    RESPONSE_CHANNEL,
    TOOL_LLM,
    TYPES,
    Sandbox,
    SandboxError,
    SandboxTypeError,
    available,
    capability_imports,
    component_imports,
    expected_imports,
    record,
    wasi_imports,
    wasm_path,
)

_ARTIFACTS = [
    "node_parse_message",
    "node_moderate_content",
    "node_fetch_context",
    "node_generate_response",
    "node_send_reply",
    "hostile_ambient",
    "hostile_ungranted",
]
_missing = [m for m in _ARTIFACTS if not wasm_path(m).exists()]

pytestmark = pytest.mark.skipif(
    not available() or bool(_missing),
    reason=(
        "component tier unavailable: "
        + ("wasmtime not installed (`uv sync --group poc`)" if not available() else "")
        + (f" missing artifacts {_missing} (`make wasm`)" if _missing else "")
    ),
)


# ── The attacks, defined once ──────────────────────────────────────
#
# Each attack names a class of ambient authority. The host-tier function performs
# it in plain Python and returns True when it succeeds (it always does); the
# component-tier column names the WASM export that attempts the same class of
# escape and returns a typed verdict.


def _host_reads_a_file() -> bool:
    # A node granted no filesystem capability reads an arbitrary file anyway.
    return bool(Path(__file__).read_text())


def _host_opens_a_socket() -> bool:
    # A node granted no network capability constructs a socket anyway (ambient).
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.close()
    return True


def _host_reads_the_environment() -> bool:
    # A node granted no environment capability reads process env anyway.
    return os.environ.get("PATH") is not None


HOST_ATTACKS = {
    "filesystem": _host_reads_a_file,
    "network": _host_opens_a_socket,
    "environment": _host_reads_the_environment,
}

COMPONENT_ESCAPES = {
    "filesystem": "escape-fs",
    "network": "escape-net",
    "environment": "escape-env",
}


def _component_escaped(export: str) -> tuple[bool, str]:
    """Run a hostile-ambient export and return `(escaped, detail)`.

    The hostile component is granted nothing — and, its world importing nothing,
    there is nothing it could have been granted."""
    sb = Sandbox("hostile_ambient")
    verdict = sb.call(export)
    return verdict.escaped, verdict.detail


# ── The host tier's gap is asserted, not hidden ────────────────────


@pytest.mark.parametrize("attack", sorted(HOST_ATTACKS))
def test_host_tier_escape_succeeds(attack):
    """Scenario: the host tier's gap is asserted, not hidden. Host discipline does
    not confine a hostile node — every ambient-authority attack succeeds. This is
    the limitation the confined tier exists to close."""
    assert HOST_ATTACKS[attack]() is True


# ── The component tier denies every escape ─────────────────────────


def test_component_denies_filesystem_access():
    """Scenario: filesystem access is denied — there is no filesystem import."""
    escaped, detail = _component_escaped("escape-fs")
    assert not escaped, f"filesystem escape should fail, got: {detail}"


def test_component_denies_network_egress():
    """Scenario: network egress is denied — there is no socket import."""
    escaped, detail = _component_escaped("escape-net")
    assert not escaped, f"network escape should fail, got: {detail}"


def test_component_denies_environment_access():
    """Scenario: ambient environment access is denied — there is no env import."""
    escaped, detail = _component_escaped("escape-env")
    assert not escaped, f"environment escape should fail, got: {detail}"


def test_every_ambient_attack_is_denied_on_the_component_tier():
    """The whole ambient-authority class is denied: the component tier is the mirror
    image of the host tier's gap above. This is the confinement result the core-wasm
    tier established, carried over intact by the port — the requirement that the
    change must strengthen the mechanism without weakening the outcome."""
    for export in COMPONENT_ESCAPES.values():
        escaped, detail = _component_escaped(export)
        assert not escaped, f"{export} should be denied, got: {detail}"


# ── No ambient WASI imports at all ─────────────────────────────────


@pytest.mark.parametrize("component", _ARTIFACTS)
def test_no_component_imports_any_wasi_function(component):
    """Scenario: the component's import set contains no WASI functions.

    The strengthened form of "no ambient authority", and the headline result of the
    port. A `wasm32-wasip1` module — what the retired tier shipped — imports WASI
    stubs (`environ_get`, `fd_write`, `path_open`, …) through the standard library.
    They were powerless there, because the host handed them an empty `WasiConfig`;
    but they were *present*, and confinement was therefore a fact about the host's
    configuration rather than about the artifact.

    These components are built for `wasm32-unknown-unknown` and converted with no
    WASI adapter. No filesystem, socket, environment or clock function appears among
    their imports at all."""
    assert wasi_imports(component) == []


def test_the_hostile_component_imports_nothing_whatsoever():
    """The hostile-ambient node's world declares no capabilities, so its import set
    holds nothing but the shared type vocabulary — which declares records and enums
    and no functions, and so grants no authority. There is literally nothing for it
    to call."""
    assert capability_imports("hostile_ambient") == []
    assert component_imports("hostile_ambient") == [TYPES]


# ── A component's imports are exactly its declared capabilities ─────


def test_parse_message_imports_only_the_inference_interface():
    """Scenario: a confined node's imports are exactly its declared capabilities.
    ParseMessage holds `LLMClient<inference>` — its component imports exactly the
    typed inference interface and no other capability interface."""
    assert capability_imports("node_parse_message") == [INFERENCE_LLM]


def test_generate_response_imports_only_its_two_interfaces():
    """GenerateResponse holds `LLMClient<[lookup]>` and a read-only DB handle — its
    component imports exactly the two backing interfaces and nothing else (no
    exfiltrate, no write interface, no second tool)."""
    assert capability_imports("node_generate_response") == sorted([TOOL_LLM, KB_READ])


def test_fetch_context_imports_only_the_read_db_interface():
    """Scenario: the regenerated capability-holding node is confined to its declared
    handles. `FetchContext` holds `DBHandle<'knowledge-base', read>` — its Rust
    component imports exactly the `kb-read` interface and no other capability, so a
    node regenerated in a second language exercises the typed DB boundary and is held
    to it, not merely to a pure transformation."""
    imports = capability_imports("node_fetch_context")
    assert imports == [KB_READ]
    # No writer, no LLM, no channel — the read handle is the whole of its authority.
    assert TOOL_LLM not in imports
    assert INFERENCE_LLM not in imports
    assert RESPONSE_CHANNEL not in imports


def test_send_reply_imports_only_the_response_channel_interface():
    """`SendReply` holds `ResponseChannel<user-session>` — its component imports
    exactly the write-only `response-channel` interface and nothing else. There is no
    read interface in its world, so a node that can reply cannot read the channel."""
    assert capability_imports("node_send_reply") == [RESPONSE_CHANNEL]


def test_moderate_content_imports_only_the_inference_interface():
    """`ModerateContent` holds `LLMClient<inference>` — inference only, exactly like
    ParseMessage: its component imports the inference interface and no tool interface,
    so it can be influenced by the query it classifies but cannot act on it."""
    imports = capability_imports("node_moderate_content")
    assert imports == [INFERENCE_LLM]
    assert TOOL_LLM not in imports


def test_inference_only_node_has_no_tool_interface_at_all():
    """Scenario: an inference-only node has no tool import at all. Stronger than the
    host tier's missing *method*: the tool-calling capability is absent from the
    component's world entirely, and `inference-llm` has no case in which it could
    return a tool request even if a tool existed to run."""
    imports = capability_imports("node_parse_message")
    assert TOOL_LLM not in imports
    assert KB_READ not in imports


@pytest.mark.parametrize(
    ("component", "node"),
    [
        ("node_parse_message", "ParseMessage"),
        ("node_moderate_content", "ModerateContent"),
        ("node_fetch_context", "FetchContext"),
        ("node_generate_response", "GenerateResponse"),
        ("node_send_reply", "SendReply"),
    ],
)
def test_component_imports_match_the_graph_signature(component, node):
    """Scenario: the boundary cannot drift from the node signature.

    The expected import set is *derived from the graph JSON* — the node's `with`
    clause, parsed with the project's own type parser and mapped onto WIT interfaces
    (`poc/sandbox/interfaces.py`) — and compared against what the built component
    actually imports. A world that grants an interface the graph never asked for
    fails here, rather than shipping as a silent over-grant."""
    graph = load_graph_dict("customer-support")
    assert component_imports(component) == expected_imports(graph, node)


# ── A node cannot call a capability it was not granted ─────────────


def test_ungranted_capability_component_cannot_instantiate():
    """Scenario: a node cannot call a capability it was not granted. The hostile
    component's world imports `kb-read`; provisioned as an inference-only node
    (which links only the inference interface), the import is unsatisfied and
    instantiation fails before a single instruction runs."""
    with pytest.raises(SandboxError, match="not granted"):
        Sandbox("hostile_ungranted", {INFERENCE_LLM: {"infer": lambda _s, _p, _t: "unknown"}})


def test_the_denial_names_the_interface_it_refused():
    """The typed boundary improves even the failure. The core-wasm host could only
    report an unsatisfied *symbol* (`cap_kb_lookup`); here the refusal names the
    capability interface the component asked for and did not get."""
    with pytest.raises(SandboxError) as exc:
        Sandbox("hostile_ungranted", {INFERENCE_LLM: {"infer": lambda _s, _p, _t: "unknown"}})
    assert KB_READ in str(exc.value)


def test_ungranted_capability_is_stronger_than_the_host_tier():
    """On the host tier an inference-only Python node could still `import` and
    fabricate a DB handle. Here the capability is absent from the component's world
    — and granting it nothing does not let it instantiate either."""
    with pytest.raises(SandboxError):
        Sandbox("hostile_ungranted", {})


# ── The boundary is typed ──────────────────────────────────────────


def test_type_mismatched_value_is_rejected_at_the_boundary():
    """Scenario: a value that does not match an interface's WIT type is a boundary
    error, not a marshalling accident.

    This is what the flat ABI could not offer. There, every value was bytes in
    linear memory: a malformed one was reinterpreted as *something* and surfaced
    later as a nonsense field, or not at all. Here `run` takes a `raw-message`, and a
    value of the wrong shape never reaches the guest."""
    sb = Sandbox("node_parse_message", {INFERENCE_LLM: {"infer": lambda _s, _p, _t: "unknown"}})
    with pytest.raises(SandboxTypeError):
        sb.call("run", record(wrong_field="not a raw-message"))


def test_the_intent_enum_is_closed_at_the_boundary():
    """The graph says ParseMessage's intent comes from a closed set, and on this tier
    the *type* says so: `intent` is a WIT enum. However adversarial the text, and
    whatever label the model returns, the value crossing back cannot be outside the
    five cases — there is no such value to construct. The core-wasm node body needed
    a membership check to promise this; here the promise is structural."""
    from poc.values import Intent

    wit_cases = {i.value.replace("_", "-") for i in Intent}
    for label in ("billing_question", "TOTALLY_MADE_UP", "'; DROP TABLE --", ""):
        infer = lambda _s, _p, _t, reply=label: reply  # noqa: E731 — bind per iteration
        sb = Sandbox("node_parse_message", {INFERENCE_LLM: {"infer": infer}})
        out = sb.call("run", record(text="hello"))
        assert out.intent in wit_cases, f"model label {label!r} widened the intent set"


# ── Host and component tiers compose within one graph ──────────────

_SANDBOXED = {"ParseMessage", "GenerateResponse"}


def _run(message: str, sandbox=_SANDBOXED):
    from poc.demo import STORES
    from poc.graph import assemble
    from poc.llm import StubLLM
    from poc.runtime import execute
    from poc.values import CustomerRequest

    graph = assemble(
        load_graph_dict("customer-support"), backend=StubLLM(), stores=STORES, sandbox=sandbox
    )
    return execute(graph, CustomerRequest(session_id="user-session", body=message))


def test_mixed_tier_graph_runs_end_to_end_and_reports_tiers():
    """Scenario: a mixed-tier graph runs end-to-end. ParseMessage and GenerateResponse
    run as confined components; the rest run on the host tier; the vertical completes
    and the runtime reports which tier enforced each node. The migration story — port
    the security-critical nodes first, leave the rest — survives the port."""
    from poc.demo import BENIGN
    from poc.values import DeliveryConfirmation

    result = _run(BENIGN)

    confirmation = result.terminals["SendReply"]
    assert isinstance(confirmation, DeliveryConfirmation)
    assert confirmation.delivered

    assert result.tiers["ParseMessage"] == "sandbox"
    assert result.tiers["GenerateResponse"] == "sandbox"
    assert result.tiers["ModerateContent"] == "host"
    assert result.tiers["ReceiveMessage"] == "host"


def test_component_and_host_tiers_produce_the_same_outcome():
    """Code as compiled artifact: the Rust/WASM node bodies and the Python ones satisfy
    the same contracts, so the graph reaches the same terminal along the same path
    regardless of which tier runs the two ported nodes."""
    from poc.demo import BENIGN

    host = _run(BENIGN, sandbox=())
    mixed = _run(BENIGN, sandbox=_SANDBOXED)
    assert host.order == mixed.order
    assert all(t == "host" for t in host.tiers.values())


# The most-confined configuration: every node with a component port runs confined,
# leaving only the pure `ReceiveMessage` narrowing on the host tier.
_MOST_CONFINED = {
    "ParseMessage",
    "ModerateContent",
    "FetchContext",
    "GenerateResponse",
    "SendReply",
}


def test_majority_of_the_customer_path_runs_confined():
    """Scenario: majority-confined execution succeeds. In its most-confined
    configuration the customer path runs five of its six nodes as WASM components, the
    run completes with the same outcome as the host-tier run, and the per-node tier
    report names each node's tier. The claim 'a node cannot exceed its declared
    capabilities' now holds for most of the demonstrated graph, not for two nodes."""
    from poc.demo import BENIGN
    from poc.values import DeliveryConfirmation

    confined = _run(BENIGN, sandbox=_MOST_CONFINED)
    host = _run(BENIGN, sandbox=())

    # Same terminal, same path, regardless of tier — the contracts are what match.
    assert confined.order == host.order
    assert isinstance(confined.terminals["SendReply"], DeliveryConfirmation)
    assert confined.terminals["SendReply"] == host.terminals["SendReply"]

    # Every node's tier is reported, and a strict majority of the taken path is confined.
    assert set(confined.tiers) == set(confined.order)
    sandboxed = [n for n in confined.order if confined.tiers[n] == "sandbox"]
    assert set(sandboxed) == _MOST_CONFINED
    assert 2 * len(sandboxed) > len(confined.order)  # 5 of 6
    # Only the pure narrowing node stays host-side.
    assert confined.tiers["ReceiveMessage"] == "host"


def test_confined_identity_routing_lands_on_the_reply_channel():
    """The confined `SendReply` reports the session it delivered to — the channel's
    identity, which the guest never held as data, crosses back on the confirmation.
    So identity routing is observable across the WIT boundary, not only at assembly."""
    from poc.demo import BENIGN

    result = _run(BENIGN, sandbox=_MOST_CONFINED)
    confirmation = result.terminals["SendReply"]
    assert confirmation.session_id == "user-session"
    assert confirmation.delivered


# ── Composition across enforcement tiers ───────────────────────────
#
# `add-subgraph-execution` composed a host-tier parent with a host-tier child, and
# left cross-tier composition explicitly "not attempted". It works, and needs no new
# mechanism: the sub-graph executor stays backend-free, and the child's nodes resolve
# to their own tiers exactly as in a top-level run. A host-tier `SupportPlatform`
# therefore runs `CustomerSupport` with confined nodes inside it, and confinement
# across the boundary falls out of the same plumbing.

_PLATFORM_STORES = {
    "knowledge-base": {"billing_question": ["Duplicate charges clear in 3-5 days."]},
    "billing": {},
    "audit": {},
}
_RC = "ResponseChannel<user-session>"


def _customer_traffic():
    from poc.values import HTTPRoute

    return HTTPRoute(
        path="/customer/message",
        session_id="user-session",
        body="Why was I charged twice on my latest invoice?",
    )


def _assemble_platform(**kw):
    from poc.graph import assemble
    from poc.llm import StubLLM

    return assemble(
        load_graph_dict("support-platform"), backend=StubLLM(), stores=_PLATFORM_STORES, **kw
    )


def test_host_parent_runs_a_child_with_confined_nodes():
    """Scenario: a host-tier parent runs a child whose nodes run confined. The platform
    itself runs on the host tier (its own nodes were never ported); its `CustomerSupport`
    sub-graph node resolves to a graph (tier `graph`); and inside that child, five nodes
    run as WASM components while the pure narrowing stays host-side. The composition
    completes end to end, and every node's tier is reported at its own altitude."""
    from poc.runtime import execute
    from poc.values import AuditConfirmation

    platform = _assemble_platform()
    result = execute(platform, _customer_traffic(), sandbox={"CustomerSupport": _MOST_CONFINED})

    # The parent's own nodes on the host tier; the sub-graph node reports `graph`.
    assert result.tiers["RouteRequest"] == "host"
    assert result.tiers["CustomerSupport"] == "graph"
    assert result.tiers["RecordAudit"] == "host"

    # The child's nodes resolve to their own tiers, reported in the nested result.
    child = result.subgraphs["CustomerSupport"]
    assert {n for n in child.order if child.tiers[n] == "sandbox"} == _MOST_CONFINED
    assert child.tiers["ReceiveMessage"] == "host"

    # And it runs all the way to the platform's audit terminal.
    assert isinstance(result.terminals["RecordAudit"], AuditConfirmation)


def test_capability_instance_routes_into_the_confined_child():
    """Identity routing survives both the composition boundary and the WIT boundary:
    the platform declares a distinct `customer_session` instance for `CustomerSupport`,
    and the *confined* reply node inside it sends on that instance, not the shared
    default."""
    from poc.handles import ResponseChannel
    from poc.runtime import execute

    platform = _assemble_platform()
    routed = platform.handle_for(platform.nodes["CustomerSupport"], _RC)
    shared = platform.handles[_RC]
    assert routed is not shared

    execute(platform, _customer_traffic(), sandbox={"CustomerSupport": _MOST_CONFINED})

    assert isinstance(routed, ResponseChannel) and len(routed.sent) == 1
    assert isinstance(shared, ResponseChannel) and shared.sent == []


def test_confinement_holds_across_the_composed_boundary():
    """Scenario: confinement holds across the composed boundary. A confined child node
    reaches its capability only through the host closure over the handle the parent
    routed — the child's executor holds no backend to provision one of its own. So when
    the parent withdraws that authority, the confined `SendReply` crossing *inside the
    child* fails, two altitudes down: confinement, and its revocation, cross the composed
    boundary because nothing on the child side can re-mint the severed capability."""
    from poc.handles import RevokedCapabilityError
    from poc.runtime import execute

    platform = _assemble_platform(revocable_instances=[(_RC, "customer_session")])
    traffic = _customer_traffic()

    # Before revocation the confined child completes.
    before = execute(platform, traffic, sandbox={"CustomerSupport": _MOST_CONFINED})
    assert before.subgraphs["CustomerSupport"].tiers["SendReply"] == "sandbox"

    # Sever the routed instance; the confined crossing inside the child now fails.
    platform.revoke(_RC, "customer_session")
    with pytest.raises(RevokedCapabilityError):
        execute(platform, traffic, sandbox={"CustomerSupport": _MOST_CONFINED})


def test_confined_parse_message_still_discharges_trust():
    """The confined ParseMessage consumes `Untrusted[RawMessage]` and emits a plain
    `CustomerQuery`; downstream nodes see non-`Untrusted` values, exactly as on the
    host tier."""
    from poc.demo import ADVERSARIAL
    from poc.values import CustomerQuery, Untrusted

    result = _run(ADVERSARIAL)
    assert isinstance(result.received["ParseMessage"], Untrusted)
    mod_in = result.received["ModerateContent"]
    assert isinstance(mod_in, CustomerQuery)
    assert not isinstance(mod_in, Untrusted)


# ── Prompt-injection attenuation holds on the component tier ────────


def test_confined_tool_node_never_receives_raw_user_text():
    """Scenario: the tool-capable node never sees raw user text — holds on the
    component tier too. GenerateResponse receives a `ConversationContext`, not the
    `Untrusted[RawMessage]`."""
    from poc.demo import ADVERSARIAL
    from poc.values import ConversationContext, RawMessage, Untrusted

    ctx = _run(ADVERSARIAL).received["GenerateResponse"]
    assert isinstance(ctx, ConversationContext)
    assert not isinstance(ctx, (Untrusted, RawMessage))


def test_confined_adversarial_run_completes_without_tool_escape():
    """Scenario: adversarial instructions cannot trigger tools. Even confined, the run
    completes to a delivered reply — the tool-capable node could only ever call
    `lookup`, which is the only tool interface in its world."""
    from poc.demo import ADVERSARIAL
    from poc.values import DeliveryConfirmation

    result = _run(ADVERSARIAL)
    assert isinstance(result.terminals["SendReply"], DeliveryConfirmation)


def test_free_text_residual_survives_into_the_confined_tool_node():
    """Scenario: the residual free-text exposure is still disclosed. Typing the
    boundary closes marshalling ambiguity and closes ambient authority; it does NOT
    close the bounded free-text field, which still reaches the tool-capable node as
    data. What bounds the damage is the capability scope, not the type of the
    boundary. Recording this keeps the port honest about what it did not buy."""
    from poc.demo import ADVERSARIAL
    from poc.values import ConversationContext

    ctx = _run(ADVERSARIAL).received["GenerateResponse"]
    assert isinstance(ctx, ConversationContext)
    assert "ignore all previous instructions" in ctx.question.lower()


# ── Revocation composes to the confined tier ───────────────────────
#
# `add-capability-revocation` enforced revocation on the host tier and left open
# whether severing *composes* to the confined tier. It does, structurally and for
# free: a sandboxed node reaches its capabilities through WIT host functions that
# the host satisfies with closures over the node's handle, and for a revocable
# instance that handle is a Caretaker. The guest's only path to the resource is
# that import, so once the caretaker is severed the crossing raises — the failure
# is at the WIT boundary, not the memory level (CHERI remains the follow-up).

INFERENCE_CAP = "LLMClient<inference>"


def _assemble_confined_revocable(node="ParseMessage", identity="parse_llm"):
    """Assemble the graph with `node` on the confined tier and its inference LLM
    provisioned as a revocable instance, so the host can sever it between runs."""
    from poc.demo import STORES
    from poc.graph import assemble
    from poc.llm import StubLLM

    return assemble(
        load_graph_dict("customer-support"),
        backend=StubLLM(),
        stores=STORES,
        sandbox={node},
        identities={node: {INFERENCE_CAP: identity}},
        revocable_instances=[(INFERENCE_CAP, identity)],
    )


def test_a_confined_node_cannot_exercise_a_revoked_instance():
    """Scenario: a sandboxed node cannot exercise a revoked instance. ParseMessage
    runs as a confined component whose sole capability import is the inference LLM;
    before revocation its `infer` crossing succeeds, and after the host severs the
    instance the same crossing raises `RevokedCapabilityError` — revocation reaches
    across the WIT boundary, so the confined tier does not outlive a withdrawal."""
    from poc.handles import RevokedCapabilityError
    from poc.runtime import execute
    from poc.values import CustomerRequest

    g = _assemble_confined_revocable()
    msg = CustomerRequest(session_id="user-session", body="Why was I charged twice?")

    before = execute(g, msg)
    assert before.tiers["ParseMessage"] == "sandbox"
    # ParseMessage produced output, so the confined `infer` crossing ran and returned.
    assert "ModerateContent" in before.order

    g.revoke(INFERENCE_CAP, "parse_llm")
    with pytest.raises(RevokedCapabilityError, match="revoked"):
        execute(g, msg)


def test_revocation_on_the_confined_tier_is_targeted():
    """Severing the confined node's instance does not disturb a same-typed sibling
    on the shared-by-type default: ModerateContent also holds `LLMClient<inference>`
    but on the type-default handle, and remains usable after the revocation."""
    from poc.handles import Caretaker

    g = _assemble_confined_revocable()
    g.revoke(INFERENCE_CAP, "parse_llm")

    sibling = g.handle_for(g.nodes["ModerateContent"], INFERENCE_CAP)
    assert not isinstance(sibling, Caretaker)  # untouched type-default, not the severed instance
    assert sibling.infer(system="s", prompt="p", task="moderate")  # still exercises authority


# ── Capability-crossing overhead is measured ───────────────────────


def test_overhead_is_measured_and_reported_against_the_envelope():
    """Scenario: overhead is reported against the proposal's envelope. The benchmark
    reports instantiation and per-crossing cost and states whether the crossing falls
    within the asserted envelope (per-crossing < ~1ms) — now across a typed boundary
    that lifts and lowers WIT values, where the retired tier passed raw bytes."""
    from poc.sandbox.bench import ENVELOPE_CROSSING_MS, measure

    result = measure(repeats=50)
    assert result.instantiation_ms > 0
    assert result.compilation_ms > 0
    assert result.crossing_ms >= 0
    assert result.generate_crossings > result.parse_crossings
    # The measured crossing is expected to sit well within the envelope; assert the
    # comparison is computed rather than hard-coding a machine-specific bound.
    assert result.within_envelope == (result.crossing_ms < ENVELOPE_CROSSING_MS)
