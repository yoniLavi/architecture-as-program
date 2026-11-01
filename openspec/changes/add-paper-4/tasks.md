# Tasks

Every session working on this change first checks the feed recorder (standing task 0.3 of
`strengthen-generation-evidence`) and `git status`.

## 0. Approval

- [x] 0.1 **The author approves this proposal**: the claim block, the budget, and the three
      open questions (Paper 3, title, directory). No paper text is written before this
      (proposal approved 1 November 2026. The three open questions are still to be
      answered; the first decides the corpus's order, see `docs/ROADMAP.md`)

## 1. The evidence, made quotable

- [ ] 1.1 `poc/architect/report.py`: a `display` block in `dist/architect.json` with
      pre-formatted strings for every non-integer figure (the confirmatory p first)
- [ ] 1.2 Serialise every count the paper states that the JSON only implies
- [ ] 1.3 `make build` green; commit

## 2. Corpus plumbing

- [ ] 2.1 `papers/04-architect/proposal.typ`: a title block with no DOI, section labels, and
      `json("/dist/architect.json")`, `json("/dist/agentdojo-banking.json")`
- [ ] 2.2 `Makefile` targets for Paper 4, and its citable PDF name
- [ ] 2.3 The survey's entries in `citations.bib`, each checked against its source

## 3. Drafting

- [ ] 3.1 §§1–9 to the budget, figures interpolated, the null first
- [ ] 3.2 Hedge pins for Paper 4 in `scripts/check-hedges.py`
- [ ] 3.3 A test pinning the keys Paper 4 reads

## 4. Review

- [ ] 4.1 A full critical review, with the result applied
- [ ] 4.2 **The author's read**
- [ ] 4.3 `papers/README.md`, `AGENTS.md`, `docs/ROADMAP.md`; `openspec validate --strict`
