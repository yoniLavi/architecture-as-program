## 1. Verify composition
- [x] 1.1 Determine which object the sandbox WIT host-function closures in `poc/sandbox/nodes.py` bridge
      to — the caretaker resolved via `handle_for`/`handles_for`, or a handle captured before wrapping
      — the adapters receive handles as `*capability_handles` arguments, which the executor resolves
      through `handle_for` (`poc/runtime.py:44`); for a managed instance that IS the caretaker
- [x] 1.2 `/verify`: assemble a graph with a sandboxed node binding a revocable instance, revoke it, and
      drive a crossing through the confined tier; observe whether it raises `RevokedCapabilityError`
      — PASS. ParseMessage on the sandbox tier: its `infer` crossing succeeds before revocation and
      raises `RevokedCapabilityError` after. The exception propagates cleanly (it subclasses
      `RuntimeError`, so `Sandbox.call`'s `SandboxTypeError` catch does not swallow it)

## 2. Enforce (only if composition does not already hold)
- [x] 2.1 If the closure captured a pre-wrap handle, route it through the caretaker so revocation composes
      — not needed: composition already holds because the adapter closes over the `handle_for`-resolved
      caretaker, and the caretaker interposes on *attribute access* so `llm.infer` / `llm.backend` /
      `db.read` all hit the revoked check
- [x] 2.2 If routing is insufficient, sever at the host-function boundary: refuse to service a guest call
      for a revoked instance — not needed; no second sever point added (avoids a redundant path)

## 3. Tests
- [x] 3.1 Add a revoked-instance escape to the hostile-node suite (`tests/test_poc_sandbox.py`): a
      sandboxed node's use of a revoked instance must fail on the confined tier
      (`test_a_confined_node_cannot_exercise_a_revoked_instance`)
- [x] 3.2 Assert the pre-revocation crossing succeeds, so the test proves severing, not a broken wire
- [x] 3.3 Keep the existing hostile-node escapes (filesystem, network, env, ungranted capability) passing
      — plus `test_revocation_on_the_confined_tier_is_targeted` (a same-typed host-tier sibling still works)

## 4. Wrap-up
- [x] 4.1 Fold into the proposal: Technical Note A "Capability revocation and rotation" — enforcement note
      moves from "host tier" to revocation reaching the confined tier, unforgeable at the WIT boundary
- [x] 4.2 Note what remains open: rotation on the sandbox tier, ambient-authority revocation (none exists),
      and memory-level (CHERI) — all stated in the proposal paragraph
- [x] 4.3 Full gate green: ruff, pytest (150 passed + 21 subtests with `--group poc`), `make build`; no
      `make wasm` needed (no artifacts changed — composition was structural)

## Notes for whoever picks this up
- The likely outcome is that composition already holds because the sandbox bridge reuses the same handle
  objects — in which case this change is mostly a recorded test. Verify first; add a sever point only if
  needed.
- Do not over-claim: the failure is at the WIT boundary, not the memory level. Keep CHERI as the follow-up.
- Do not weaken the free-text residual note: adversarial data in a *permitted* field still reaches a
  tool-capable node; revocation withdraws the handle's authority, it does not filter content.
