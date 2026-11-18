# Tasks

Every session first checks the feed recorder (`operate-feed-triage` 0.2) and `git status`.

## 0. Approval

- [ ] 0.1 The author approves this proposal and answers `design.md`'s open questions.
  Record the date and the answers here. No paper text is written before this.

## 1. The evidence, made quotable

- [ ] 1.1 A report over the committed bind, split and provenance records, emitting
  `dist/grants.{md,json}` with a `display` block and a `counts` block. It calls no model.
  Verify: built by `make build`, and the headline counts pinned by test (41 runs; 16
  attacker and 24 bill attempts refused; 1 of 7 unavoidable; the split re-run's 4 of 5).
- [ ] 1.2 `make build` green; commit.

## 2. The paper

- [ ] 2.1 `papers/05-…/proposal.typ` with a title block and no DOI, its corpus entry in
  `papers/README.md`, and the Makefile target. Verify: `scripts/check-corpus-citations.py`
  refuses a stamp while Paper 4 is unpublished.
- [ ] 2.2 Draft, every figure interpolated from `dist/grants.json`, with each pinned limit
  in the same paragraph as its claim (D3).
- [ ] 2.3 `tests/test_paper5_figures_pinned.py`.

## 3. Review

- [ ] 3.1 Agentic review: a critical review and an adversarial claims check by
  subagents. Record the findings and what was done.
- [ ] 3.2 The author's read.

## 4. Publication

- [ ] 4.1 After Paper 4 is published: stamp the DOI, publish, and commit `RECORD.json`.
- [ ] 4.2 `make build` and `make spec-check` green; archive.
