## 1. Identity surface
- [ ] 1.1 Choose the smallest surface for naming capability identity (likely named slots at the graph
      boundary); record the token / structural options as a design note, not code
- [ ] 1.2 Decide whether identity is spelled in `graphs/schema.json` or only at the provisioning API,
      following the surface chosen

## 2. Identity-aware provisioning
- [ ] 2.1 Key provisioning on (type, identity), not type alone; construct a distinct handle per
      declared identity
- [ ] 2.2 Preserve type-only provisioning as the default when no identity is declared (backward compatible)
- [ ] 2.3 Route each named instance to the nodes that name it (the sandbox tier already isolates the
      per-instance binding)

## 3. Tests
- [ ] 3.1 Two same-typed capabilities with distinct identities are provisioned as distinct instances;
      state on one does not affect the other
- [ ] 3.2 Existing graphs (no identity declared) behave exactly as before; the security vertical still passes

## 4. Wrap-up
- [ ] 4.1 Fold findings into the proposal: Technical Note A "Hierarchical capability routing" (identity
      resolved as a step) and "Capability revocation and rotation" (identity is the prerequisite)
- [ ] 4.2 Note explicitly what this does NOT do: sub-graph hierarchical routing and revocation remain
      separate later changes
- [ ] 4.3 Full gate green: ruff, pytest, `make build`

## Notes for whoever picks this up
- This is the *narrow* half of Technical Note A's routing item: name capability identity, nothing more.
  Sub-graph routing (named slots vs structural matching across boundaries) and revocation are separate,
  larger changes this one enables.
- Keep identity opt-in. If a simple read-only graph changes behaviour, the scope has crept.
- Design the identity shape minimally so a later revocation/rotation change can build on it without rework.
