# Change: Publish the founding vision paper (conclude its sanctioned publication revision)

## Why
The `paper-corpus` spec permits a frozen paper **one editorial-and-metadata revision for the purpose of
publication**. That revision was executed in July 2026 in *preparation* for an arXiv posting — but the
posting never happened, and the venue has since changed: arXiv's October 2025 moderation practice for CS
requires prior peer review for position papers, which the vision paper is, so the maintainer chose **Zenodo**
instead. Publication-day metadata (the DOI of the record the paper is published under) cannot exist before
the venue's record exists, so the sanctioned revision cannot be complete until the paper is actually
published. This change records the honest interpretation: the single publication revision **concludes at the
actual publication event**, and the concluding step is limited to publication-day metadata plus a
rendering-legibility fix (the Figure 1 edge label collides with its node boxes). No prediction, hedge, or
argument moves — the same invariant that governed the preparation step.

## What Changes
- **Clarify the freeze exception** (`paper-corpus`, MODIFIED requirement): the single publication revision
  concludes when the paper is published; publication-day metadata and rendering-legibility fixes belong to
  that same single revision even when preparation and conclusion land as separate commits (here because the
  venue changed). Each step is recorded in the errata record; the paper is re-frozen at the final published
  commit and is errata-only thereafter.
- **Stamp publication metadata** into `papers/01-vision/proposal.typ`'s title block: the reserved Zenodo DOI
  and the CC BY 4.0 licence line.
- **Fix the Figure 1 legibility defect** in `papers/01-vision/diagrams/typed-wiring.typ`: the ill-typed edge
  label overlaps both node titles; widen column spacing and break the label onto two lines.
- **Re-freeze**: move `FREEZE_REF` in `scripts/check-freeze.py` to the published commit; update the guard's
  docstring and `papers/01-vision/ERRATA.md` to record the concluding step under the one revision entry.
- **Publish on Zenodo** (human step): resource type Publication → Preprint, CC BY 4.0, reserved DOI.
- **Record the publication**: link the published DOI from the repository README so paper and artifact
  point at each other; update `AGENTS.md`'s freeze note to say the publication revision is spent.

## Impact
- **Affected specs:** `paper-corpus` — MODIFIED "The founding vision paper is frozen and self-contained"
  (the publication-revision exception gains its concluding-step clause).
- **Affected docs/files:** `papers/01-vision/proposal.typ` (title block only), `papers/01-vision/diagrams/typed-wiring.typ`,
  `papers/01-vision/ERRATA.md`, `scripts/check-freeze.py` (`FREEZE_REF` + docstring), `README.md`, `AGENTS.md`.
- **Not in scope:** any change to the paper's claims, sections, citations, or figures beyond the two files
  above; Paper 2; the shared artifact.

## Open questions
- None blocking. The reserved DOI must be obtained from Zenodo (human) before the stamp can be applied.
