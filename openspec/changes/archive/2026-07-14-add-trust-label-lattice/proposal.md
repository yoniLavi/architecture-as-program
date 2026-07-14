# Change: A flow-sensitive trust-label lattice with no upward coercion

## Why
This is the deepest *unbuilt* piece of the proposal's security-by-construction claim, and the one
Technical Note A ("The coercion problem in trust-annotated wiring") flags most sharply. The current
validator enforces trust with **two independent rules**: edge type-compatibility, and a separate
`discharges_trust` presence check. That separation is load-bearing in a way the proposal admits is
fragile: the `launder_trust` variant type-checks on every edge and is caught *only* by the standalone
discharge rule. A type system that folded trust into ordinary subtyping — allowing `Untrusted<T> <: T`
— would admit that laundering invisibly, and the failure would not show up at the level of edge types.

The proposal argues the principled fix is a **security-label lattice** in the Jif @myers_decentralized_1997
lineage: trust levels ordered so that information may only flow *upward* in restriction, with **no
upward coercion** (`Untrusted<T>` is not a subtype of `T`), and wiring checks that are **flow-sensitive
with respect to trust**. This change specifies that property and implements a first version in the
validator, so that trust-laundering is rejected as a *lattice violation* rather than by a rule bolted
on beside edge typing.

## What Changes
- Introduce a **trust-label lattice**: trust levels are lattice elements with a partial order; the
  only way to lower an element (discharge) is an explicit, declared transformation.
- Make wiring checks **flow-sensitive with respect to trust**: an edge is well-typed only if the
  source's trust label flows to the target's under the lattice order. **No upward coercion** —
  `Untrusted<T>` does not inhabit `T`.
- Model **discharge as a typed transformation** performed only at nodes declared as dischargers, not
  as a label the wiring may silently drop.
- Reject **trust laundering structurally**: the `launder_trust` variant is caught by the lattice
  order, not by a separate `discharges_trust` presence check — subsuming today's two-rule scheme into
  one principled check.
- Feed the result back into Technical Note A: replace "the contribution is adapting the well-understood
  literature to the graph wiring context" with a concrete first realisation and whatever it exposes.
- **BREAKING (validator-internal):** the standalone `discharges_trust` check is subsumed by the
  lattice; the graph JSON's `discharges_trust` marker is reinterpreted as "this node is a declared
  discharger", not as a side-condition checked independently of edge typing.

## Impact
- Affected specs: NEW capability `trust-typing` (the type-level trust semantics and their soundness),
  distinct from `signal-graph-runtime` (execution) — the lattice is a property of the static analysis
  and type system, not the runtime.
- Affected code: `scripts/graph_validator.py` and `scripts/type_parser.py` (the trust-propagation
  analysis becomes a lattice check); the unsafe-variant tests (`launder_trust` must now fail for a
  lattice reason). The validator stays stdlib-only.
- Proposal feedback: @sec:signal-graph coercion discussion and the Technical Note A coercion and
  soundness items.
- Not in scope: a mechanised noninterference proof (that is Phase 3, @sec:phase3); a full Jif-style
  decentralised-label model with principals (see design.md — deliberately open).

## Notes on what is deliberately left open (design.md)
Whether the lattice is the minimal two-point `Untrusted ⊑ Trusted`, a small graded set, or a
Jif-style label system with principals is an **open Phase 1 language-design question**. This change
specifies the *properties the lattice must have* (no upward coercion; flow-sensitive wiring; discharge
as the only downward move) and implements the simplest lattice that exhibits them, leaving the richer
designs as a documented decision point rather than a commitment.
