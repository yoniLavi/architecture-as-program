## Context
`add-capability-identity` made provisioning key on `(type, identity)`, so a specific handle instance is
now nameable: `AssembledGraph.handle_for(node, cap_type)` resolves a distinct instance per declared
identity. That is exactly the thing a revoke targets. Revocation itself is unbuilt — the proposal's
Technical Note A "Capability revocation and rotation" names identity as the now-available prerequisite
and the mechanism as still open. This change builds the mechanism, for the host tier, on that primitive.

## Goals / Non-Goals
- **Goals:** withdraw a *named* capability instance's authority at runtime; a node's use after
  revocation fails rather than exercising authority; revocation is targeted (siblings of the same type
  untouched); authority to revoke is separate from authority to use; revocation is opt-in so un-revoked
  provisioning is unchanged.
- **Non-Goals:** capability **rotation** (re-pointing a live handle at a new resource behind the same
  identity); the graph-transformation / redeployment form of revocation; sandbox-tier enforcement
  (host tier first); concurrent / mid-node-execution revocation semantics (the PoC executor runs nodes
  synchronously, so revocation is well-defined only *between* node runs).

## Decisions
- **Decision: severable indirection (the caretaker pattern).** A revocable instance is provisioned as a
  `Caretaker` that forwards every call to the real handle and checks a `revoked` flag first. This is
  the object-capability revocation mechanism (`@miller_robust_2006`): revocation is an operation on an
  interposed proxy, not a mutation of the underlying resource.
- **Decision: authority to revoke is a separate capability, not held by nodes.** Provisioning returns a
  paired revoker (a closure or small object) to the *host* (the code calling `assemble`); nodes only
  ever receive the caretaker. A node cannot revoke its own — or any — capability. This mirrors the ocap
  separation between using authority and administering it.
- **Decision: revocation is opt-in, layered on identity.** Only instances the caller marks revocable
  are wrapped in caretakers; plain-identity and type-only instances stay bare. This keeps the identity
  change's tests and the type-only default byte-for-byte unchanged, and keeps overhead off the common
  path.
- **Decision: after revocation every method raises `RevokedCapabilityError`.** Uniform, loud failure —
  the same discipline as `CapabilityError` for out-of-scope tool calls. Revocation is idempotent.

## Deliberately underspecified / open
- **The caretaker's surface fidelity.** A caretaker must present the *same* operations as the handle it
  wraps (`infer` / `respond` / `read` / `send` / `emit`) so a node cannot distinguish it until
  revoked. Delegation via `__getattr__` is the obvious route, but it interacts with the identity
  tests' `isinstance(handle, ResponseChannel)` checks — the implementation must either make the
  caretaker duck-type transparently or have those tests assert behaviour rather than concrete type.
  Flagged here so it is decided in implementation, not discovered.
- **The revoker handle's shape.** A per-instance token returned at provisioning vs a
  `graph.revoke(cap_type, identity)` method on the assembled graph. The method form is simpler to
  review; the token form is closer to true ocap (revocation authority is itself a passable value).
  Start with whichever is smaller; let a later rotation change drive further shape.

## Risks / Trade-offs
- **Scope creep into rotation and redeployment.** The Technical Note A item bundles revocation *and*
  rotation. → This change does revocation only; rotation (re-point instead of sever) reuses the same
  indirection and is a separate change.
- **Over-claiming enforcement.** On the host tier a caretaker is host-discipline, not unforgeable — a
  hostile Python node can still `import os`. Revocation binds the *handle's* authority, nothing more.
  The sandbox tier's per-instance host functions route through these same handles, so severing *may*
  compose to the confined tier for free — but that is a `/verify` question, not a claim to bake in.

## Migration Plan
Additive and backward-compatible. Absent any revocable declaration, provisioning behaves exactly as
after `add-capability-identity` (which itself preserved the type-only default). Existing graphs and
tests are unaffected; new tests exercise revoke-then-use and targeted revocation.

## Open Questions
- What is the minimal revoker shape a later **rotation** change can reuse without rework (sever vs
  re-point behind one identity)?
- Does host-tier revocation compose to the sandbox tier through the shared backing handles, or does the
  confined tier need its own severing at the host-function boundary? (A `/verify` question for the
  sandbox-extension follow-up.)
