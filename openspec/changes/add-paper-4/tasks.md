# Tasks

Every session working on this change first checks the feed recorder (standing task 0.3 of
`strengthen-generation-evidence`) and `git status`.

## 0. Approval

- [x] 0.1 **The author approves this proposal**: the claim block, the budget, and the three
      open questions (Paper 3, title, directory). No paper text is written before this
      (proposal approved 1 November 2026. The three open questions are still to be
      answered; the first decides the corpus's order, see `docs/ROADMAP.md`)

- [x] 0.2 **The author answers the remaining open questions** (`design.md`): title,
      directory, and question 4, whether the slice's two replays over the registered
      records are reported as labelled post-hoc analyses (added 7 November 2026).
      Answered 16 November 2026: title *Reviewed Before It Runs: Automated Review of an
      Architect's Authority* (citable PDF `lavi-2026-reviewed-before-it-runs.pdf`);
      directory `papers/04-architect/`; question 4 is **(b)**, labelled post-hoc analyses
      from `dist/slice.json`, kept apart from the registered results
- [x] 0.3 Paper 3 published and its `RECORD.json` committed (`add-paper-3` 6.5); until then
      Paper 4 may be drafted but not stamped. Published 16 November 2026
      (https://zenodo.org/records/24043532)

## 1. The evidence, made quotable

- [x] 1.1 `poc/architect/report.py`: a `display` block in `dist/architect.json` with
      pre-formatted strings for every non-integer figure (the confirmatory p first).
      Rates are exact and rounded half up, so 17/80 prints 21.3%, as a reader checks it
- [x] 1.2 Serialise every count the paper states that the JSON only implies: a `counts`
      block. **Trials and grants differ:** the registered `unseen` column counts trials
      (59), and those trials hold 61 unseen grants, the unit the slice's replays use
      ("1 of 61"). The paper names which it states, every time
- [x] 1.3 `make build` green; commit

## 2. Corpus plumbing

- [x] 2.1 `papers/04-architect/proposal.typ`: a title block with no DOI, section labels, and
      `json("/dist/architect.json")`, `json("/dist/agentdojo-banking.json")`, and
      `json("/dist/slice.json")` for its `post_hoc` block only
- [x] 2.2 `Makefile` targets for Paper 4, and its citable PDF name
      (`lavi-2026-reviewed-before-it-runs.pdf`)
- [x] 2.3 The survey's entries in `citations.bib`, each checked against its source, and a
      Paper 3 entry with its DOI (`lavi_granted_2026`). Checked 16 November 2026: ACE
      (NDSS 2026), Conseca (HotOS '25), Kim et al. (ICML 2025) and CoT Red-Handed
      (NeurIPS 2025) are peer-reviewed, not arXiv-only as the survey had them; Kolluri's
      autonomy definition is quoted from its abstract; Panickssery's correlation is from
      fine-tuning. Only the entries the paper cites were added (Ye et al., PlanGuard not)
- [x] 2.4 If question 4 is (b): the replays' keys in `dist/slice.json` given a `display`
      block, kept apart from the registered figures and labelled post hoc: `post_hoc`,
      with its own `label` and `display`. The scope-binding replay counts grants (61),
      the behaviour one trials (76 widened, 76 clean), and the keys say which; the
      behaviour replay's 5 gained and 1 lost are computed (`review.crossover`)

## 3. Drafting

- [x] 3.1 §§1–9 to the budget, figures interpolated, the null first (first draft,
      16 November 2026, ~6,000 words of text; the slice's replays in their own post-hoc
      subsection, §5.3)
- [x] 3.2 Hedge pins for Paper 4 in `scripts/check-hedges.py` (nine)
- [x] 3.3 A test pinning the keys Paper 4 reads (`tests/test_paper4_figures_pinned.py`:
      the whole architect artifact, the banking and slice subtrees it reads, and a check
      that the source reads nothing outside them)

## 4. Review

- [x] 4.1 A full critical review, with the result applied (16 November 2026: 5 blocking,
      18 should-fix, 18 minor, each checked against the records before it was applied.
      The pilot history was corrected: a fourth change, never piloted. Hand-typed outcomes
      are now computed or asserted. The Q0 spelling slip and its post-hoc p are stated, by
      the author's decision (`design.md`). New report keys: within-label false alarms per
      view, effect-class planted widenings, target kind, failed-but-scored runs. Two hedge
      pins were re-seeded where the lower bound became a stated expectation)
- [ ] 4.2 **The author's read**. Deferred by the author, 16 November 2026: the research
      agenda goes further first, and Paper 4 publishes later as a checkpoint, as Papers 2
      and 3 did. The draft stays unstamped, held by its figure and hedge pins meanwhile
- [ ] 4.3 `papers/README.md`, `AGENTS.md`, `docs/ROADMAP.md`; `openspec validate --strict`
