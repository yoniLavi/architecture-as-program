# Change: Enforce capability revocation on the confined (sandbox) tier

## Why
Revocation is enforced on the host tier only, where a caretaker is host-discipline — a hostile Python node
can reach around it. The sandbox tier is where confinement becomes *unforgeable* at the WASM boundary. The
revocation design left one question explicitly open (a `/verify` question): a sandboxed node reaches its
capabilities through typed WIT host functions that bridge to the *same* backing handle objects the host
tier uses (`poc/sandbox/nodes.py`), so severing a caretaker *may* already compose to the confined tier for
free — but that must be verified and locked in with a test, and if it does not hold, severed at the
host-function boundary. Otherwise "revocation" silently means "host-tier revocation" while the confined
tier — the one whose confinement we actually trust — could still exercise withdrawn authority.

## What Changes
- Verify that revoking a capability instance also severs it for a **sandboxed** node that binds it: the
  guest→host capability crossing calls the revoked caretaker, which raises, so the node's use fails on the
  confined tier as it does on the host tier.
- Add a **hostile-node test** asserting a sandboxed node cannot exercise a revoked instance — mirroring the
  existing host-tier revocation test and the sandbox hostile-node suite, so the confined-tier result is a
  recorded fact, not an assumption.
- If composition does **not** hold automatically, sever at the host-function boundary: the per-instance
  host function refuses to service a guest call for a revoked instance.
- Not in scope: rotation on the sandbox tier (its own change); revocation of ambient authority (there is
  none by construction — `wasi_imports()` is empty); memory-level enforcement (CHERI remains the named
  follow-up); revoking mid-crossing (crossings are synchronous).

## Impact
- Affected specs: `signal-graph-runtime` (ADDED: revocation composes to the confined tier).
- Affected code: `poc/sandbox/nodes.py` and/or `poc/sandbox/host.py` (ensure the caretaker is what the WIT
  host functions bridge to; sever at the boundary only if needed), `tests/test_poc_sandbox.py` (a
  revoked-instance escape that must fail on the confined tier).
- Proposal feedback: Technical Note A "Capability revocation and rotation" — upgrade the enforcement note
  from "host tier" to "host tier, and unforgeable at the WASM boundary for ported nodes", keeping rotation
  and the redeployment form open.
- Builds on: archived `add-capability-revocation` (the mechanism) and the WASM component tier
  (`add-wasm-component-model`).

## Dependencies
Independent of `add-capability-rotation`; both build on `add-capability-revocation`. If rotation lands
first, a follow-up can extend this to sandbox-tier rotation by the same argument.
