## 1. Identity surface
- [x] 1.1 Choose the smallest surface for naming capability identity (likely named slots at the graph
      boundary); record the token / structural options as a design note, not code
  - Chosen: identity is named at the **assembly/provisioning API** as a `node → {capability type →
    identity label}` map. This is the smallest surface that leaves the type strings — and therefore the
    dependency-free validator, `type_parser`, and the sandbox WIT-interface derivation — byte-for-byte
    untouched. Named-slot JSON syntax, opaque tokens, and structural matching are recorded as the open
    Phase 1 options in Technical Note A "Hierarchical capability routing".
- [x] 1.2 Decide whether identity is spelled in `graphs/schema.json` or only at the provisioning API,
      following the surface chosen
  - Only at the provisioning API. `graphs/schema.json` is unchanged, so every existing graph is
    identity-agnostic and unaffected.

## 2. Identity-aware provisioning
- [x] 2.1 Key provisioning on (type, identity), not type alone; construct a distinct handle per
      declared identity
  - `assemble(..., identities=...)` builds a `(cap_type, label) → instance` pool; distinct labels get
    distinct `provision()` results, a shared label shares one instance.
- [x] 2.2 Preserve type-only provisioning as the default when no identity is declared (backward compatible)
  - Absent any identity, `AssembledGraph.instances` is empty and `handle_for` falls through to the
    shared-by-type `handles` dict — the prior behaviour exactly.
- [x] 2.3 Route each named instance to the nodes that name it (the sandbox tier already isolates the
      per-instance binding)
  - `handle_for(node, cap_type)` resolves per-node; `runtime._capability_handles` and `handles_for`
    both go through it, so execution routes the right instance. Misrouted declarations (unknown node,
    unknown capability, capability the node does not declare) fail loudly at assembly.

## 3. Tests
- [x] 3.1 Two same-typed capabilities with distinct identities are provisioned as distinct instances;
      state on one does not affect the other
  - `test_distinct_identities_get_distinct_instances_with_independent_state` (probes
    `ResponseChannel<user-session>`'s `.sent`), plus shared-label and local-reroute tests.
- [x] 3.2 Existing graphs (no identity declared) behave exactly as before; the security vertical still passes
  - `test_same_typed_capability_is_shared_by_type_without_identity` asserts `instances == {}` and the
    shared object; the full suite (host + sandbox) is green: 127 passed, 21 subtests.

## 4. Wrap-up
- [x] 4.1 Fold findings into the proposal: Technical Note A "Hierarchical capability routing" (identity
      resolved as a step) and "Capability revocation and rotation" (identity is the prerequisite)
- [x] 4.2 Note explicitly what this does NOT do: sub-graph hierarchical routing and revocation remain
      separate later changes
  - Both paragraphs now state the naming step is done and name the two remaining obligations (the
    surface / graph-JSON spelling / cross-sub-graph routing, and the revocation mechanism itself).
- [x] 4.3 Full gate green: ruff, pytest, `make build`
  - `ruff check` clean; `uv run --group poc pytest` 127 passed + 21 subtests; `make build` complete.

## Notes for whoever picks this up
- This is the *narrow* half of Technical Note A's routing item: name capability identity, nothing more.
  Sub-graph routing (named slots vs structural matching across boundaries) and revocation are separate,
  larger changes this one enables.
- Keep identity opt-in. If a simple read-only graph changes behaviour, the scope has crept.
- Design the identity shape minimally so a later revocation/rotation change can build on it without rework.
