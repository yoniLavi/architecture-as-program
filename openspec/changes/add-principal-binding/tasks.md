- [x] `binds_principal` on nodes in `graphs/schema.json`, mirroring `discharges_trust`
- [x] `Node.binds_principal`; `assemble(..., principal=...)`; `AssembledGraph.principal`
- [x] `NodeTrace.principal` and `.acting_as` (RFC 8693 shape), optional in the trace schema so
      graphs binding no principal serialise exactly as before
- [x] Executor threads the chain with the worklist rather than as a cursor, so branches descending
      from different binders cannot pick up each other's delegates
- [x] Composition: the child is assembled with the parent's principal, so a sub-graph cannot mint one
- [x] Validator rejects a binder holding no capability
- [x] Five tests: opt-in absence, containment across a run, chain grows only at declared binders,
      the principal crosses a composition boundary, and the binder-without-capability rejection
- [x] Paper 2 §3.4 reports it; §7.5's open problem narrows to the *typed* form and attenuation
