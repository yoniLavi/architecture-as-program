## 1. Workstream A — Paper 1 preprint preparation
- [x] 1.1 Relax the freeze rule: MODIFIED `paper-corpus` requirement permitting one editorial-and-metadata
      revision for publication, re-frozen after, errata-only thereafter (spec delta in this change)
- [x] 1.2 Editorially tidy `papers/01-vision/proposal.typ` — typos, phrasing, formatting, and factually wrong
      details only; **diff every hunk against `59898cc~1` and reject any that changes a claim's meaning**
      (diff verified purely additive: the preprint-note front-matter block only; no existing line touched)
- [x] 1.3 Add preprint front matter: author affiliation (Codeliance, already present), a **standalone**
      preprint note, and honest dating ("first circulated June 2026; editorially revised July 2026"). Per
      maintainer decision the vision paper stands alone and does **not** reference the followup; the earlier
      forward-pointing note was replaced, its `lavi_demonstrator_2026` bib entry removed, and one
      implementation-preview passage (the §7.1 proof-of-concept validator paragraph) was removed as out of
      place for a vision paper. Net diff vs the June 2026 freeze: standalone note added, that passage removed;
      no prediction, hedge, or argument changed (spec MODIFIED accordingly)
- [x] 1.4 Re-freeze: move `FREEZE_REF` in `scripts/check-freeze.py` to the published commit (76a57ef); update
      `papers/01-vision/ERRATA.md` preamble to record the one-time revision and the new freeze point
      (probe path updated too, so the guard actively checks rather than silently skipping; drift-catch verified)
- [x] 1.5 Reword Paper 2's freeze language (§1.4 and the title-page footnote): "editorially tidied for its
      preprint but substantively unchanged from the June 2026 vision" (§5 line was about Paper 2's own mood,
      not Paper 1's byte-identity, so left accurate as-is)

## 2. Workstream B — Paper 2 aggressive tighten (see design.md catalogue)
- [x] 2.1 Dedup the 8 catalogued repeated points to one primary statement + cross-references each
- [x] 2.2 Prune marginal passages and compress the inherited Related Work (47pp → 42pp). Target was ~30–34pp;
      held at 42 by maintainer decision — all catalogued redundancy removed and Related Work halved, but the
      remaining ~8pp is load-bearing (predictions table, threats, open-problem agenda, the type-error
      illustration) and "target not quota; do not cut substance" governs
- [x] 2.3 Residual sweep: CHERI-backstop overclaim, proposal-voice remnants in Related Work
- [x] 2.4 Verify preserved: hedging discipline, the predictions-and-outcomes table, threats-to-validity
      substance — no limitation weakened, no hedge softened, no "confined tier only" scoping dropped

## 3. Verification
- [x] 3.1 Re-run both review lenses on Paper 2 (hedging discipline; structure/duplication) after the cut;
      confirm no present-tense overclaim or dangling reference was reintroduced
- [x] 3.2 Confirm Paper 1's `@sec:`/`@tab:` reference set and Paper 2's are intact (diff before/after):
      Paper 1 ref/label set byte-identical to freeze; Paper 2 label-definition set byte-identical, every ref resolves
- [x] 3.3 Full gate green: both papers render, citations resolve, freeze guard passes at the new commit;
      ruff, pytest, corpus `make build`
- [x] 3.4 `openspec validate prepare-corpus-for-preprint --strict`

## Notes for whoever picks this up
- The one job that can go quietly wrong is A1.2: an "editorial" reword that shades a claim. When unsure whether
  a change is editorial or substantive, treat it as substantive — route it to errata or leave it.
- ~30–34pp is a target, not a quota. Do not cut a stated limitation to hit it; the honest-limits content is
  what makes the paper survive review.
- Numbers in Paper 2's Evaluation are interpolated from `dist/evaluation.json`; never hand-edit a figure while
  tightening prose around it.
