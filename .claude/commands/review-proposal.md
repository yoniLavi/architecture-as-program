Please perform a full critical review of this repository's living paper.

**Which paper:** `$ARGUMENTS` — `2` (or `demonstrator`), or no argument: **Paper 2** (`papers/02-demonstrator/proposal.typ`), the only living paper and the meaning of "the proposal" in this repo. (A former Paper 3, the method paper, was merged into it in September 2026; if `3` is passed, say so and review Paper 2.) Paper 1 (`papers/01-vision/`) is **frozen and never reviewed for change** — it may be read for cross-reference, and any genuine error found in it becomes a proposed entry for `papers/01-vision/ERRATA.md`, not an edit. For the whole-corpus pass (the paper plus roadmap and strategy), use `/review-corpus` instead.

**Run this in a fresh session.** A review is worth most from a reader who did not write the text. If this session drafted or rewrote the paper, say so at the top of the report, and suggest re-running the review in a fresh session instead.

## Phase 1: Read everything

Run `make clean && make build` first, so `dist/evaluation.json` and the rendered copies are fresh. Then establish **what changed since the last review**: run `git log --oneline -- papers/02-demonstrator/proposal.typ`, find the most recent review-fix commit (its message says so), and diff against it. If the diff is large — a rewrite, a merge, or a condensation — also fetch the earlier text (`git show <commit>:papers/02-demonstrator/proposal.typ`, or a tag such as `paper-3-before-merge`) for the lost-qualification check in Phase 2.

Then read in parallel:

- The paper under review (`papers/02-demonstrator/proposal.typ`)
- Paper 1 (`papers/01-vision/proposal.typ`), for the accounting in §5 — skim, don't deep-review
- `citations.bib` (shared bibliography — an entry is "used" if *any* paper cites it)
- `AGENTS.md` (repo context; includes the editing rules and the current test counts)
- `papers/README.md` (how the corpus is organised; living vs frozen)
- `docs/PRIOR-ART.md` (the survey record — what was taken, refused, and the open verification debts)
- `Makefile` and `.pre-commit-config.yaml` (build pipeline)
- All scripts in `scripts/`
- All graph definitions in `graphs/` — treat these as reviewable design artifacts, not support files. Check that type names, variants, capability annotations, and edge-port names in the prose match the JSON.
- `dist/evaluation.json` — the single source of every figure Paper 2's §4 states
- `papers/01-vision/ERRATA.md` and `papers/01-vision/PUBLISHED.json` — the dated record of Paper 1's freeze, revision, and publication, against which §5's account of the protocol is checked
- The rendered copies `dist/papers/02-demonstrator/proposal.{md,html}` — skim them, don't reread them. They are built by pandoc, not typst, so a defect can live there while the PDF is right

## Phase 2: Evaluate the paper

Assess on each dimension. For each, give a clear judgement (strong / adequate / weak) with specific evidence (quote lines, name sections):

### Argument
- Is the central claim (§1.1) clearly stated, falsifiable, and matched by what the evidence sections actually deliver?
- Does each section build on the previous, or are there logical gaps?
- Does the lead result (capability-surface derivation, §3.2.1) stay the lead throughout — abstract, contributions, evaluation, conclusion — with the accounting (§5) supporting it rather than competing with it?
- Does §5 stay accounting — verdicts traceable to Paper 1's frozen text, corrections traceable to the artifact?

### Prior art
- Is the literature survey accurate and fairly positioned? Cross-check against `docs/PRIOR-ART.md` — a contrast stated in the paper that PRIOR-ART lists as an **open verification debt** is a publication blocker; flag it.
- Are there significant missing references that would strengthen or challenge the argument?
- Paper 2 §6.1 (LLM-agent security) is load-bearing: any prompt-injection claim must position against CaMeL, TACIT, Greshake, AgentDojo, and the pattern catalogue.

### Technical claims
- Are claims appropriately hedged relative to what has actually been built? The two traps specific to Paper 2's form: (a) §2 describes intent in a paper otherwise written in the present tense, so an unproven claim reads as substantiated unless its mood is deliberately conditional; (b) a property that holds only on the **confined tier** must say so, or it reads as universal while the host tier demonstrably escapes.
- Is anything asserted about the type system that does not exist? (Conditional vocabulary: *"would"*, *"in a sound realisation"*, *"in a well-typed realisation"*.)
- Do the concrete graphs (CustomerSupport, SupportPlatform) still carry the argument, or has the artifact outgrown them?
- **Summary sites shed qualifiers.** The abstract, the contributions, §5's verdict notes, and the conclusion each restate claims made in the body. For every claim at a summary site, find its body statement, and check that the summary keeps the body's qualifier (confined tier only, checked not verified, bound but not typed, attenuated not eliminated). A qualifier that survives in the body and vanishes from the conclusion is the most common overstatement this paper has shipped.
- **Lost qualifications after a rewrite.** If Phase 1 found a large diff, go through the earlier text's limits and hedges, and confirm that each one is still present where it bounds the same claim. Quote the old qualifier and the new unbounded sentence. The hedge guard (`scripts/check-hedges.py`) covers only its pinned passages in §2.3–§2.4, so everything else rests on this check.

