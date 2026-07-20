# Change: Prepare the corpus for preprint — tidy both papers

## Why
Paper 1 (the founding vision) is to be posted as an arXiv preprint soon, and Paper 2 (the demonstrator) has
just reached paper form. Two things stand in the way, one per paper.

**Paper 1 needs an editorial + metadata pass, and it is currently frozen.** The freeze
(`scripts/check-freeze.py` guarding `papers/01-vision/proposal.typ` against commit `59898cc~1`; corrections
confined to `ERRATA.md`) was the right device while the paper was only an internal record. For an actual
public preprint it is too strict: it forbids fixing a typo or a citation year in the body, and it carries no
publication front matter. The maintainer's decision is a **one-time unfreeze → editorial tidy → re-freeze**
at the published commit.

The hazard this creates is precise and must be designed around: Paper 2's §5 (predictions and outcomes) and
§1.4 argue that the vision's claims were *made before outcomes were known*, and that argument is only honest
if the tidy changes **no claim**. So the unfreeze is licensed for editorial and metadata changes only — no
prediction added, removed, strengthened, or weakened — after which the paper is re-frozen and errata-only
again.

**Paper 2 is 47 pages and says the same things many times.** Two independent review passes over the freshly
assembled paper found heavy redundancy: the wasip1-vs-`unknown-unknown` ambient-authority argument stated 4×,
the free-text residual 6×, the `ServiceOutcome` unchecked-alias gap 4×, the trust-lattice mechanism 5×, the
host-tier escape gap 5×, covert channels 3×, distributed authority 3×, and the benchmark-timing caution and
one-machine caveat twice each. The maintainer's decision is an **aggressive tighten** to ~30–34pp: dedup each
repeated point to one primary statement plus cross-references, prune marginal passages, and compress the
inherited Related Work — without touching the hedging discipline, the predictions-vs-outcomes table, or the
substance of the threats-to-validity section, which are the paper's strengths.

## What Changes

### Workstream A — Paper 1 preprint preparation (one-time unfreeze)
- **Relax the freeze rule** to permit a *single* editorial-and-metadata revision of a frozen paper for the
  purpose of publication, after which the freeze re-applies at the published commit. The invariant that
  survives: the revision changes no substantive claim, and post-publication the paper is again errata-only.
  (Spec: MODIFIED requirement in `paper-corpus`.)
- **Editorially tidy `papers/01-vision/proposal.typ`**: typos, phrasing, obvious infelicities, and any
  genuinely wrong factual detail (e.g. a citation year) that would otherwise be an erratum. No claim may be
  added, removed, strengthened, or weakened — verified by a diff review against the freeze commit.
- **Add preprint front matter**: author affiliation, a short preface/cover note situating the paper as Paper 1
  of the program and pointing forward to Paper 2, and honest dating (it dated itself June 2026 and is
  editorially revised for the preprint — the front matter must not pretend the revised text is byte-identical
  to June 2026).
- **Re-freeze**: move `FREEZE_REF` in `scripts/check-freeze.py` to the new published commit; update
  `papers/01-vision/ERRATA.md`'s preamble to describe the new freeze point and the one-time editorial revision.
- **Reword Paper 2's freeze language**: §1.4 and §5 (and the title-page footnote) currently say Paper 1 is
  "preserved verbatim / frozen and unedited." Change to "editorially tidied for its preprint but substantively
  unchanged from the June 2026 vision," so Paper 2's own account of the arrangement stays accurate.

### Workstream B — Paper 2 aggressive tighten
- **Deduplicate** each repeated point to one primary statement plus cross-references. Catalogue in
  `design.md`; the primary location for each is where the point is load-bearing, the rest become references.
- **Prune marginal passages** and **compress the inherited Related Work**, targeting ~30–34pp.
- **Preserve, do not touch**: the hedging discipline (conditional mood on unproven claims), the
  predictions-and-outcomes table and its four statuses, and the substance of the threats-to-validity section.
  Cuts that would weaken an honest limitation are out of bounds; this is a tightening, not a softening.
- **Sweep residual hedging spots** flagged by review that were not already fixed, and re-verify the
  confined-tier-vs-universal scoping throughout.

### Not in scope
- New artifact, evaluation, or demonstrator behaviour (this is editorial).
- Any *substantive* revision of Paper 1's claims (the unfreeze is editorial-and-metadata only).
- The act of posting the preprint (a separate human step), and the choice of venue beyond "arXiv."

## Impact
- **Affected specs:** `paper-corpus` — MODIFIED "The founding vision paper is frozen and self-contained" to
  permit a one-time editorial-and-metadata revision for publication with the no-substantive-change invariant.
- **Affected docs:** `papers/01-vision/` (tidy, front matter, re-freeze), `papers/02-demonstrator/` (tighten +
  reword freeze references), `scripts/check-freeze.py` (`FREEZE_REF`), `papers/01-vision/ERRATA.md`, `AGENTS.md`
  (freeze-rule and length guidance). No artifact-behaviour change; `citations.bib` may gain a preprint/DOI
  detail.

## Dependencies
Depends on `rewrite-demonstrator-paper` (archived): Paper 2 is in paper form with the freeze-referencing
language this change rewords. This is the last editorial step before Paper 1 is posted.

## Open questions (for the implementing session)
- **Dating.** How the tidied Paper 1 represents its date honestly — e.g. "First circulated June 2026;
  editorially revised for preprint July 2026" — without undermining the June-2026 provenance Paper 2 cites.
- **The editorial/claim boundary.** Fixing a wrong citation year is uncontroversial; rewording a sentence that
  is merely awkward risks shading a claim. The implementing session should adopt a bright line (diff every
  change against the freeze commit; anything touching a claim's meaning is rejected or routed to errata).
- **Cut depth per section.** ~30–34pp is the target; which specific marginal passages are genuinely cuttable
  versus load-bearing is decided during implementation, guided by the `design.md` catalogue.
