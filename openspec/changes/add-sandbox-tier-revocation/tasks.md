## 1. Verify composition
- [ ] 1.1 Determine which object the sandbox WIT host-function closures in `poc/sandbox/nodes.py` bridge
      to — the caretaker resolved via `handle_for`/`handles_for`, or a handle captured before wrapping
- [ ] 1.2 `/verify`: assemble a graph with a sandboxed node binding a revocable instance, revoke it, and
      drive a crossing through the confined tier; observe whether it raises `RevokedCapabilityError`

## 2. Enforce (only if composition does not already hold)
- [ ] 2.1 If the closure captured a pre-wrap handle, route it through the caretaker so revocation composes
- [ ] 2.2 If routing is insufficient, sever at the host-function boundary: refuse to service a guest call
      for a revoked instance, gated on the same revoked flag so un-revoked crossings are unchanged

## 3. Tests
- [ ] 3.1 Add a revoked-instance escape to the hostile-node suite (`tests/test_poc_sandbox.py`): a
      sandboxed node's use of a revoked instance must fail on the confined tier
- [ ] 3.2 Assert the pre-revocation crossing succeeds, so the test proves severing, not a broken wire
- [ ] 3.3 Keep the existing hostile-node escapes (filesystem, network, env, ungranted capability) passing

## 4. Wrap-up
- [ ] 4.1 Fold into the proposal: Technical Note A "Capability revocation and rotation" — enforcement note
      moves from "host tier" to "host tier, and unforgeable at the WASM boundary for ported nodes"
- [ ] 4.2 Note what remains open: rotation on the sandbox tier, ambient-authority revocation (none exists),
      and memory-level (CHERI)
- [ ] 4.3 Full gate green: ruff, pytest (with `--group poc`), `make build`; `make wasm` only if artifacts
      change

## Notes for whoever picks this up
- The likely outcome is that composition already holds because the sandbox bridge reuses the same handle
  objects — in which case this change is mostly a recorded test. Verify first; add a sever point only if
  needed.
- Do not over-claim: the failure is at the WIT boundary, not the memory level. Keep CHERI as the follow-up.
- Do not weaken the free-text residual note: adversarial data in a *permitted* field still reaches a
  tool-capable node; revocation withdraws the handle's authority, it does not filter content.
