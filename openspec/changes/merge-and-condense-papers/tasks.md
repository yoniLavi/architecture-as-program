# Tasks

## 0. Before writing

- [x] 0.1 Author settles the open questions in `design.md` (budget moves, title, Paper 3's
      directory, Zenodo relations to Paper 1)
- [x] 0.2 Author approves the section budget

## 1. The merged paper (`papers/02-demonstrator/proposal.typ`)

Words are prose only, measured on 30 September 2026 (target in brackets).

- [x] 1.1 §1 Introduction, claim and contributions: 747 (~900)
- [x] 1.2 §2 Design: 1,881 (~1,800). No hedge pin moved: all 19 fragments survive verbatim in
      `sec:concrete-graph` and `sec:security`, so none was re-seeded
- [x] 1.3 §3 Implementation, with an "Also built" subsection: ~2,090 (~2,000); "Also built"
      alone ~920 (~600), over because each mechanism keeps its limits
- [x] 1.4 §4 Evaluation: ~1,410 (~2,000); all figures still interpolated
- [x] 1.5 §5 Predictions and outcomes: 850 prose plus the 19-row table (~1,500). The
      table is now data (`#let outcomes`), and the verdict counts are computed from it
- [x] 1.6 §6 Related work: 1,108 (~1,500)
- [x] 1.7 §7 Limitations and open problems: 1,186 (~1,500), with a new §7.5 for threats
      from the method
- [x] 1.8 §8 Future work: 134 (~300); §9 Conclusion: 289 (~400)
- [x] 1.9 Abstract rewritten for the merged claim; magnitudes only (338 words)
- [x] 1.10 Remove every `@lavi_predicting_2026` citation; cite no unpublished work

## 2. The corpus

- [x] 2.1 Retire Paper 3: `papers/03-method/` deleted (tag `paper-3-before-merge`); its
      Makefile targets and the `lavi_predicting_2026` and `lavi_confinement_2026` bib
      entries removed (the second was only Paper 3's citation of Paper 2)
- [x] 2.2 `AGENTS.md`, `papers/README.md`, `README.md`, `docs/ROADMAP.md`,
      `docs/PRIOR-ART.md`, and the repo's slash commands: one living paper; the two-paper
      rules dropped; the "42pp" note replaced with the new budget. `METHODOLOGY.md` had no
      two-paper content
- [x] 2.3 Title and slug unchanged per the author's answer; the Makefile's publication name
      stands

## 3. Verification

- [x] 3.1 `make clean && make build` green, including hedges, citations, freeze
- [x] 3.2 Words per section reported against the budget, with any miss explained (total
      ~10,000 against ~12,000; see 1.x)
- [x] 3.3 A whole-paper read (`/review-proposal 2`, run by an independent reviewer against
      the pre-merge texts) and fixes to what it finds. Must-fix: the merge had spread Paper
      3's "published and frozen before building" to five sites, but `poc/` dates from 14 July
      and Paper 1 was published on 21 July, so only the June *freeze* precedes the build. All
      five are corrected, and the protocol now says the publication revision came after
      building began. All should-fix and most nice-to-have items applied
- [x] 3.3a A second round of independent paper and corpus reviews. Must-fix: the fix in 3.3
      kept "frozen before any of it was built" at five sites, but a stdlib validator running
      early forms of all six §3.1 analyses (and rejecting `launder_trust`) already existed at
      the freeze commit, described by a passage the publication revision removed. The five
      sites now say "before its executable demonstrator was built", §5.1 names the early
      validator and the removed passage, and §7.5 discloses that three rows credit analyses
      that partly predate the freeze. Correction 2 misstated what the vision separated (local
      discharge vs the wiring check) and what admits laundering; restated. Also: the
      change's own proposal and design repeated the timeline error, AGENTS.md recorded the
      editor verdict as *partial* (it is *not attempted*), and the spec delta left "both
      living papers" in the capability-sweep requirement
- [ ] 3.4 Author's end-to-end read
- [x] 3.5 `openspec validate merge-and-condense-papers --strict`

## 4. Publication (author's step)

- [ ] 4.1 Upload to the reserved DOI 10.5281/zenodo.23057135 per the checklist, with the
      title and description updated, and *Continues* as the only relation to Paper 1
- [ ] 4.2 Archive this change and `prepare-paper-2-publication`
