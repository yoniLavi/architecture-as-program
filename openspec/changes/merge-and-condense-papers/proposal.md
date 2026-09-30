# Merge Papers 2 and 3 into one condensed paper

> **Status: in progress.** Scaffolded 30 September 2026. The author settled the open
> questions and approved the budget the same day (`design.md` §"Decisions").

## Why

On the day of publication, the author's final review found that Paper 2 cites Paper 3
ten times, while Paper 3 is unpublished and cites Paper 2 for every figure. The
dependency ran both ways, so neither paper could be published first honestly. Asked
whether to publish both at once or break the cycle, the author went further. The two
papers had grown too detailed, and the author would rather merge and condense them,
saying: *"I much prefer for us to say more with fewer words than the opposite."*

The July split (`archive/2026-08-01-split-demonstrator-paper`) argued that the systems
claim and the method claim, fused at 45 pages, each weakened the other. That was true at
that length. But the underlying problem was length, not structure. Together the papers
now run to ~30,000 words (Paper 2 ~21,400, Paper 3 ~8,400). `AGENTS.md` already records
that the lever for length is "dropping a capability from the paper's scope, not shaving
prose — a scope decision to raise with the author". The author has now made it.

At the right size, the method material strengthens the systems claim instead of
competing with it. Two parts carry it: the outcomes table, with 19 predictions frozen
and published before building and reported without revision, and the four design
corrections that building forced. Together they show that the claims were not
rationalised after the fact, which few systems papers can show.

## What Changes

- **One paper.** Paper 2 absorbs Paper 3's accounting in condensed form and is
  condensed itself, from a combined ~30,000 words to a target of ~12,000 (about 24
  pages). The budget and the cut list are in `design.md`.
- **Paper 3 is retired** as a separate paper. Its forward agenda shrinks to a short
  future-work passage, and its protocol description to a subsection.
- **The cycle dissolves**, and a rule stops it recurring: a paper published under a DOI
  cites no unpublished work.
- **Machinery that existed only for two papers goes**: the one-owner-per-number rule
  between papers, "the method paper interpolates no data", and the
  `lavi_predicting_2026` citation.
- **Publication** uses the DOI already reserved on Zenodo, **10.5281/zenodo.23057135**.
  A draft's title and file may change before it is published. The stamp is committed
  (`58211c8`) and stays.
- **Nothing is cut that bounds a claim.** Every stated limitation and hedge survives.
  Where a cut would shed one, the hedge wins and the budget is missed. The hedge guard's
  pins in §2.3 and §2.5 will need deliberate re-seeding as §2 condenses, and each
  re-seed is named in its commit.

## Impact

- Affected specs: `paper-corpus`, which drops the two-paper requirements and adds
  the no-unpublished-citation rule
- Affected papers: `papers/02-demonstrator/proposal.typ` (rewritten and condensed);
  `papers/03-method/` (retired)
- Affected build: `Makefile` (Paper 3 targets), `scripts/check-hedges.py` (re-seeded
  pins), `scripts/check-citations.py` (a bib entry cited by no paper becomes an orphan)
- Affected docs: `AGENTS.md` (the corpus description, the two-paper structure, the
  "42pp" note), `papers/README.md`, `METHODOLOGY.md`, `docs/ROADMAP.md`
- Supersedes the `publication-checklist.md` of `prepare-paper-2-publication` for the
  upload itself (title, description, and possibly the filename slug change); that change
  is archived when this one publishes
- Paper 1 is untouched. It is published, frozen, and served from its stored artifacts.
