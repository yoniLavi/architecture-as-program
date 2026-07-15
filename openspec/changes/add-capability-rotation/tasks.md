## 1. Mechanism: generalize the caretaker cell
- [ ] 1.1 Replace `_Severance(revoked)` in `poc/handles.py` with a target cell carrying the current
      `target` handle and the `revoked` flag; `Caretaker.__getattr__` reads the flag (raise if set) then
      forwards to `cell.target` instead of a fixed `_wrapped`
- [ ] 1.2 Add a `Rotator` (host-held authority) that re-points `cell.target`; keep `Revoker` flipping
      `cell.revoked`; define ordering (severed wins — a revoked instance stays revoked after a rotate)
- [ ] 1.3 Keep `revocable(handle) -> (caretaker, revoker)` working; add `rotatable(handle) -> (caretaker,
      rotator)` and an internal path that mints both authorities over one caretaker/cell

## 2. Rotatable provisioning
- [ ] 2.1 Add a `rotatable_instances` parameter to `assemble(...)`; wrap an instance in a caretaker if it
      is named in `revocable_instances` *or* `rotatable_instances`, minting only the requested authorities
- [ ] 2.2 Store rotators on `AssembledGraph.rotators` (host-held, never handed to a node); keep the
      revocation path and the type-only / plain-identity defaults byte-for-byte unchanged

## 3. Rotate operation and enforcement
- [ ] 3.1 Implement `AssembledGraph.rotate(cap_type, identity, new_handle)`: re-point the named instance's
      cell so subsequent use is served by `new_handle`; raise if the instance was not provisioned rotatable
- [ ] 3.2 Enforce the same-kind guard: reject a replacement whose type differs from the current target's
- [ ] 3.3 Ensure rotation is targeted: rotating one instance leaves other identities and the shared-by-type
      default unchanged

## 4. Tests
- [ ] 4.1 Rotate-then-use: a node's use is served by the original handle before rotation and the new handle
      after (observe via distinct backing state)
- [ ] 4.2 Targeted rotation: rotating identity A does not affect identity B or a type-only sibling
- [ ] 4.3 Same-kind guard: rotating to a different capability kind is rejected
- [ ] 4.4 Independent authorities: a rotatable-but-not-revocable instance exposes rotate but no revoke;
      revoked-then-rotated stays revoked
- [ ] 4.5 Backward compatibility: existing graphs (no rotatable/revocable declaration) behave exactly as
      before; the revocation and security verticals still pass

## 5. Wrap-up
- [ ] 5.1 Fold into the proposal: Technical Note A "Capability revocation and rotation" — mark rotation
      demonstrated on the identity primitive; keep the redeployment form and the sandbox tier open
- [ ] 5.2 Run `/verify`: drive rotate-then-use through `poc.runtime.execute` so the new authority is
      observed during a real graph run, not just a unit test
- [ ] 5.3 Full gate green: ruff, pytest, `make build`

## Notes for whoever picks this up
- Rotation is the in-place runtime form only — re-point a live caretaker. The redeployment form is separate.
- Reuse the caretaker; do not add a second indirection. One cell, three roles (use / revoke / rotate).
- Keep it opt-in and host-tier, and least-authority: rotatable and revocable are granted independently.
- Same-kind guard protects the node's surface; stricter type/scope checking waits for graph-level identity.
