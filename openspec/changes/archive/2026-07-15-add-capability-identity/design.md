## Context
Provisioning currently maps a capability *type string* to a single handle instance
(`AssembledGraph.handles`, keyed by type). Every node naming that type gets the same object. The
sandbox tier already binds capabilities per WASM instance, so the *binding* layer can distinguish
nodes; the gap is upstream, at provisioning and at the graph boundary, where identity is collapsed to
type. This change adds a way to name capability identity so distinct instances can be provisioned and
routed.

## Goals / Non-Goals
- **Goals:** capability identity expressible at the graph boundary; distinct same-typed instances
  provisioned and routed to specific nodes; type-only default preserved for identity-agnostic
  capabilities; groundwork for revocation.
- **Non-Goals:** revocation/rotation (separate later change); the full sub-graph hierarchical-routing
  design; changing the sandbox binding layer (it already isolates per instance).

## Decisions
- **Decision: identity is opt-in; type-only remains the default.** Read-only, stateless handles keep
  today's shared-by-type provisioning; only capabilities that declare an identity get distinct
  instances. This keeps simple graphs unchanged and the change tightly scoped.
- **Decision: provisioning keys on (type, identity), not type alone.** When identity is present, the
  provisioner constructs a distinct handle per identity and routes it to the nodes that name that
  identity.

## Deliberately underspecified (open Phase 1 language-design question)
- **The surface for expressing identity.** Options:
  1. **Named capability slots** — the graph boundary names each instance (e.g. `DBHandle as kb_primary`,
     `DBHandle as kb_replica`); nodes bind by slot name. Explicit, reviewable.
  2. **Opaque identity tokens** — an instance carries an identity value threaded through the graph.
  3. **Structural matching** — identity inferred from additional type structure.
  This change specifies the outcome and implements the smallest surface (likely named slots), leaving
  the choice as a decision revisited by the later hierarchical-routing change.
- **Whether identity is spelled in `graphs/schema.json`** or only at the provisioning API — depends on
  the surface chosen above.

## Risks / Trade-offs
- **Scope creep into full hierarchical capability routing.** The routing item in Technical Note A is
  larger (sub-graph boundaries, aliasing semantics). → This change does only *identity naming*; routing
  through sub-graph boundaries is a separate change that can build on it.
- **Interaction with revocation.** Identity is a prerequisite for revocation; over-designing identity
  for a revocation model that does not exist yet risks churn. → Name identity minimally; let the
  revocation change drive any further shape.

## Migration Plan
Additive and backward-compatible. Absent any identity declaration, provisioning behaves exactly as
today (shared by type). Existing graphs and tests are unaffected; a new test exercises two same-typed
capabilities with distinct identities.

## Open Questions
- Does per-node capability identity subsume, or merely feed, the sub-graph hierarchical-routing item in
  Technical Note A? (Likely feeds: routing across sub-graph boundaries is a further step.)
- What is the minimal identity shape that a future revocation/rotation change can build on without
  rework?
