## Context
`add-capability-revocation` provisions a rotatable/revocable instance behind a `Caretaker` — a forwarding
proxy holding a `_Severance` cell (`revoked: bool`) that a separate `Revoker` flips. The caretaker already
delegates the wrapped handle's whole surface via `__getattr__`. Rotation is the same shape with a different
lever: instead of flipping a flag that makes every call raise, re-point the *target* the caretaker forwards
to. So the two operations want one generalized cell.

## Goals / Non-Goals
- **Goals:** re-point a *named* instance at a new backing handle at runtime; a node's use after rotation
  exercises the new authority through the same caretaker; rotation is targeted (siblings untouched),
  opt-in (un-rotated provisioning unchanged), host-held (nodes cannot rotate), and same-kind (the
  replacement is the same capability kind, preserving the surface).
- **Non-Goals:** redeployment-form rotation; sandbox-tier rotation; full type/scope-compatibility of the
  replacement beyond same-kind; concurrent / mid-node rotation semantics.

## Decisions
- **Decision: one target cell, three roles.** Replace `_Severance(revoked)` with a cell carrying the
  current `target` handle *and* the `revoked` flag. `Caretaker.__getattr__` reads `cell.revoked` (raise if
  set) then forwards to `cell.target`. `Revoker.revoke()` sets `cell.revoked`; `Rotator.rotate(new)` sets
  `cell.target`. Revocation and rotation compose on one instance: a revoked-then-rotated instance stays
  revoked (severed wins); the cell makes that ordering explicit rather than accidental.
- **Decision: rotate authority is a separate object, host-held.** Mirrors the `Revoker` decision. A node
  holds only the caretaker; the `Rotator` lives on `AssembledGraph.rotators`, reachable via
  `graph.rotate(cap_type, identity, new_handle)`. Using, revoking, and rotating are three distinct
  authorities.
- **Decision: rotation is opt-in via `rotatable_instances`, unioned with revocable for wrapping.** An
  instance is wrapped in a caretaker if it is named in `revocable_instances` *or* `rotatable_instances`.
  The graph then exposes `revoke` only for revocable instances and `rotate` only for rotatable ones, so an
  instance can be rotatable-but-not-revocable (or both). This keeps least authority and leaves the
  revocation-only and type-only defaults byte-for-byte unchanged. The existing "opt-in" spec requirement
  generalizes from "revocable" to "revocable or rotatable".
- **Decision: same-kind guard on the replacement.** `graph.rotate` requires `type(new_handle) is
  type(current_target)` (e.g. `ResponseChannel` → `ResponseChannel`). The caretaker promised the node a
  fixed surface; a cross-kind swap would break it. Stricter checking (matching the declared capability
  *scope*, e.g. `DBHandle<'a', read>` vs `DBHandle<'b', read>`) is deferred — the host provisions the
  replacement, so it already controls the resource, and same-kind is the property that protects the node.

## Deliberately underspecified / open
- **How the host obtains the replacement handle.** The minimal path: the host calls `provision(cap_type,
  …)` (or constructs a handle directly) and passes it to `graph.rotate`. A richer form would name a new
  identity/resource spec and let the runtime provision it — but that reaches toward the graph-level
  identity surface (a separate change), so start with a host-provided handle.
- **Interaction with revocation ordering.** Decided above (severed wins), but whether a later change wants
  *un-revoke via rotate* (re-pointing a severed instance to revive it) is left open; the default is that
  revocation is terminal.

## Risks / Trade-offs
- **Scope creep toward redeployment.** This is the *runtime, in-place* form only — re-point a live
  caretaker. The graph-transformation form (rotate by re-emitting the graph) stays out, as it did for
  revocation.
- **Over-claiming enforcement.** Same host-tier caveat as revocation: a hostile Python node can reach
  around the object model. Rotation re-points the *handle's* target, nothing more. Whether it composes to
  the sandbox tier is that change's question.

## Migration Plan
Additive and backward-compatible. Absent any rotatable declaration, provisioning behaves exactly as after
`add-capability-revocation`. `revocable()` keeps its `(caretaker, revoker)` signature; the cell
generalization is internal. Existing graphs and tests are unaffected; new tests exercise rotate-then-use
and targeted rotation.

## Open Questions
- Should the same-kind guard tighten to full capability-type/scope compatibility once identity is spelled
  in the graph JSON (where the declared type is available to check against)?
- Does rotation belong on the sandbox tier in the same change as revocation there, since both re-point the
  same backing handles the WIT host functions bridge to?
