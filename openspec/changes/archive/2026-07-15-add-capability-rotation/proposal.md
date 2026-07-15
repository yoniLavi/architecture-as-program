# Change: Rotate a named capability instance at runtime

## Why
Revocation severs a capability instance permanently. Production operation also needs the *other* runtime
move: re-point a live handle at a new resource without redeploying the graph — rotate a credential, cut a
store over to its replacement, swap a backend — while the nodes using it keep the same identity and never
see a gap. The caretaker indirection just landed for revocation already interposes on every call; rotation
reuses it directly (re-point the wrapped target instead of severing it). This closes the second half of
Technical Note A's "Capability revocation and rotation" item, whose first half revocation demonstrated.

## What Changes
- Add runtime **rotation** of a named capability instance: after assembly, the host can re-point a
  rotatable `(capability type, identity)` instance at a freshly provisioned handle, so a node's
  subsequent use exercises the *new* authority — same identity, same caretaker object held by the node,
  new backing target.
- Generalize the caretaker's severance cell into a **target cell** (current target + severed flag), so
  revocation and rotation are two operations on one shared indirection rather than two mechanisms.
- Keep rotation **opt-in and host-tier**, layered on identity exactly as revocation is: only instances
  declared rotatable are wrapped; the rotate authority is host-held and never handed to a node; an
  instance may be both revocable and rotatable, or either alone (least authority).
- Guard rotation to a **same-kind** replacement (a `ResponseChannel` rotates to another
  `ResponseChannel`, never to a `ReadDBHandle`), so the caretaker's surface promise to the node holds
  across a rotation.
- Not in scope: the graph-transformation / redeployment form of rotation; sandbox-tier rotation (host
  tier first, mirroring revocation); full type/scope-compatibility checking of the replacement beyond
  same-kind; rotation *during* a node's execution (the PoC executor is synchronous, so rotation is
  well-defined only between node runs).

## Impact
- Affected specs: `signal-graph-runtime` (ADDED: a named instance can be rotated at runtime; MODIFIED:
  the opt-in wrapping requirement generalizes from "revocable" to "revocable or rotatable").
- Affected code: `poc/handles.py` (a `Rotator`; generalize `_Severance` → a target cell shared by
  `Caretaker`/`Revoker`/`Rotator`; keep `revocable()` working), `poc/graph.py` (a `rotatable_instances`
  parameter; `AssembledGraph.rotators` + `AssembledGraph.rotate(...)`), tests.
- Proposal feedback: Technical Note A "Capability revocation and rotation" — mark rotation demonstrated
  on the identity primitive, so the item's remaining open parts are the redeployment form and the
  sandbox tier.
- Builds on: archived `add-capability-revocation` (the caretaker is the mechanism rotation re-points)
  and `add-capability-identity` (the nameable instance a rotation targets).
