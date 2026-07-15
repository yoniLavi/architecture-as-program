## 1. Mechanism and surface
- [x] 1.1 Add a `Caretaker` wrapper in `poc/handles.py` that forwards every operation to a wrapped
      handle and raises `RevokedCapabilityError` once severed; ensure it presents the same surface as
      the handle it wraps (decide `__getattr__` delegation vs explicit, per design.md)
      — chose `__getattr__` delegation: it forwards the wrapped surface *including absence*
      (a caretaker over `InferenceLLM` still reports no `respond`), so a node cannot distinguish
      the proxy through the capability surface. The identity tests keep their `isinstance` checks
      because revocation is opt-in — those tests provision no revocable instances, so no caretaker appears.
- [x] 1.2 Choose the revoker shape (a `graph.revoke(cap_type, identity)` method vs a per-instance
      token returned at provisioning); record the alternative as a design note, not code
      — chose the **method** form `AssembledGraph.revoke(cap_type, identity)` as the primary surface
      (smallest for the host to call and review). The backing `Revoker` objects are also exposed on
      `AssembledGraph.revokers`, so the true-ocap **token** alternative (revocation authority as a
      passable value) is available without extra machinery. A later rotation change can add a
      `rotate(new_handle)` operation on the same `Revoker`/`_Severance` cell.

## 2. Revocable provisioning
- [x] 2.1 Extend `assemble(...)` so identity instances marked revocable are provisioned behind a
      caretaker; keep the paired revoke authority with the host, never handed to a node
      — added `revocable_instances: Iterable[tuple[str, str]]`; caretakers wrap the identity-pool
      entry, revokers land in `AssembledGraph.revokers` (host-held).
- [x] 2.2 Preserve un-revoked provisioning exactly: type-only and plain-identity instances stay bare,
      so the identity change's tests and the type-only default are unchanged
      — wrapping is gated behind the `revocable_instances` set; absent it, the pool is untouched.

## 3. Revoke operation and enforcement
- [x] 3.1 Implement the revoke operation: severing a `(cap_type, identity)` instance makes that node's
      subsequent use raise `RevokedCapabilityError`; revocation is idempotent
- [x] 3.2 Ensure revocation is targeted: severing one instance leaves other identities of the same
      type — and the shared-by-type default — fully usable

## 4. Tests
- [x] 4.1 Revoke-then-use: a node using a revoked instance raises; before revocation it succeeds
- [x] 4.2 Targeted revocation: revoking identity A does not affect identity B or a type-only sibling
- [x] 4.3 Separation: nodes never receive revoke authority; only the host holds it
- [x] 4.4 Backward compatibility: existing graphs (no revocable declaration) behave exactly as before;
      the security vertical still passes (137 passed, 21 subtests — 10 new, existing suite unchanged)

## 5. Wrap-up
- [x] 5.1 Fold into the proposal: Technical Note A "Capability revocation and rotation" — mark
      revocation demonstrated on the identity primitive; keep rotation and the redeployment form open
- [x] 5.2 Note explicitly what this does NOT do: rotation, redeployment-form revocation, and
      sandbox-tier enforcement remain separate later steps (stated in the proposal paragraph)
- [x] 5.3 Full gate green: ruff, pytest, `make build`

## Notes for whoever picks this up
- This is revocation only — the narrow half of Technical Note A's "revocation and rotation" item.
  Rotation reuses the same caretaker indirection (re-point instead of sever) and is a separate change.
- Keep it opt-in and host-tier. Do not retro-break the just-landed identity tests; if caretaker
  wrapping trips `isinstance` checks, fix by transparent delegation or by asserting behaviour.
- Design the revoker shape minimally so a later rotation change can build on it without rework.
- Do not claim unforgeable enforcement on the host tier; whether severing composes to the sandbox tier
  is a `/verify` question for the follow-up, not a claim.
