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
- [x] 3.3b A third round. Must-fix: the freeze was *designated* on 16 July (`2d22c80`, which
      added the guard), two days into building, after the same document had been amended in
      place with building findings; "frozen before" and "could not be quietly amended" were
      both false. The sites now say "frozen at its last state before the executable
      demonstrator", and §7.5 states the designation and the in-place amendments. And
      "every node body was written by hand" understated the artifact: `ParseMessage` was
      generated once, in Python and Rust, from its signature and contract (`poc/generated/`);
      §2's preamble, §5.1, §8 and the ROADMAP now say so. Stale section numbers in the UI, tests,
      ROADMAP and PRIOR-ART fixed. Left to the author: whether Correction 2 is still a
      correction building forced (see the publication checklist)
- [x] 3.3c A fourth round. Must-fix, now of precision rather than history: "the freeze
      commit" named both the pre-build commit and the guard's reference, which was re-pointed
      to the published commit, so only version history fixes the pre-build text; and the
      ported and generated bodies were said to be held to "a contract", but no canonical
      node carries one (the generated body predates the contract language, and a
      tier-equality test is what shows interchangeability). Also the conclusion's
      sub-graph sentence regained its host-tier qualifier
- [x] 3.3d A fifth round (paper only; the corpus round before it found nothing must-fix).
      One must-fix, in the repo rather than the prose: a history rewrite after 21 July had
      left the freeze guard's `FREEZE_REF` (and `PUBLISHED.json`'s `source_commit`) naming
      a commit no fresh clone holds, so the source check skipped itself everywhere but the
      author's clone, and §5.1's description of it was untrue for any reader. Re-pointed
      at the same-tree commits (`5a551e0`; `7acf585~1` for the pre-build state), recorded
      in `ERRATA.md`, and the guard now fails rather than skips when a full clone cannot
      reach its reference (three new tests). Nothing else must-fix: returns had diminished
- [x] 3.5 `openspec validate merge-and-condense-papers --strict`

## 4. Handed off at archive (30 September 2026)

This change was archived once the paper was written and five review rounds had run.
Its open steps moved to `prepare-paper-2-publication` (its tasks 7.1–7.3), which stays open
until upload:

- formerly 3.4, the author's end-to-end read (task 7.1 there, and the first item of its
  `publication-checklist.md`)
- formerly 4.1, the upload to the reserved DOI 10.5281/zenodo.23057135 with *Continues* as
  the only relation to Paper 1 (task 7.2)
- formerly 4.2, archiving `prepare-paper-2-publication` after the upload (task 7.3)
