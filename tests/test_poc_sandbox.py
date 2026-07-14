"""The hostile-node suite and the sandbox execution tier.

This suite is the deliverable of the WASI-sandbox change, not the sandbox itself.
Its spine is a set of *attacks*: a node body that actively tries to escape its
capability set. Each attack is asserted twice —

  * on the **host tier**, where it **succeeds** (host discipline cannot stop a
    node from `import os` / opening a socket / reading the environment), so the
    known gap is recorded as a test rather than as prose; and
  * on the **sandbox tier**, where it **fails**, because the WASM module runs
    under an empty WASI context with only its declared capability imports.

Covers the `signal-graph-runtime` spec requirements added/modified by
`add-wasi-node-sandbox`:
  - Nodes execute with no ambient authority
  - A hostile node cannot exceed its injected capabilities
  - Host and sandbox tiers compose within one graph
  - Capability-crossing overhead is measured
  - Prompt-injection attenuation, disclosed per tier

If the wasmtime toolchain or the built `.wasm` artifacts are absent, the whole
module skips with a clear reason rather than failing.
"""

from __future__ import annotations

import os
import socket
from pathlib import Path

import pytest

from poc.sandbox import SandboxError, available, wasm_path
from poc.sandbox.host import FS, Sandbox, cap_imports, wasi_imports

_ARTIFACTS = [
    "node_parse_message",
    "node_generate_response",
    "hostile_ambient",
    "hostile_ungranted",
]
_missing = [m for m in _ARTIFACTS if not wasm_path(m).exists()]

pytestmark = pytest.mark.skipif(
    not available() or bool(_missing),
    reason=(
        "sandbox tier unavailable: "
        + ("wasmtime not installed (`uv sync --group poc`)" if not available() else "")
        + (f" missing artifacts {_missing} (`make wasm`)" if _missing else "")
    ),
)


# ── The attacks, defined once ──────────────────────────────────────
#
# Each attack names a class of ambient authority. The host-tier lambda performs
# it in plain Python and returns True when it succeeds (it always does); the
# sandbox-tier column names the WASM export that attempts the same class of
# escape and reports a verdict.


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

SANDBOX_ESCAPES = {
    "filesystem": "escape_fs",
    "network": "escape_net",
    "environment": "escape_env",
}


def _sandbox_escaped(export: str) -> tuple[bool, str]:
    """Run a hostile-ambient export and return `(escaped, detail)`."""
    sb = Sandbox("hostile_ambient")  # no capability imports granted at all
    verdict, _, detail = sb.call_export(export).partition(FS)
    return verdict == "yes", detail


# ── The host tier's gap is asserted, not hidden ────────────────────


@pytest.mark.parametrize("attack", sorted(HOST_ATTACKS))
def test_host_tier_escape_succeeds(attack):
    """Scenario: the host tier's gap is asserted, not hidden. Host discipline
    does not confine a hostile node — every ambient-authority attack succeeds.
    This is the limitation the sandbox tier exists to close."""
    assert HOST_ATTACKS[attack]() is True


# ── The sandbox tier denies every escape ───────────────────────────


def test_sandbox_denies_filesystem_access():
    """Scenario: filesystem access is denied — no preopen was granted."""
    escaped, detail = _sandbox_escaped("escape_fs")
    assert not escaped, f"filesystem escape should fail, got: {detail}"


def test_sandbox_denies_network_egress():
    """Scenario: network egress is denied — no socket capability was granted."""
    escaped, detail = _sandbox_escaped("escape_net")
    assert not escaped, f"network escape should fail, got: {detail}"


def test_sandbox_denies_environment_access():
    """Scenario: ambient environment access is denied — empty WASI env."""
    escaped, detail = _sandbox_escaped("escape_env")
    assert not escaped, f"environment escape should fail, got: {detail}"


def test_every_ambient_attack_is_denied_in_the_sandbox():
    """The whole ambient-authority class is denied: the sandbox tier is the
    mirror image of the host tier's gap above."""
    for export in SANDBOX_ESCAPES.values():
        escaped, detail = _sandbox_escaped(export)
        assert not escaped, f"{export} should be denied, got: {detail}"


# ── A node cannot call a capability it was not granted ─────────────


def test_ungranted_capability_module_cannot_instantiate():
    """Scenario: a node cannot call a capability it was not granted. The hostile
    module imports `cap_kb_lookup`; provisioned as an inference-only node (which
    links only `cap_infer`), the import is unsatisfied and instantiation fails
    before a single instruction runs."""
    with pytest.raises(SandboxError, match="not granted"):
        Sandbox("hostile_ungranted", {"cap_infer": lambda a: "ok"})


def test_ungranted_capability_is_stronger_than_the_host_tier():
    """On the host tier an inference-only Python node could still `import` and
    fabricate a DB handle. On the sandbox tier the capability is absent from the
    import table — granting nothing lets the module instantiate at all."""
    with pytest.raises(SandboxError):
        Sandbox("hostile_ungranted", {})


# ── A sandboxed node's imports are exactly its declared capabilities ─


def test_parse_message_imports_only_inference():
    """Scenario: a sandboxed node's imports are exactly its declared capabilities.
    ParseMessage holds `LLMClient<inference>` — its module imports exactly
    `cap_infer` and no other capability function."""
    assert cap_imports("node_parse_message") == ["cap_infer"]


def test_generate_response_imports_only_its_two_capabilities():
    """GenerateResponse holds `LLMClient<[lookup]>` and a read-only DB handle —
    its module imports exactly the two backing host functions and nothing else
    (no exfiltrate, no write, no second tool)."""
    assert cap_imports("node_generate_response") == ["cap_generate", "cap_kb_lookup"]


