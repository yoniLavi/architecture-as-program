# Change: Revoke a named capability instance at runtime

## Why
Capabilities are provisioned when a graph is assembled and live for its whole run. Production
operation sometimes needs to withdraw authority *while running* — revoke a compromised handle, drain
access to a deprecated store — without redeploying the graph. Until now there was no instance to
revoke: capabilities shared by type meant severing one severed every node naming the type. The
just-landed capability-*identity* primitive supplies the missing prerequisite — a nameable instance —
so revocation can target exactly one instance and leave its siblings untouched.

## What Changes
- Add runtime **revocation** of a named capability instance: after assembly, the host can sever a
  specific `(capability type, identity)` instance so a node's subsequent use of it fails instead of
  exercising authority.
- Model revocation as **severable indirection** (the object-capability caretaker pattern): the node
  holds a caretaker that forwards to the real handle; a separate revoker severs it. Authority to
  revoke is distinct from authority to use.
- Keep revocation **opt-in**: only instances provisioned as revocable are wrapped; type-only and
  plain-identity provisioning are byte-for-byte unchanged.
- Not in scope: capability **rotation** (re-pointing a live handle at a new resource); the
  graph-transformation / redeployment form of revocation; sandbox-tier enforcement of revocation
  (host tier first). Each is a distinct later step this change enables.

## Impact
- Affected specs: `signal-graph-runtime` (ADDED: a provisioned instance can be revoked at runtime;
  revocation is targeted and opt-in).
- Affected code: `poc/handles.py` (a caretaker wrapper + `RevokedCapabilityError`), `poc/graph.py`
  (provision revocable instances behind caretakers; expose the revoke operation), tests.
- Proposal feedback: Technical Note A "Capability revocation and rotation" — upgrade the entry from
  unbuilt to demonstrated on the identity primitive, keeping rotation and the redeployment form open.
- Builds on: archived `add-capability-identity` (identity is the prerequisite a revoke targets).
