## Context
The archived sandbox tier proved the *security* question (a hostile node cannot escape) with core
`wasm32-wasip1` + an empty WASI context + a flat host-function ABI. That was the right first move —
cheapest path to a falsifiable confinement result. This change trades that scaffolding for the
Component Model, whose typed interfaces are the natural runtime form of the signal graph's typed node
boundaries. The goal is not more confinement (the empty context already confines); it is to make the
capability boundary *typed* and to make "no ambient authority" visible in the import set.

## Goals / Non-Goals
- **Goals:** capability kinds as typed WIT interfaces; node bodies as components; no ambient WASI
  imports on the component tier; the typed boundary rejects type-mismatched values; parity with the
  host tier on outcomes; the two-tier composition story preserved.
- **Non-Goals:** CHERI; a general resource/handle framework beyond the five capability kinds;
  multi-language node bodies; replacing the host tier.

## Decisions
- **Decision: model the five capability kinds as WIT interfaces, one `world` per node.**
  A node imports the worlds/interfaces named by its `with` clause and nothing else. The mapping from
  the graph's capability type strings to WIT interfaces is the crux and should be generated from the
  same graph JSON that drives everything else, so the boundary cannot drift from the signature.
- **Decision: keep the LLM tool-orchestration loop inside the node** (as the core-wasm port already
  does), now over typed WIT calls rather than the tagged flat protocol. `GenerateResponse` imports a
  typed `llm` interface offering only `lookup` and a typed `kb` read interface.
- **Decision: the ported nodes move to components; unported nodes stay on the host tier.** The
  migration story (opaque host node → confined node) is unchanged; "confined" now means "typed
  component" rather than "core module with flat ABI".

## Deliberately underspecified (settle at implementation time)
- **WIT world/interface layout** — one shared world with per-capability interfaces, vs one world per
  node. Pick when writing the `.wit`.
- **Bindings toolchain** — `cargo component` vs `wit-bindgen` directly for the Rust side; `wasmtime`'s
  Python component API vs a thin generated shim for the host side. The wasm component tooling is still
  moving; choose the least-friction combination that builds reproducibly and can commit artifacts.
- **Value marshalling for domain types** — how `CustomerQuery`/`ConversationContext` are expressed in
  WIT (records vs strings). Records are the point of the exercise, but the first cut may keep some
  fields as strings; note whatever is deferred.

## Risks / Trade-offs
- **Toolchain weight and churn.** The component-model toolchain is heavier and less stable than core
  wasm. → Confine it to the `poc` group and a `make wasm` step; commit built artifacts so tests run
  without it, exactly as the core-wasm tier does now.
- **Scope creep into a general component framework.** → Model only the five capability kinds the
  vertical needs; anything broader is a later change.
- **Losing the falsifiable confinement result.** → The hostile-node suite must carry over unchanged
  (or strengthened): the component tier must still deny every escape the core-wasm tier denied.

## Migration Plan
Additive then substitutive: stand up the component tier alongside the core-wasm tier, port the two
security-critical nodes, confirm the hostile-node suite passes on the component tier, then retire the
core-wasm ABI for the ported nodes. Host-tier nodes are untouched.

## Open Questions
- Does the component model's typed boundary let us drop the node-side tool loop in favour of a typed
  handler interface, or does keeping the loop in the node remain the more faithful model?
- Can the "imports no ambient WASI" property be asserted as directly as the core tier's cap-import
  test — i.e., is there a clean way to enumerate a component's imports and assert the WASI set is
  empty?
