## 1. Cross-language regeneration (moves §5.2 "interchangeable across languages" beyond n=1)

- [x] 1.1 Pick the capability-holding node(s) to regenerate (`FetchContext` for a database read handle; `SendReply` if identity routing across the WIT boundary is in reach) and record the choice in design.md
- [x] 1.2 Regenerate the node in Rust from the graph signature + contract; add the crate under `poc/sandbox/rust/`, build with `make wasm`, commit the component
- [x] 1.3 Wire the regenerated node into the registry behind the same graph JSON (no graph edit); add a test asserting the end-to-end outcome is unchanged
- [x] 1.4 Extend the interface-derivation test so the new component's imports are checked against its `with` clause

## 2. Confined-tier coverage (widens §5.2 "cannot exceed declared capabilities")

- [x] 2.1 Port enough remaining path nodes to components that a majority of the taken path runs confined; keep host-tier fallbacks registered
- [x] 2.2 Add a majority-confined execution test asserting outcome parity with the host-tier run and per-node tier reporting
- [x] 2.3 Update the evaluation harness's tier table so `dist/evaluation.{md,json}` reports the new coverage (no hand-typed figures in the paper)

## 3. Cross-tier sub-graph composition (closes a named "not attempted" bound)

- [x] 3.1 Make sub-graph execution tier-aware: a host-tier parent nests a child whose nodes resolve to their own tiers
- [x] 3.2 Test: `SupportPlatform` → `CustomerSupport` with confined child nodes completes; tier report covers nested nodes; `customer_session` identity routing still lands on the child's reply node
- [x] 3.3 Test: a confined child node cannot reach a capability the parent did not route (confinement across the composed boundary)

## 4. ServiceOutcome alias check (closes the recorded output-side validation gap)

- [x] 4.1 Implement the output-side cross-graph check in `scripts/graph_validator.py` (structural union comparison against the child's terminal types); keep it stdlib-only
- [x] 4.2 Flip the gap-pinning test from asserting the gap to asserting the rejection; add a mutation-corpus case in `poc/evaluate.py` pinned to verdict *and* reason class
- [x] 4.3 Confirm both canonical graphs still validate and the corpus growth is pinned (unpinned `UNSAFE_VARIANTS` entries are errors)

## 5. Paper 2 updates

- [x] 5.1 §3: report the new coverage, the cross-tier composition, and the output-side check as built facts
- [x] 5.2 §5: upgrade the three verdicts with their remaining restrictions stated (interchangeability still bounded by contract incompleteness; enforcement still WASM-boundary, not memory-level)
- [x] 5.3 §7/§8: remove only the bounds this change actually closed (cross-tier composition, alias gap); leave multi-terminal aggregation and every §5.3 conditional untouched
- [x] 5.4 `make build` green; freeze guard, citation check, and pinned evaluation verdicts all pass
