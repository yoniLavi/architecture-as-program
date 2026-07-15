# Change: Express capability identity in the canonical graph source

## Why
Capability *identity* is real in the runtime — distinct instances of one type, routable per node, and now
revocable and rotatable — but it is nameable only through the Python assembly API (`identities=`,
`revocable_instances=`, `rotatable_instances=`), a side channel to the graph. The `graphs/*.json` files are
this project's single source of truth: pseudocode listings and diagrams are generated from them, and the
proposal's thesis is that the graph *is* the artifact. Identity that lives only in Python contradicts that —
the rendered graph cannot show which nodes hold distinct instances, and a parent graph cannot route a named
instance into a specific sub-graph node. This change spells identity in the graph JSON so the runtime,
pseudocode, and diagrams agree, and so identity composes across sub-graph boundaries.

## What Changes
- Add graph-JSON syntax for **naming capability identity** on a node: an optional per-node map from a
  declared capability type to an identity label. `assemble` derives its `identities` from the graph, so the
  Python argument becomes an override/convenience rather than the only source.
- Extend `graphs/schema.json` to validate the new field, and the graph validator to check it (an identity
  may be declared only for a capability the node actually holds — the same rule the runtime enforces today).
- Route identity **across sub-graph boundaries**: a parent graph (`SupportPlatform`) can bind a named
  instance to a sub-graph (`CustomerSupport`) capability slot, so composition carries identity, not just
  type.
- Surface identity in the **generated pseudocode and diagrams** (`scripts/generate-graph.py`) so a distinct
  instance is visible in the rendered artifact and cannot drift from the JSON.
- Keep it **opt-in and backward-compatible**: a node with no identity declaration provisions by type
  exactly as today; existing graphs render and assemble unchanged.
- Not in scope: the revocation/rotation *mechanisms* (already built — this only makes their targets
  nameable in the graph); the full "named capability slots vs opaque identity tokens vs structural
  matching" language-design decision beyond the minimal label form; carrying identity by *type* rather than
  by instance (the component-tier `resource`-typed follow-up).

## Impact
- Affected specs: `signal-graph-runtime` (ADDED: capability identity is expressible in the canonical graph
  source; identity routes across sub-graph boundaries).
- Affected code: `graphs/schema.json` (new field), `scripts/graph_validator.py` (validate identity
  declarations), `scripts/type_parser.py` only if an inline-suffix syntax is chosen, `poc/graph.py`
  (`assemble` reads identity from the graph), `scripts/generate-graph.py` (render identity), `graphs/*.json`
  (optionally demonstrate identity on `support-platform.json`), tests, and the proposal figures/text.
- Proposal feedback: §4/§5 capability-routing discussion and Technical Note A "Hierarchical capability
  routing" — mark the *naming surface* resolved in the graph source and identity routing across sub-graphs
  demonstrated, leaving the by-type-vs-by-instance question open.
- Builds on: archived `add-capability-identity` (runtime identity at the assembly boundary), and enables
  cleaner targeting for `add-capability-revocation` / `add-capability-rotation` (revocable/rotatable
  instances named in the graph rather than in Python).

## Dependencies
Independent of the rotation and sandbox-tier changes, but complementary: once identity is in the graph, a
follow-up can let `revocable`/`rotatable` be declared there too, and the rotation same-kind guard can tighten
to full type/scope compatibility using the declared type.
