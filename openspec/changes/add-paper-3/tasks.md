# Tasks

Every session working on this change first checks the feed recorder (standing task 0.3 of
`strengthen-generation-evidence`) and `git status`.

## 0. Approval

- [x] 0.1 **The author approves this proposal**: the claim block, budget, title, directory and
      stamp check. No paper text is written before this. **Approved 29 October 2026** ("yes,
      please proceed"), with `papers/03-generation/` as proposed. The working title stays
      provisional until the author's read. The author will review and publish Paper 2 first,
      then return to Paper 3.

## 1. The evidence, made quotable

Before any edit under `poc/`, confirm no generation run or replay is in progress. A run imports
the working tree.

- [x] 1.1 `poc/generation/report.py`: a `display` block in `dist/generation.json` holding
      pre-formatted strings for every non-integer figure Paper 3 will use. The confirmatory
      p-value is the first of them. **Done (`e04ff6b`)**: `display.confirmatory_p`, with
      `scientific()` tested. That typst and pandoc render it identically was checked by hand
      in the built PDF and Markdown (both `1.1 × 10⁻⁴⁰`), not by a test: see 1.1a
- [ ] 1.1a A test that the PDF and Markdown renderings state the same `display` strings. It
      needs pandoc and typst, so it is skipped without them, like `test_resolve_crossrefs.py`
- [x] 1.2 Serialise any count Paper 3 states that the JSON only implies, for example caught
      components that would not have shipped. It is computed in `serialise`, never in prose.
      Done: `registered.no_claim` and `registered.gate_off`
- [x] 1.3 Bring the report's opening ("Three arms") and closing ("What this does and does not
      show") up to the registered run. Rule-withheld and the six-pretext ladder answer two of
      its caveats. State what still holds: the pretexts are fixed and blunt, they sit in the
      task, and P5 was written after the fact. This is the understating direction, which no
      check catches. The rule-withheld caveat's direction is computed from the data
- [x] 1.4 `make build` green. Commit (`e04ff6b`)

## 2. Corpus plumbing

- [x] 2.1 `papers/03-generation/proposal.typ`: a title block with no DOI, section labels, and
      `#let gen = json("/dist/generation.json")` and
      `#let feed = json("/dist/evaluation-feed.json")`.
- [x] 2.2 `Makefile`: Paper 3 targets to `dist/papers/03-generation/proposal.{pdf,md,html}`
      and the citable `lavi-2026-granted-by-claim.pdf`, depending on both JSON artifacts, in
      `build`. The slug follows the working title and changes with it.
- [x] 2.3 `citations.bib`: Paper 2's entry with its reserved DOI.
- [x] 2.4 `scripts/check-corpus-citations.py` (design, "the stamp check"), with tests:
      - a stamped paper citing an unpublished corpus paper fails;
      - an unstamped one passes;
      - a Lavi/Zenodo entry mapping to no paper fails;
      - Paper 2 as it stands passes.

      Wired into `make build` and pre-commit.
- [x] 2.5 `prepare-paper-2-publication/publication-checklist.md`: commit
      `papers/02-demonstrator/RECORD.json` at upload.
- [x] 2.6 `papers/README.md` table row; `AGENTS.md` key-files rows; `docs/ROADMAP.md` (M5
      started). `make build` green.

## 3. Survey before writing related work

- [x] 3.1 Survey work on LLMs complying with claimed authority or approval (social-engineering
      prompt injection), and studies of the security of LLM-written code. Ask what should change
      in the design or the claim, not only who to cite. Recorded in `docs/PRIOR-ART.md` §§16–19.
      Every new citation was checked against its source; Leong, Progent and Yang et al. were
      re-read against their abstracts by the drafting session. It changed the claim: compliance
      is not ours to claim, and the zero baseline is not generalised.

## 4. Writing, section by section

**A deviation, stated.** The first draft was written whole on 29 October 2026, rather than
committed section by section, because the author asked for the work to proceed while they
turn to Paper 2. Each section was built, counted and checked against "What is not negotiable"
before the commit. Section-level scrutiny happens in the phase 5 review.

- [x] 4.1 §2 Setting: cites Paper 2 for the gate and restates none of it
- [x] 4.2 §3 Method
- [x] 4.3 §4 Results
- [x] 4.4 §5 The service
- [x] 4.5 §7 Limitations, checked against "What is not negotiable", item by item
- [x] 4.6 §6 Related work
- [x] 4.7 §1 Introduction and claim block; §8; §9; abstract (counts interpolated, and every
      qualitative statement about the data computed from it)
- [x] 4.8 Hedge pins for Paper 3 in `scripts/check-hedges.py`: claim and qualification as one
      fragment. A regression guard over those passages, and described as no more than that.
      Seven pins were seeded:
      - the gate catches by construction;
      - the result says nothing about retrieved content;
      - the ladder is not a factorial;
      - "registered" means only that;
      - "equal" is not equivalence;
      - a replay is not operation;
      - the policy is not the validator.

      **Rule withheld is not pinned.** Its wording is computed from the data (`#moved`), so a
      verbatim pin would quote typst code, not a claim.
- [x] 4.9 Word count per section against the budget. First draft: ~4,600 words of body
      against the ~8,000 target (abstract 389, §1 491, §2 387, §3 986, §4 683, §5 388, §6 655,
      §7 414, §8 64, §9 129). Being under the target is allowed. Every non-negotiable limit was
      checked present.

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