def test_inference_only_node_has_no_tool_import_at_all():
    """Scenario: an inference-only node has no tool import at all. Stronger than
    the host tier's missing *method*: the tool-calling capability is absent from
    the module's import table entirely."""
    imports = cap_imports("node_parse_message")
    assert "cap_kb_lookup" not in imports
    assert not any("lookup" in name or "generate" in name for name in imports)


def test_no_capability_import_grants_ambient_authority():
    """No `cap` import is a filesystem, socket, environment, or clock handle. The
    WASI functions the module links (environ_get, fd_write, …) exist but are
    powerless under the empty context — proven by the escape tests above — and
    there are no ambient sockets in wasip1 at all."""
    for module in ("node_parse_message", "node_generate_response"):
        caps = cap_imports(module)
        assert all(c.startswith("cap_") for c in caps)
    # wasip1 provides no socket family: ambient network is absent even as an import.
    assert not any("sock" in w for w in wasi_imports("node_parse_message"))


# ── Host and sandbox tiers compose within one graph ────────────────

_SANDBOXED = {"ParseMessage", "GenerateResponse"}


def _run(message: str, sandbox=_SANDBOXED):
    from poc.demo import STORES
    from poc.graph import assemble, load_graph_dict
    from poc.llm import StubLLM
    from poc.runtime import execute
    from poc.values import CustomerRequest

    graph = assemble(
        load_graph_dict("customer-support"), backend=StubLLM(), stores=STORES, sandbox=sandbox
    )
    return execute(graph, CustomerRequest(session_id="user-session", body=message))


def test_mixed_tier_graph_runs_end_to_end_and_reports_tiers():
    """Scenario: a mixed-tier graph runs end-to-end. ParseMessage and
    GenerateResponse run confined; the rest run on the host tier; the vertical
    completes and the runtime reports which tier enforced each node."""
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


def test_sandbox_and_host_tiers_produce_the_same_outcome():
    """Code as compiled artifact: the Rust/WASM node bodies and the Python ones
    satisfy the same contracts, so the graph reaches the same terminal along the
    same path regardless of which tier runs the two ported nodes."""
    from poc.demo import BENIGN

    host = _run(BENIGN, sandbox=())
    mixed = _run(BENIGN, sandbox=_SANDBOXED)
    assert host.order == mixed.order
    assert all(t == "host" for t in host.tiers.values())


def test_sandboxed_parse_message_still_discharges_trust():
    """The confined ParseMessage consumes `Untrusted[RawMessage]` and emits a
    plain `CustomerQuery`; downstream nodes see non-`Untrusted` values, exactly
    as on the host tier."""
    from poc.demo import ADVERSARIAL
    from poc.values import CustomerQuery, Untrusted

    result = _run(ADVERSARIAL)
    assert isinstance(result.received["ParseMessage"], Untrusted)
    mod_in = result.received["ModerateContent"]
    assert isinstance(mod_in, CustomerQuery)
    assert not isinstance(mod_in, Untrusted)


# ── Prompt-injection attenuation holds on the sandbox tier ─────────


def test_sandboxed_tool_node_never_receives_raw_user_text():
    """Scenario: the tool-capable node never sees raw user text — holds on the
    sandbox tier too. GenerateResponse receives a `ConversationContext`, not the
    `Untrusted[RawMessage]`."""
    from poc.demo import ADVERSARIAL
    from poc.values import ConversationContext, RawMessage, Untrusted

    ctx = _run(ADVERSARIAL).received["GenerateResponse"]
    assert isinstance(ctx, ConversationContext)
    assert not isinstance(ctx, (Untrusted, RawMessage))


def test_sandboxed_adversarial_run_completes_without_tool_escape():
    """Scenario: adversarial instructions cannot trigger tools. Even confined,
    the run completes to a delivered reply — the tool-capable node could only
    ever call `lookup`, which is all its module imports."""
    from poc.demo import ADVERSARIAL
    from poc.values import DeliveryConfirmation

    result = _run(ADVERSARIAL)
    assert isinstance(result.terminals["SendReply"], DeliveryConfirmation)


def test_free_text_residual_survives_into_the_sandboxed_tool_node():
    """Scenario: the residual free-text exposure is still disclosed. The sandbox
    closes ambient-authority escapes; it does NOT close the bounded free-text
    field, which still reaches the tool-capable node as data. What bounds the
    damage is the capability scope, not the sandbox."""
    from poc.demo import ADVERSARIAL
    from poc.values import ConversationContext

    ctx = _run(ADVERSARIAL).received["GenerateResponse"]
    assert isinstance(ctx, ConversationContext)
    assert "ignore all previous instructions" in ctx.question.lower()


# ── Capability-crossing overhead is measured ───────────────────────


def test_overhead_is_measured_and_reported_against_the_envelope():
    """Scenario: overhead is reported against the proposal's envelope. The
    benchmark reports instantiation and per-crossing cost and states whether the
    crossing falls within the asserted envelope (per-crossing < ~1ms)."""
    from poc.sandbox.bench import ENVELOPE_CROSSING_MS, measure

    result = measure(repeats=50)
    assert result.instantiation_ms > 0
    assert result.compilation_ms > 0
    assert result.crossing_ms >= 0
    assert result.generate_crossings > result.parse_crossings
    # The measured crossing is expected to sit well within the envelope; assert
    # the comparison is computed rather than hard-coding a machine-specific bound.
    assert result.within_envelope == (result.crossing_ms < ENVELOPE_CROSSING_MS)
