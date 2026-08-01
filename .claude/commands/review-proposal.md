Please perform a full critical review of one of this repository's living papers.

**Which paper:** `$ARGUMENTS` — accept `2` (or `demonstrator`) for Paper 2, `3` (or `method`) for Paper 3. If no argument is given, review **Paper 2** (`papers/02-demonstrator/proposal.typ`), the default meaning of "the proposal" in this repo. Paper 1 (`papers/01-vision/`) is **frozen and never reviewed for change** — it may be read for cross-reference, and any genuine error found in it becomes a proposed entry for `papers/01-vision/ERRATA.md`, not an edit. For the whole-corpus pass (both papers plus roadmap and strategy), use `/review-corpus` instead.

## Phase 1: Read everything

Run `make build` first so `dist/evaluation.json` is fresh, then read in parallel:

- The paper under review (`papers/02-demonstrator/proposal.typ` or `papers/03-method/proposal.typ`)
- The *other* living paper, for the cross-paper contract (below) — skim, don't deep-review
- `citations.bib` (shared bibliography — an entry is "used" if *any* paper cites it)
- `AGENTS.md` (repo context; includes the editing rules and the current test counts)
- `papers/README.md` (how the corpus is organised; living vs frozen)
- `docs/PRIOR-ART.md` (the survey record — what was taken, refused, and the open verification debts)
- `Makefile` and `.pre-commit-config.yaml` (build pipeline)
- All scripts in `scripts/`
- All graph definitions in `graphs/` — treat these as reviewable design artifacts, not support files. Check that type names, variants, capability annotations, and edge-port names in the prose match the JSON.
- `dist/evaluation.json` — the single source of every figure Paper 2's §4 states

## Phase 2: Evaluate the paper

Assess on each dimension. For each, give a clear judgement (strong / adequate / weak) with specific evidence (quote lines, name sections):

### Argument
- Is the central claim (Paper 2 §1.1 / Paper 3 §1.1) clearly stated, falsifiable, and matched by what the evidence sections actually deliver?
- Does each section build on the previous, or are there logical gaps?
- Paper 2: does the lead result (capability-surface derivation, §3.3.2) stay the lead throughout — abstract, contributions, evaluation, conclusion?
- Paper 3: does the accounting stay accounting — verdicts traceable to the frozen text's claims, corrections traceable to the artifact?

### Prior art
- Is the literature survey accurate and fairly positioned? Cross-check against `docs/PRIOR-ART.md` — a contrast stated in the paper that PRIOR-ART lists as an **open verification debt** is a publication blocker; flag it.
- Are there significant missing references that would strengthen or challenge the argument?
- Paper 2 §6.1 (LLM-agent security) is load-bearing: any prompt-injection claim must position against CaMeL, TACIT, Greshake, AgentDojo, and the pattern catalogue.

### Technical claims
- Are claims appropriately hedged relative to what has actually been built? The two traps specific to Paper 2's form: (a) §2 describes intent in a paper otherwise written in the present tense, so an unproven claim reads as substantiated unless its mood is deliberately conditional; (b) a property that holds only on the **confined tier** must say so, or it reads as universal while the host tier demonstrably escapes.
- Is anything asserted about the type system that does not exist? (Conditional vocabulary: *"would"*, *"in a sound realisation"*, *"in a well-typed realisation"*.)
- Do the concrete graphs (CustomerSupport, SupportPlatform) still carry the argument, or has the artifact outgrown them?

### Numbers and interpolation discipline
- **Never check arithmetic by eye against the prose — check provenance.** Every figure in Paper 2 §4 must be interpolated (`#ev` / `#d`) from `dist/evaluation.json`; a hand-typed number adjacent to interpolated ones is a defect even if currently correct (this class of bug has occurred: hand-typed counts drifting after the data moved).
- Paper 3 interpolates **no** data: every figure it mentions must be cited to Paper 2. Any number stated in Paper 3's own voice is a violation of the one-owner-per-number rule.
- Paper 3's prose counts (abstract, §4 opening, conclusion) must agree with `tab:outcomes` and sum to the stated number of predictions. This exact bug has shipped once; check it every time.

### Cross-paper contract
- Paper 2 §5 ("What this establishes") must not have grown into a second accounting — the predictions-and-outcomes table lives in Paper 3 *only*.
- Statements each paper makes about the other (title-block notes, §1.3/§5 cross-references) must still be accurate.
- Demos (the inspector, and successors) get **a mention, never a section**, stay out of the contributions list, and never move a Paper 3 verdict.

### Completeness
- Are limitations honestly acknowledged in the right home? Paper 2: honest limits in §7.1–§7.4, bounding open problems in §7.5; Paper 3: threats in §6, forward agenda in §5. A gap you identify should usually be proposed as an addition there, not only flagged in-section.
- Paper 2: is the two-tier story (migration path, host-tier gap recorded as passing tests) intact?

### Presentation
- Is the abstract effective (and, for Paper 2, not so dense it buries the lead)?
- Is the length right? Paper 2's working target is roughly the low-to-mid 30s of pages; each load-bearing point has one primary home and is cross-referenced elsewhere, not restated.
- Structural or readability issues; the AI-collaboration note's accuracy.

### Tooling
- Does the build pipeline work? Run `make build` and `scripts/check-citations.py`. Confirm the freeze guard passes and the paper's figures regenerate.

## Phase 3: Recommendations

Present findings as a prioritised list. For each recommendation:
- **What:** the specific problem, with file and line numbers
- **Why it matters:** impact on credibility or clarity
- **Suggested fix:** concrete enough to act on

Separate into:
1. **Must fix before publishing** — issues that would cause informed readers to dismiss the paper, or that violate the corpus's own stated rules (interpolation discipline, one owner per number, no second accounting)
2. **Should fix** — issues that weaken the argument but don't break it
3. **Nice to have** — polish items

## Important guidance

- **Verify before flagging hedging.** The hedging vocabulary is deliberate and may sit several sentences from the claim it qualifies. Grep for the conditional patterns nearby before flagging.
- **Check the designated homes before flagging a gap.** Paper 2's §7 and Paper 3's §5–§6 cover most known limits; a "missing limitation" that is present there is a false positive.
- **Build the project.** Actually run `make build` and `scripts/check-citations.py`; use `scripts/validate-bib.py` if bibliographic accuracy is in doubt. Don't just read the Makefile.
- **Be concrete.** Every recommendation should include file:line and a fix implementable without further discussion.
- **Verify factual claims before reporting.** Author names, years, venues → check the PDFs in `refs/` first, then `scripts/validate-bib.py`, then web search. Claims about what a cited paper says → read the PDF in `refs/` before disputing. Don't list unverified suspicions; silence is better than a false flag.
- **Terminology drift.** If you propose a rename, list every location needing updating: both living papers' prose, graph JSON, figure captions, generated diagrams, and (if applicable) WIT/`poc` identifiers. Incomplete renames are worse than the original issue.

Do NOT make any changes during the review itself. Present the review for discussion first.

## If asked to address the findings afterwards

- Work in priority order: must-fix first.
- Use `TaskCreate` to track progress across items when there are more than a few.
- After edits, run `make build` (catches broken refs, freeze drift, evaluation-pin divergence) and `scripts/check-citations.py`.
- Do a consistency sweep before reporting done: terminology propagated everywhere, cross-paper statements still true, prose counts still matching tables.
- Report what changed, grouped by the review's priority tiers.
