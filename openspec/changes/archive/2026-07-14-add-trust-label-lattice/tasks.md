## 1. Lattice model
- [x] 1.1 Choose the first-cut lattice (two-point `Untrusted ⊑ Trusted`) and define its partial order
      in the validator; record the graded / Jif-style options as a design note, not code
- [x] 1.2 Represent a node's declared-discharger status as a lattice-level property (reinterpreting the
      existing `discharges_trust` marker), not a standalone flag

## 2. Flow-sensitive wiring
- [x] 2.1 Fold the trust comparison into the edge check: an edge is well-typed only if source trust
      flows to target trust under the order, with no upward coercion (`Untrusted<T>` not `<: T`)
- [x] 2.2 Discharge is the only downward move and only at a declared discharger, yielding a distinct
      refined output type

## 3. Subsume the two-rule scheme
- [x] 3.1 Remove the standalone `discharges_trust` presence check; laundering is now caught by the
      lattice order
- [x] 3.2 Update the unsafe-variant tests: `launder_trust` must fail for a lattice reason; the
      `CustomerSupport` graph and its single discharger stay well-typed

## 4. Tests
- [x] 4.1 Property tests: random trust labellings and wirings; every upward-coercion edge is rejected,
      every discharger-mediated flow accepted
- [x] 4.2 The existing security-vertical tests still pass; the validator stays stdlib-only

## 5. Wrap-up
- [x] 5.1 Fold findings into the proposal: the coercion discussion in @sec:signal-graph and the
      coercion / compositionality / soundness items in Technical Note A
- [x] 5.2 State the compositionality condition the lattice must satisfy, even if the proof is deferred
      to Phase 3
- [x] 5.3 Full gate green: ruff, pytest, `make build`

## Notes for whoever picks this up
- The point is to make trust a property of the *type relation*, not a rule beside it. If
  `launder_trust` still needs a separate check to be caught, the lattice is not doing its job.
- Do not build the Jif-style label system yet. Implement the two-point lattice; keep the richer designs
  as documented options (see `design.md`).
- This is the piece the security-by-construction claim ultimately rests on — bias toward a correct,
  well-tested small lattice over an expressive unproven one.
