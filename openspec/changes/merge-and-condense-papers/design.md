# Design: merging and condensing

## Principle

The author's rule is to **say more with fewer words**. Each point gets one primary home,
and each section exists because the central claim needs it. The budget below is a target,
not a quota, and it never pays for a hedge: a limit that bounds a claim stays, even where
that costs the budget.

## Central claim (unchanged)

A node's `with` clause *determines* its compiled component's import surface, derived from
the graph and checked against the binary (now including a real over-granting binary as a
pinned negative control). Second: a trust lattice with no upward coercion rejects
laundering that type-checks on every edge. The merged paper adds a third, supporting
strand: these results were **predicted in a paper frozen and published before any of it
was built**, and are reported against those predictions without revision.

## Budget (~12,000 words, ~24 pages)

Word counts are from the 28 September build.

| Section | Now (P2 + P3) | Target | Kept | Cut or compressed |
|---|---:|---:|---|---|
| 1. Introduction, claim, contributions | ~1,200 | ~900 | The window argument (short); the claim block verbatim; contributions ≤5 bullets | P2 §1.3 corpus relation; P3 intro |
| 2. Design | ~3,600 | ~1,800 | Signal graph and `with` clauses; trust annotations; the `CustomerSupport` running example (which §4 tests); security properties by vulnerability class with their conditional mood | FRP history (P2 §2.1.1, 485 words) to one paragraph; running example (1,147) roughly halved |
| 3. Implementation: validator, tiers, derivation | ~1,600 | ~1,400 | §3.2 validator; §3.3.2 confined tier (the lead result) nearly whole | Host tier to two sentences |
| 3.x Also built | ~2,800 | ~600 | One paragraph each: identity, revocation and scoped lifetime; sub-graph execution; contracts with blame; the two-layer trace (and the inspector, one sentence) | Mechanism detail; every limit each one carries stays |
| 4. Evaluation | ~2,450 | ~2,000 | All five subsections, all figures interpolated, the negative control, the free-text residual | Repeated method notes; the flat-ABI comparison paragraph shortened |
| 5. Predictions and outcomes (from P3) | ~2,500 | ~1,500 | The protocol in brief (freeze, DOI, guard, errata-only); `tab:outcomes` whole; the four corrections, one paragraph each | Protocol mechanisation detail; the partial and conditional commentary folded into table notes |
| 6. Related work | ~3,200 | ~1,500 | §6.1 agent security (CaMeL, TACIT, LBAC, AgentDojo) and §6.6 WASM (Spin, wasmCloud, WASI-Virt, WAC, McCann, Wassette) near whole; §6.2 CAmkES whole | Effect systems, CHERI, adjacent traditions and SDD to a paragraph or a sentence each |
| 7. Limitations and open problems | ~2,900 | ~1,500 | Construct, internal, external and security threats; open problems only where one bounds a claim made here | P2 §7.5 (1,368) roughly halved; P3 §6 threats-from-method to a paragraph |
| 8. Future work | ~2,500 | ~300 | The generation experiment; the typed lattice; fan-in | P3 §5 phase-by-phase agenda |
| 9. Conclusion | ~1,000 | ~400 | | |

## What is not negotiable

- Every figure in §4 is interpolated from `dist/evaluation.json`, including counts and
  magnitudes. The abstract and conclusion use magnitudes.
- The free-text residual, "attenuation, not elimination", and the confined-tier-only scope of
  confinement each stay stated where they bound a claim.
- `tab:outcomes` keeps all 19 rows and their verdicts. Only its commentary condenses.
- Paper 1 is cited, never edited.
- No citation to unpublished work.

## Decisions (settled 30 September 2026)

The author settled the four questions below and approved the budget as proposed:

1. **Budget:** approved as it stands. Where "Also built" cannot keep a limit in its share,
   it overruns and the miss is reported, rather than the hedge being cut.
2. **Title:** kept. The slug `lavi-2026-confinement-by-construction` is unchanged.
3. **Paper 3's directory:** deleted. Its text survives in git history, under the tag
   `paper-3-before-merge`.
4. **Zenodo relation to Paper 1:** *Continues* only. DataCite's *Reviews* usually marks a
   peer review, and a harvester could misread it.

## Open questions for the author (settled; see Decisions)

1. **Budget moves.** Keep more of identity and revocation (a tested capability, 939 words
   now), or cut related work harder than ~1,500?
2. **Title.** Keep *Confinement by Construction: Capability Surfaces Derived from an
   Architecture Model*, or name the predicted-before-built strand as well? The filename
   slug `lavi-2026-confinement-by-construction.pdf` follows the title.
3. **Paper 3's directory.** Delete `papers/03-method/` (its text lives in git history),
   or keep it as an unbuilt draft for a possible later methods paper?
4. **The Paper 1 relation.** The merged paper both builds on Paper 1 *and* accounts for it.
   Zenodo relations: *Continues* plus *Reviews* (or *References*) for `10.5281/zenodo.21473361`?

## Method of work (for the implementing session)

1. Settle the open questions and approve the budget.
2. Write the merged paper section by section, with `make build` and the hedge guard
   after each one. Re-seed a pin only deliberately, and name it in the commit.
3. Measure words per section against the budget, and report any miss with its reason.
4. The author reads the whole draft once, end to end, before it is stamped as final.
5. Then run the publication steps in `prepare-paper-2-publication/publication-checklist.md`,
   with the title and description updated.
