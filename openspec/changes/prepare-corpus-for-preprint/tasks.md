## 1. Workstream A — Paper 1 preprint preparation
- [ ] 1.1 Relax the freeze rule: MODIFIED `paper-corpus` requirement permitting one editorial-and-metadata
      revision for publication, re-frozen after, errata-only thereafter (spec delta in this change)
- [ ] 1.2 Editorially tidy `papers/01-vision/proposal.typ` — typos, phrasing, formatting, and factually wrong
      details only; **diff every hunk against `59898cc~1` and reject any that changes a claim's meaning**
- [ ] 1.3 Add preprint front matter: author affiliation, a preface situating it as Paper 1 and pointing to
      Paper 2, and honest dating ("First circulated June 2026; editorially revised for the preprint")
- [ ] 1.4 Re-freeze: move `FREEZE_REF` in `scripts/check-freeze.py` to the published commit; update
      `papers/01-vision/ERRATA.md` preamble to record the one-time revision and the new freeze point
- [ ] 1.5 Reword Paper 2's freeze language (§1.4, §5, title-page footnote): "editorially tidied for its
      preprint but substantively unchanged from the June 2026 vision"

## 2. Workstream B — Paper 2 aggressive tighten (see design.md catalogue)
- [ ] 2.1 Dedup the 8 catalogued repeated points to one primary statement + cross-references each
- [ ] 2.2 Prune marginal passages and compress the inherited Related Work; target ~30–34pp
- [ ] 2.3 Residual sweep: CHERI-backstop overclaim, proposal-voice remnants in Related Work
- [ ] 2.4 Verify preserved: hedging discipline, the predictions-and-outcomes table, threats-to-validity
      substance — no limitation weakened, no hedge softened, no "confined tier only" scoping dropped

## 3. Verification
- [ ] 3.1 Re-run both review lenses on Paper 2 (hedging discipline; structure/duplication) after the cut;
      confirm no present-tense overclaim or dangling reference was reintroduced
- [ ] 3.2 Confirm Paper 1's `@sec:`/`@tab:` reference set and Paper 2's are intact (diff before/after)
- [ ] 3.3 Full gate green: both papers render, citations resolve, freeze guard passes at the new commit;
      ruff, pytest, corpus `make build`
- [ ] 3.4 `openspec validate prepare-corpus-for-preprint --strict`

## Notes for whoever picks this up
- The one job that can go quietly wrong is A1.2: an "editorial" reword that shades a claim. When unsure whether
  a change is editorial or substantive, treat it as substantive — route it to errata or leave it.
- ~30–34pp is a target, not a quota. Do not cut a stated limitation to hit it; the honest-limits content is
  what makes the paper survive review.
- Numbers in Paper 2's Evaluation are interpolated from `dist/evaluation.json`; never hand-edit a figure while
  tightening prose around it.
