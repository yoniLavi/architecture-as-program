## Context
Two papers, two modes of editorial work, one combined change (maintainer's call). Paper 1 is frozen and gets a
one-time editorial unfreeze for its preprint; Paper 2 is living and gets an aggressive tighten. The papers now
have separate `proposal.typ` files, so tightening Paper 2 does not touch Paper 1 — a welcome side effect is
that their near-identical Related Work sections diverge, reducing cross-paper duplication.

This document exists mainly to carry the **redundancy catalogue** for Workstream B, so the tightening is a
checklist rather than a re-derivation, and to fix the **editorial/claim bright line** for Workstream A, which
is the part most able to go quietly wrong.

## Decisions

### Decision: Paper 1's unfreeze is editorial-and-metadata only, enforced by diff
The predictions-vs-outcomes argument in Paper 2 is worthless if Paper 1's claims move. So the licensed changes
are: typo/spelling/grammar fixes, phrasing of awkward-but-unambiguous sentences, formatting, publication front
matter (affiliation, preface, dating), and correction of a *factually wrong* detail (a citation year, a
misspelled proper noun) that would otherwise be an erratum. The bright line: **diff every hunk against the
freeze commit `59898cc~1`; if a hunk changes what a sentence claims — adds/removes a hedge, shifts a
prediction, alters scope — it is rejected or routed to ERRATA.md instead.** A claim that is genuinely *wrong*
is recorded as a dated erratum, not silently rewritten, exactly as today.

### Decision: honest dating over a clean date
The tidied Paper 1 must not present its revised text as byte-identical to June 2026. Front matter states the
provenance plainly ("First circulated June 2026; editorially revised for the preprint, <month> 2026") and the
ERRATA.md preamble records the one-time revision and the new freeze point. This keeps faith with Paper 2's
citation of it as the pre-outcomes record while being truthful that a copyedit happened.

### Decision: re-freeze at the published commit, keep errata-only thereafter
After the tidy, `FREEZE_REF` moves to the commit that is the published preprint, and the paper returns to
errata-only. The spec change is narrow: it permits *one* editorial revision for publication, not open-ended
editing.

### Decision: Paper 2 tightening preserves the three strengths
Dedup and prune freely, but the hedging discipline, the predictions-and-outcomes table, and the substance of
threats-to-validity are out of bounds for weakening. A cut that removes a stated limitation, softens a hedge,
or drops a "confined tier only" scoping is a regression, not a tightening.

## Workstream B — the redundancy catalogue
Each entry: the point, its proposed **primary home** (kept in full), and the distinguishing phrase to find the
**secondary** occurrences (reduced to one clause + a cross-reference). Line numbers drift as editing proceeds;
grep the phrase.

1. **wasip1 vs `unknown-unknown` ambient authority** (≈4–5×). Primary: §3.4 confined tier ("An earlier
   iteration of this tier compiled nodes to `wasm32-wasip1`… What was a configured absence is now a structural
   one"). Secondaries to compress: §5.3 Partial ("An earlier version confined nodes under an empty WASI
   context"), §6 Related work (reused sandboxing prose, "A `wasm32-wasip1` module still _imports_"), §5.5
   Revealed, and the compressed restatement in §4. Keep §5.3's *point* (that "no ambient authority" named two
   guarantees) but state it in one sentence referring to §3.4.

2. **Free-text residual** (≈6×). Primary: §4.3 Evaluation ("The residual, stated plainly"). Secondaries:
   Abstract (one clause, keep), §2.4 Design (the "schema that retains a free-text field" sentence + the
   "framework supplies the enforcement substrate; disciplined schema design…" formula), §2's concrete-graph
   restatement, §8.4 Threats, Conclusion (one clause, keep). The "framework supplies the substrate…" formula
   appears ≥3× verbatim — keep it once (in §4.3), delete elsewhere.

3. **`ServiceOutcome` unchecked-alias gap** (4×). Primary: §3.6 sub-graph execution (where the mechanism is).
   Secondaries: §5.5 Revealed, §7.1 Phase 1 agenda, §8.4 Threats — each independently re-explains "the language
   has no alias mechanism and the cross-graph analysis never examines the output side." Reduce three of the
   four to a clause + reference.

4. **Trust-lattice mechanism** (5×). Primary: §3.2 Validator (the full mechanism + the laundering argument).
   Secondaries: §2 Design (keep the design-level statement, it precedes the artifact), §5.2 Substantiated,
   §5.5 Revealed, §7.1 Phase 1. The "one order not two" point is made in both §3.2 and §5.5 — keep §5.5's as
   the *outcome* framing but drop its re-derivation.

5. **Host-tier escape gap** (5×). Primary: §4.4 Evaluation (the table + expected-ESCAPES framing). Secondaries:
   §3.4 host tier, §4.3, §5.3, §8.3. Several are one-liners already; ensure they reference §4.4 rather than
   re-argue.

6. **Covert channels** (3×, near-identical self-contained paragraphs). Primary: §7.2 Phase 2 (where the
   forward plan lives). Secondaries: §2.8 Design security, §8.4 Threats — reduce to a sentence each.

7. **Distributed authority** (3×). Primary: §7.3 Phase 3. Secondaries: §2.8, §8.4 — reduce to a sentence each.

8. **Benchmark timing caution + one-machine caveat** (2× each). Primary: §4.2 Evaluation. The §8.2 Threats
   copy was already trimmed to a reference during the rewrite's review pass — verify it did not regress and
   that §8.2 points at §4.2 rather than restating.

## Workstream B — residual non-duplication sweep (from review, not yet fixed)
- **CHERI backstop overclaim.** §6 CHERI ("The result is two complementary enforcement layers") reads as a
  property of this work's stack; add "would provide, once integrated (§7.3)" or similar.
- **Proposal voice left in Related Work.** "This work replaces the C4 model…" and "the kind of typed,
  capability-aware graph substrate we propose" still read as written pre-artifact. Align to the reporting
  register used elsewhere.
- Re-run both review lenses (hedging discipline; structure/duplication) after the cut, since aggressive
  editing can reintroduce a present-tense overclaim or a dangling reference.

## Risks / Trade-offs
- **The unfreeze quietly becomes a rewrite.** → the diff bright line above; a reviewer (or a review agent)
  checks the Paper 1 diff hunk-by-hunk against the freeze commit before re-freezing.
- **Aggressive tightening cuts a load-bearing hedge or limitation.** → the three-strengths rule; re-run the
  hedging review after the cut and confirm the predictions table and threats section are intact.
- **Cross-references break during the cut.** → `make build` fails on a broken typst ref; also diff the
  `@sec:`/`@tab:` set before and after.

## Migration Plan
Editorial. Sequence within the implementing session: (A1) unfreeze-tidy Paper 1 with diff review → (A2) front
matter + dating → (A3) commit as the published preprint → (A4) move `FREEZE_REF`, update ERRATA.md, re-freeze
→ (A5) reword Paper 2's freeze language. Then (B) tighten Paper 2. A can land before B; B is independent of the
re-freeze. Build stays green throughout.
