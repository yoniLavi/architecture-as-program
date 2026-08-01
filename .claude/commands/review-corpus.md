Please perform a whole-corpus review: the cross-paper consistency pass, the staleness sweep, and a strategic assessment of what to do next. This is the wide-angle complement to `/review-proposal` (one paper, deep) and `/tighten-proposal` (one paper, surface): it reads everything, checks the seams *between* the artifacts, and ends with a sequencing recommendation the author can act on.

`$ARGUMENTS`, if given, is a strategic question to answer explicitly in the final assessment (e.g. "should we publish now or build M2 first?"). Without one, still end with a recommendation on the highest-value next step.

## Phase 1: Read the whole state

Run `make build` first (fresh `dist/evaluation.json`, freeze guard exercised), then read:

- `docs/ROADMAP.md` — including its "state as of" header, which claims to describe the present
- **Both living papers, end-to-end**: `papers/02-demonstrator/proposal.typ`, `papers/03-method/proposal.typ`
- `docs/PRIOR-ART.md` — especially the **open verification debts** section
- `papers/README.md` and `AGENTS.md` — the corpus rules the papers must obey
- `openspec/changes/` — active (unarchived) change proposals
- Recent `git log --oneline` (~20 commits) — what has landed since the papers were last read end-to-end
- Paper 1 only as needed for cross-reference (it is frozen; findings about it become proposed `ERRATA.md` entries, never edits)

## Phase 2: The seam checks

These target the bug classes that single-paper review misses because each instance looks locally fine. Check every one; each has produced (or nearly produced) a real shipped defect.

### One owner per number
- Paper 3 interpolates **no** data — every figure it refers to must be cited to Paper 2. Any measurement stated in Paper 3's own voice violates the rule.
- Every figure in Paper 2 §4 must be interpolated (`#ev`/`#d`) from `dist/evaluation.json`. A hand-typed number sitting beside interpolated ones is a defect *even if currently correct*.
- **Hand-written counts vs the tables they summarise.** Paper 3's abstract/§4/conclusion counts vs `tab:outcomes` (must also sum to the stated number of predictions); any "N of M nodes" prose in Paper 2 vs the data. This exact bug shipped once — statuses were reclassified and three prose sites kept the old counts.

### Staleness after artifact growth
- Prose written before the latest artifact changes: grep the limitations and evaluation sections for quantified claims ("two nodes", "four kinds", "N tests") and verify each against the current artifact.
- `AGENTS.md`'s recorded counts (tests, corpus cases, capability kinds) vs actual — it briefs every future session, and it has drifted before.
- `docs/ROADMAP.md`'s header vs reality: archived changes still listed as pending, done items still in the gap table.

### The cross-paper contract
- Paper 2 §5 has not grown into a second accounting; the outcomes table lives in Paper 3 only.
- What each paper says about the other (title-block notes, relation sections) is still true.
- Demos: a mention, never a section; absent from contributions; no Paper 3 verdict moved by a demo.
- Hedging parity: a claim conditional in one paper must not appear factual in the other.
- Shared `citations.bib`: run `scripts/check-citations.py`; confirm no paper-specific orphans.

### Verification debts vs published text
- For each open debt in `docs/PRIOR-ART.md`, grep both living papers: a debt whose claim **appears in a paper's text** is a publication blocker; a debt confined to the survey record is post-publication work. Say which is which.

## Phase 3: Assessment and strategy

Deliver in this order:

1. **TLDR first** — the recommendation, in two or three sentences, before any supporting detail.
2. **Defects found** — the concrete bugs from Phase 2, each with file:line, ready to fix. These come before opinions.
3. **Per-paper assessment** — brief; strengths named honestly, soft spots with evidence. This is not a full `/review-proposal`; depth belongs there.
4. **Roadmap critique** — ordering tensions (an item that "widens the current paper's lead result" belongs *before* that paper's DOI, not after), scope risks, evaluation-design gaps (e.g. a milestone that implies benchmark comparability it won't deliver), missing threat-model residuals.
5. **Sequencing recommendation** — answer the strategic question. Reason from the corpus's own structure: living papers absorb later improvement (a fundamental rethink is a *new paper*, not a rewrite); DOI order is Paper 2 before Paper 3 (3 cites 2); concurrent-work risk is real and dated (check `docs/PRIOR-ART.md`'s closest-work entries); the only work worth gating a publication on is work that changes what the paper can *claim*. Distinguish "strengthens the current paper" from "belongs to the next artifact" for every candidate work item.

## Important guidance

- **Findings before opinions.** A strategic recommendation earns trust by riding on verified concrete findings, not instead of them.
- **Verify before flagging.** Hedging and limitations are deliberate and may sit sentences away from the claim; the designated homes (Paper 2 §5/§7, Paper 3 §5–§6) cover most known limits. False positives erode trust.
- **Check provenance, not arithmetic.** For any number, ask "who owns this?" before "is it right?".
- **Be concrete about costs.** When recommending sequencing, estimate the size of each option (a scoped OpenSpec change vs a milestone vs a paper cycle) rather than ranking abstractions.
- **Respect the freeze.** Paper 1 findings → proposed errata entries only.

Do NOT make any changes during the review. Present it for discussion — the author decides the sequencing, and implementation (fixes, then any pulled-forward change) follows their call.
