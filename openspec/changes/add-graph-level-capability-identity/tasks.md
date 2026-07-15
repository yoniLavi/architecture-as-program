## 1. Graph-JSON syntax and schema
- [x] 1.1 Add an optional per-node `capability_identities` field (map: declared capability type → identity
      label) to `graphs/schema.json`, with a description matching the `inputs` capability convention
- [x] 1.2 Decide precedence between graph-declared identity and the `assemble(identities=...)` argument
      (override vs additive vs error) and record it in design.md

## 2. Validation
- [x] 2.1 Extend `scripts/graph_validator.py` to check identity declarations: an identity may be declared
      only for a capability the node holds; a label may be shared or distinct
- [x] 2.2 Reject at validation time an identity for an unheld capability, mirroring the runtime's
      assembly-time rejection (a test asserts both agree)

## 3. Assembly consumption
- [x] 3.1 Make `assemble(...)` derive `identities` from the graph JSON; keep the `identities=` argument
      working per the chosen precedence
- [x] 3.2 Verify revocable/rotatable targeting still works when the identity it targets is graph-declared

## 4. Rendering (no drift)
- [x] 4.1 Surface identity in `scripts/generate-graph.py` pseudocode and diagram output so a distinct
      instance is visible in the rendered artifact
- [x] 4.2 Optionally annotate `graphs/support-platform.json` to demonstrate distinct instances and
      sub-graph routing; regenerate figures

## 5. Sub-graph routing
- [x] 5.1 Carry identity across the `SupportPlatform` → `CustomerSupport` boundary: the parent binds a
      named instance to the sub-graph's capability slot
- [x] 5.2 Test that the sub-graph node receives the routed instance and not a sibling the parent did not
      route

## 6. Tests and wrap-up
- [x] 6.1 Tests: graph-declared identity routes distinct instances; unheld-capability identity is rejected;
      no-identity graphs unchanged; sub-graph routing carries identity
- [x] 6.2 Fold into the proposal: §4/§5 routing discussion + Technical Note A "Hierarchical capability
      routing" — mark the naming surface resolved in the graph and identity routing across sub-graphs
      demonstrated; keep by-type-vs-by-instance open
- [x] 6.3 Full gate green: ruff, pytest, `make build` (figures regenerate from the JSON)

## Notes for whoever picks this up
- Prefer the structured `capability_identities` field over an inline `@label` suffix — it keeps the type
  strings in `inputs` (and thus the type parser, edge typing, and `capabilities` list) untouched.
- Keep it opt-in: the two shipped graphs should render unchanged unless you deliberately annotate one to
  demonstrate identity. `support-platform.json` is the better demonstrator (it motivates sub-graph routing).
- This is the *naming surface* only. The full "named slots vs opaque tokens vs structural matching" routing
  decision is larger; carry identity across one composition level and record the rest as open.
