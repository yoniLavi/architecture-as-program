## Context
A graph node declares capabilities as entries in its `inputs` array that match the graph's top-level
`capabilities` list (both are type strings, e.g. `ResponseChannel<user-session>`). Identity is supplied
out-of-band via `assemble(identities={node: {cap_type: label}})`. The generator renders `inputs` as `with`
clauses; nothing in the JSON says two nodes hold *distinct* instances. This change adds identity to the
source of truth. The main decision is syntax, because the graph JSON is also what the schema validates and
the generator renders.

## Goals / Non-Goals
- **Goals:** identity declarable in `graphs/*.json`; validated by schema + graph validator; consumed by
  `assemble`; rendered in pseudocode/diagrams; routed across sub-graph boundaries; fully backward-compatible.
- **Non-Goals:** the revocation/rotation mechanisms; the complete routing language-design decision; identity
  carried by type rather than instance; declaring revocable/rotatable in the graph (a natural follow-up).

## Decisions
- **Decision: a structured per-node identity map, not an inline suffix.** Add an optional node field, e.g.
  `"capability_identities": { "ResponseChannel<user-session>": "session_a" }`, mapping a declared capability
  type to an identity label. Rationale: it mirrors the existing runtime API (`identities`) one-to-one, keeps
  the capability *type* strings in `inputs` unchanged (so the type parser, edge typing, and the
  `capabilities` list are untouched), and is trivial to validate. The alternative — an inline suffix like
  `"ResponseChannel<user-session> @ session_a"` in `inputs` — reads more compactly in the rendered `with`
  clause but forces the type parser and every consumer of `inputs` to strip identity first, spreading the
  change across the toolchain. Start structured; a later change can add sugar.
- **Decision: `assemble` derives identity from the graph; the Python argument overrides.** The graph becomes
  the source; `identities=` stays as an escape hatch (and for tests) but defaults to the graph's
  declarations. This keeps the dogfooding honest (intent lives in the artifact) without breaking the
  existing API. **Precedence (resolves the first open question): the argument overrides the graph at the
  `(node, capability type)` granularity, not wholesale.** `assemble` starts from the graph's per-node
  declarations and overlays the argument's; where both name an identity for the same `(node, cap)`, the
  argument wins; where only one does, that one applies; a node the argument does not mention keeps its graph
  declaration untouched. Override rather than error, because the argument's whole purpose is to be an escape
  hatch (retargeting one slot in a test without editing the source), and per-`(node, cap)` rather than
  per-node so overriding one slot does not silently drop a node's other graph-declared identities. The
  merged map is then validated by the *same* rule the existing code already applies (unknown node / unknown
  capability / capability-not-held), so an override cannot smuggle in an invalid declaration.
- **Decision: validate the same rule the runtime already enforces.** An identity may be declared only for a
  capability the node actually holds; a label may be shared across nodes (shared instance) or distinct
  (distinct instances). The validator gains one check; the runtime rule is unchanged, just fed from the JSON.
- **Decision: sub-graph routing binds a named instance to a slot.** For `SupportPlatform` provisioning into
  `CustomerSupport`, the parent names which instance fills the sub-graph's capability — the minimal form is
  the parent declaring identity on the boundary the same way a node does. The full "named slots" surface
  (option ii in the routing paragraph) is where this points but is not fully built here; this change carries
  identity across one composition level and records the rest as open.

## Risks / Trade-offs
- **Figure/pseudocode churn.** Rendering identity changes generated output. → Keep it opt-in; only graphs
  that declare identity render differently, and the two shipped graphs change only if we choose to
  demonstrate it (prefer demonstrating on `support-platform.json`, which motivates sub-graph routing).
- **Schema/validator drift.** A new field must be validated or it silently does nothing. → Schema change +
  validator check + a test that an identity for an unheld capability is rejected at validation time, matching
  the runtime's assembly-time rejection.
- **Two sources of identity.** Graph vs Python argument could diverge. → Define precedence (argument
  overrides graph) and test it, or make the argument purely additive.

## Migration Plan
Additive. The new field is optional; absent it, graphs validate, render, and assemble exactly as today. The
`identities=` argument keeps working. Introduce the field, then optionally annotate `support-platform.json`
to demonstrate distinct instances and sub-graph routing.

## Open Questions
- ~~Precedence when both the graph and the `identities=` argument name an identity — override or error?~~
  *Resolved:* the argument overrides the graph per `(node, capability type)`; see the assembly decision above.
- How much of the sub-graph *slot* surface to build now vs defer: does the parent name instances positionally,
  by capability type, or by an explicit slot name? (This is the routing paragraph's option (ii) and is the
  larger language-design obligation.)
- Should revocable/rotatable move into the graph in the same change, or stay in Python until this lands?
  (Kept separate here to bound scope.)
