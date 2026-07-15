## 1. Mechanism and surface
- [ ] 1.1 Add a `Caretaker` wrapper in `poc/handles.py` that forwards every operation to a wrapped
      handle and raises `RevokedCapabilityError` once severed; ensure it presents the same surface as
      the handle it wraps (decide `__getattr__` delegation vs explicit, per design.md)
- [ ] 1.2 Choose the revoker shape (a `graph.revoke(cap_type, identity)` method vs a per-instance
      token returned at provisioning); record the alternative as a design note, not code

## 2. Revocable provisioning
- [ ] 2.1 Extend `assemble(...)` so identity instances marked revocable are provisioned behind a
      caretaker; keep the paired revoke authority with the host, never handed to a node
- [ ] 2.2 Preserve un-revoked provisioning exactly: type-only and plain-identity instances stay bare,
      so the identity change's tests and the type-only default are unchanged

## 3. Revoke operation and enforcement
- [ ] 3.1 Implement the revoke operation: severing a `(cap_type, identity)` instance makes that node's
      subsequent use raise `RevokedCapabilityError`; revocation is idempotent
- [ ] 3.2 Ensure revocation is targeted: severing one instance leaves other identities of the same
      type — and the shared-by-type default — fully usable

## 4. Tests
- [ ] 4.1 Revoke-then-use: a node using a revoked instance raises; before revocation it succeeds
- [ ] 4.2 Targeted revocation: revoking identity A does not affect identity B or a type-only sibling
- [ ] 4.3 Separation: nodes never receive revoke authority; only the host holds it
- [ ] 4.4 Backward compatibility: existing graphs (no revocable declaration) behave exactly as before;
      the security vertical still passes

## 5. Wrap-up
- [ ] 5.1 Fold into the proposal: Technical Note A "Capability revocation and rotation" — mark
      revocation demonstrated on the identity primitive; keep rotation and the redeployment form open
- [ ] 5.2 Note explicitly what this does NOT do: rotation, redeployment-form revocation, and
      sandbox-tier enforcement remain separate later steps
- [ ] 5.3 Full gate green: ruff, pytest, `make build`

## Notes for whoever picks this up
- This is revocation only — the narrow half of Technical Note A's "revocation and rotation" item.
  Rotation reuses the same caretaker indirection (re-point instead of sever) and is a separate change.
- Keep it opt-in and host-tier. Do not retro-break the just-landed identity tests; if caretaker
  wrapping trips `isinstance` checks, fix by transparent delegation or by asserting behaviour.
- Design the revoker shape minimally so a later rotation change can build on it without rework.
- Do not claim unforgeable enforcement on the host tier; whether severing composes to the sandbox tier
  is a `/verify` question for the follow-up, not a claim.
