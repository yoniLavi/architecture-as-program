# Tasks

## 0. Before writing

- [ ] 0.1 Author settles the open questions in `design.md` (budget moves, title, Paper 3's
      directory, Zenodo relations to Paper 1)
- [ ] 0.2 Author approves the section budget

## 1. The merged paper (`papers/02-demonstrator/proposal.typ`)

- [ ] 1.1 §1 Introduction, claim and contributions (~900)
- [ ] 1.2 §2 Design (~1,800); re-seed the hedge pins it moves, named in the commit
- [ ] 1.3 §3 Implementation, with an "Also built" subsection (~2,000)
- [ ] 1.4 §4 Evaluation (~2,000); all figures still interpolated
- [ ] 1.5 §5 Predictions and outcomes from Paper 3: protocol in brief, `tab:outcomes`
      whole, the four corrections (~1,500)
- [ ] 1.6 §6 Related work (~1,500)
- [ ] 1.7 §7 Limitations and open problems (~1,500)
- [ ] 1.8 §8 Future work (~300); §9 Conclusion (~400)
- [ ] 1.9 Abstract rewritten for the merged claim; magnitudes only
- [ ] 1.10 Remove every `@lavi_predicting_2026` citation; cite no unpublished work

## 2. The corpus

- [ ] 2.1 Retire Paper 3 per the author's answer (delete, or keep unbuilt); remove its
      Makefile targets and the `lavi_predicting_2026` bib entry
- [ ] 2.2 `AGENTS.md`, `papers/README.md`, `METHODOLOGY.md`, `docs/ROADMAP.md`: one living
      paper; drop the two-paper rules; replace the "42pp" note with the new budget
- [ ] 2.3 Title and slug per the author's answer; update the Makefile's publication name

## 3. Verification

- [ ] 3.1 `make clean && make build` green, including hedges, citations, freeze
- [ ] 3.2 Words per section reported against the budget, with any miss explained
- [ ] 3.3 A whole-paper read (`/review-proposal 2`) and fixes to what it finds
- [ ] 3.4 Author's end-to-end read
- [ ] 3.5 `openspec validate merge-and-condense-papers --strict`

## 4. Publication (author's step)

- [ ] 4.1 Upload to the reserved DOI 10.5281/zenodo.23057135 per the checklist, with the
      title and description updated
- [ ] 4.2 Archive this change and `prepare-paper-2-publication`
