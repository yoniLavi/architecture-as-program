# Tasks

Every session working on this change first checks the feed recorder (standing task 0.3 of
`strengthen-generation-evidence`) and `git status`.

## 0. Approval

- [ ] 0.1 **The author approves this proposal**: the claim block, budget, title, directory and
      stamp check. No paper text is written before this.

## 1. The evidence, made quotable

Before any edit under `poc/`, confirm no generation run or replay is in progress. A run imports
the working tree.

- [ ] 1.1 `poc/generation/report.py`: a `display` block in `dist/generation.json` holding
      pre-formatted strings for every non-integer figure Paper 3 will use. The confirmatory
      p-value is the first of them. Test that typst and pandoc builds render it identically.
- [ ] 1.2 Serialise any count Paper 3 states that the JSON only implies, for example caught
      components that would not have shipped. It is computed in `serialise`, never in prose.
- [ ] 1.3 Bring the report's opening ("Three arms") and closing ("What this does and does not
      show") up to the registered run. Rule-withheld and the six-pretext ladder answer two of
      its caveats. State what still holds: the pretexts are fixed and blunt, they sit in the
      task, and P5 was written after the fact. This is the understating direction, which no
      check catches.
- [ ] 1.4 `make build` green. Commit.

## 2. Corpus plumbing

- [ ] 2.1 `papers/03-generation/proposal.typ`: a title block with no DOI, section skeleton
      labels, and `#let gen = json("/dist/generation.json")` and
      `#let feed = json("/dist/evaluation-feed.json")`.
- [ ] 2.2 `Makefile`: Paper 3 targets to `dist/papers/03-generation/proposal.{pdf,md,html}`
      and the citable `lavi-<year>-<slug>.pdf`, depending on both JSON artifacts. Add it to
      `build`.
- [ ] 2.3 `citations.bib`: Paper 2's entry with its reserved DOI.
- [ ] 2.4 `scripts/check-corpus-citations.py` (design, "the stamp check"), with tests:
      - a stamped paper citing an unpublished corpus paper fails;
      - an unstamped one passes;
      - a Lavi/Zenodo entry mapping to no paper fails;
      - Paper 2 as it stands passes.

      Wire it into `make build` and pre-commit.
- [ ] 2.5 `prepare-paper-2-publication/publication-checklist.md`: commit
      `papers/02-demonstrator/RECORD.json` at upload.
- [ ] 2.6 `papers/README.md` table row; `AGENTS.md` key-files row and Paper 3's structure;
      `docs/ROADMAP.md` (M5 started). `make build` green. Commit.

## 3. Survey before writing related work

- [ ] 3.1 Survey work on LLMs complying with claimed authority or approval (social-engineering
      prompt injection), and studies of the security of LLM-written code. Ask what should change
      in the design or the claim, not only who to cite. Record the result in
      `docs/PRIOR-ART.md`. Verify every new citation against its source before adding it.

## 4. Writing, section by section

After each section: `make build`, the word count against the budget, and a commit. Each section
must interpolate every figure.

- [ ] 4.1 §2 Setting, written first, because it fixes what is cited from Paper 2 and what is
      restated (nothing)
- [ ] 4.2 §3 Method
- [ ] 4.3 §4 Results
- [ ] 4.4 §5 The service
- [ ] 4.5 §7 Limitations, checked against "What is not negotiable", item by item
- [ ] 4.6 §6 Related work
- [ ] 4.7 §1 Introduction and claim block; §8; §9; abstract (magnitudes and counts interpolated)
- [ ] 4.8 Hedge pins for Paper 3 in `scripts/check-hedges.py`: claim and qualification as one
      fragment, for the claim block, the ladder, rule withheld, differential "equal", and
      replay. A regression guard over those passages, and described as no more than that.
- [ ] 4.9 Word count per section against the budget. Report any miss with its reason.

## 5. Review

- [ ] 5.1 A critical review of the whole draft, in the `review-proposal` discipline. Check for
      overstating, understating, pooled trials, causal verbs on descriptive steps, and any
      Paper 2 figure typed by hand. Fix and commit each round.
- [ ] 5.2 Cross-check every citation of a Paper 2 section against Paper 2 as it stands.

## 6. The author's read, then publication

Each step from 6.2 on is outward-facing or follows one, and needs an explicit go.

- [ ] 6.1 The author's end-to-end read
- [ ] 6.2 Paper 2 published, and its `RECORD.json` committed. The stamp check now allows
      stamping Paper 3.
- [ ] 6.3 The author reserves Paper 3's DOI. Stamp it, with the slug's year.
- [ ] 6.4 Pin the `dist/generation.json` and `dist/evaluation-feed.json` keys Paper 3 typesets,
      as `tests/test_paper2_figures_pinned.py` does for Paper 2
- [ ] 6.5 Upload, on the author's explicit go. Commit `RECORD.json`.
- [ ] 6.6 `openspec archive add-paper-3 --yes`
