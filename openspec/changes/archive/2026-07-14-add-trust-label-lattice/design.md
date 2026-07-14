## Context
The validator's trust story currently works but rests on two independent rules (edge typing +
`discharges_trust`). The archived runtime change even documented *why* this is fragile: widening a
consumer's input to `Untrusted<RawMessage>` makes every edge well-typed, and only the standalone
discharge rule catches it. That is a concrete argument for a "no upward coercion" discipline — and an
argument that the discipline should live *in the type relation*, not beside it. This change makes the
trust relation a lattice and folds the discharge rule into it.

## Goals / Non-Goals
- **Goals:** a trust-label lattice with no upward coercion; flow-sensitive wiring checks; discharge as
  the sole downward move, performed only at declared dischargers; `launder_trust` rejected as a
  lattice violation; the two-rule scheme subsumed into one.
- **Non-Goals:** a mechanised noninterference proof (Phase 3); compositionality proof of the lattice
  (named separately in Technical Note A); a production label language.

## Decisions
- **Decision: the trust relation is a lattice, and subtyping does not lower trust.** `Untrusted<T>` is
  not `<: T`. The wiring check compares source and target trust labels under the lattice order; an
  upward (more-trusted-required-than-supplied) edge is ill-typed.
- **Decision: discharge is the only downward move, and it is explicit.** A node marked as a discharger
  may emit a lower-trust (or refined, non-`Untrusted`) output from a higher-trust input; no other node
  may. This reinterprets the existing `discharges_trust: true` marker as "declared discharger" within
  the lattice, rather than a side-condition.
- **Decision: implement in the existing stdlib-only validator.** No new dependency; the lattice is a
  small partial-order over labels plus a comparison in the edge check.

## Deliberately underspecified (open Phase 1 language-design question)
- **The lattice itself.** Candidates, in increasing richness:
  1. **Two-point** `Untrusted ⊑ Trusted` — minimal, exhibits every required property, likely the first
     cut.
  2. **Graded** — a small totally- or partially-ordered set (e.g. `Untrusted ⊑ Sanitised ⊑ Trusted`)
     to model staged discharge (parse, then moderate) as distinct levels.
  3. **Jif-style decentralised labels** with principals @myers_decentralized_1997 — the fullest model,
     needed only if per-principal flow policies enter scope (interacts with the user-level
     authorisation item in Technical Note A).
  This change commits to the *properties*, implements (1), and records (2)/(3) as the decision to
  revisit — it does not pick among them.
- **Where labels are written.** Whether trust labels are carried by the `Untrusted<_>` type
  constructor alone, or become a separable annotation, is left to the implementation.

## Risks / Trade-offs
- **Over-engineering the lattice before the language exists.** → Implement the two-point lattice; keep
  the richer designs as documented options, not code.
- **Reinterpreting `discharges_trust` breaks existing graphs.** → The `CustomerSupport` graph's single
  discharger (`ParseMessage`) must remain well-typed under the lattice; the `launder_trust` variant
  must fail for a *lattice* reason, and the test that asserts "no `type mismatch`, only a discharge
  error" is updated to assert the lattice violation.

## Migration Plan
Internal to the validator. The graph JSON schema is unchanged (the `discharges_trust` marker keeps its
spelling, gains a lattice interpretation). Existing valid graphs stay valid; the unsafe variants stay
rejected, now for a principled reason.

## Open Questions
- Does the two-point lattice suffice to express the `CustomerSupport` pipeline's staged discharge
  (parse → moderate), or does it motivate the graded design (2) immediately?
- Compositionality: the lattice must compose so that wiring two well-typed nodes preserves
  noninterference (Technical Note A, "Compositionality of noninterference"). This change should state
  the condition even if the proof is deferred.