### Numbers and interpolation discipline
- **Never check arithmetic by eye against the prose — check provenance.** Every figure in Paper 2 §4 must be interpolated (`#ev` / `#d`) from `dist/evaluation.json`; a hand-typed number adjacent to interpolated ones is a defect even if currently correct (this class of bug has occurred: hand-typed counts drifting after the data moved).
- Verdict counts (abstract, conclusion) must be computed with `verdicts(...)` from the `outcomes` array, never typed. A hand-typed count has shipped wrong once; check that none has crept back.
- **Hand-maintained statements about the data that are not numbers**: "the one row whose graph does not ship", "both graphs", "every node but `ReceiveMessage`". Each one is correct today and drifts silently when the data moves. Where an interpolation exists, propose it; otherwise mark it nice-to-have.

### Corpus contract
- Statements about Paper 1 (title-block note, §5) must be accurate, and the paper must cite no unpublished work.
- **Claims about the corpus's own history are factual claims, so verify them.** Dates and orderings — what was frozen, built, revised, and published, and when — go wrong in a way a reader can check against a DOI date, which discredits the whole accounting. Verify each against `git log` (for example, the first commit under `poc/`), `ERRATA.md`, and `PUBLISHED.json`. A merge once spread "published and frozen before any of it was built" to five sites, but only the *freeze* preceded the build — and the fix then kept "frozen before any of it was built", though a validator running early forms of §3.1's analyses already existed at the freeze commit. Check what the tree held *at the freeze commit* (`git ls-tree`), not only when `poc/` first appears; the accurate phrase is "before the *executable* demonstrator".
- Demos (the inspector, and successors) get **a mention, never a section**, stay out of the contributions list, and never move a §5 verdict.

### Completeness
- Are limitations honestly acknowledged in the right home? Honest limits in §7.1–§7.5, bounding open problems in §7.6, the forward programme in §8. A gap you identify should usually be proposed as an addition there, not only flagged in-section.
- Paper 2: is the two-tier story (migration path, host-tier gap recorded as passing tests) intact?

### Presentation
- Is the abstract effective (and, for Paper 2, not so dense it buries the lead)?
- Is the length right? The approved budget is ~12,000 words (see AGENTS.md); each load-bearing point has one primary home and is cross-referenced elsewhere, not restated.
- Structural or readability issues; the AI-collaboration note's accuracy.

### Tooling
- Does the build pipeline work? Run `make build` and `scripts/check-citations.py`. Confirm the freeze guard passes and the paper's figures regenerate.
- **Do the rendered copies resolve?** Grep `dist/papers/02-demonstrator/proposal.md` and `.html` for unresolved references — `§` followed by a letter, `Table`/`Figure` followed by a label rather than a number, and `[sec]`, `[tab]`, `[fig]` — and for any figure the PDF shows but the copies drop. Every section reference once rendered as its bare label (`§open`) for weeks, because only the PDF was being read.

## Phase 3: Recommendations

Present findings as a prioritised list. For each recommendation:
- **What:** the specific problem, with file and line numbers
- **Why it matters:** impact on credibility or clarity
- **Suggested fix:** concrete enough to act on. Where the fix is a sentence or less, give the exact replacement text.

**One defect at several sites is one finding**, listing every line number. Do not scatter it across tiers.

Separate into:
1. **Must fix before publishing** — issues that would cause informed readers to dismiss the paper (a factual error, including one about the corpus's own history), or that violate the corpus's own stated rules (interpolation discipline, computed verdict counts, hedging and confined-tier scoping, no citation of unpublished work)
2. **Should fix** — issues that weaken the argument but don't break it
3. **Nice to have** — polish items

## Important guidance

- **Verify before flagging hedging.** The hedging vocabulary is deliberate and may sit several sentences from the claim it qualifies. Grep for the conditional patterns nearby before flagging.
- **Check the designated homes before flagging a gap.** §5 and §7 cover most known limits; a "missing limitation" that is present there is a false positive.
- **Build the project.** Actually run `make build` and `scripts/check-citations.py`; use `scripts/validate-bib.py` if bibliographic accuracy is in doubt. Don't just read the Makefile.
- **Be concrete.** Every recommendation should include file:line and a fix implementable without further discussion.
- **Verify factual claims before reporting.** Author names, years, venues → check the PDFs in `refs/` first, then `scripts/validate-bib.py`, then web search. Claims about what a cited paper says → read the PDF in `refs/` before disputing. Don't list unverified suspicions; silence is better than a false flag.
- **Minimal fixes, not re-expansion.** The author's rule is to say more with fewer words. A lost qualifier comes back as a clause, not a paragraph, and length alone is never a finding.
- **Terminology drift.** If you propose a rename, list every location needing updating: the paper's prose, graph JSON, figure captions, generated diagrams, and (if applicable) WIT/`poc` identifiers. Incomplete renames are worse than the original issue.

Do NOT make any changes during the review itself. Present the review for discussion first.

## If asked to address the findings afterwards

- Work in priority order: must-fix first.
- Use `TaskCreate` to track progress across items when there are more than a few.
- After edits, run `make build` (catches broken refs, freeze drift, evaluation-pin divergence, and lost hedge pins) and `scripts/check-citations.py`.
- Do a consistency sweep before reporting done: terminology propagated everywhere, statements about Paper 1 still true, prose counts still matching tables, and the same fix applied at every site of a repeated defect (grep for the phrase you corrected).
- Commit the fixes with a message that says they are review fixes, so the next review's "what changed since the last review" step can find the commit.
- Report what changed, grouped by the review's priority tiers.
