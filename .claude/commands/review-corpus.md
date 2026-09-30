Please perform a whole-corpus review: the consistency pass across the paper, its frozen predecessor, the docs, and the build, then the staleness sweep, and a strategic assessment of what to do next. This is the wide-angle complement to `/review-proposal` (one paper, deep) and `/tighten-proposal` (one paper, surface): it reads everything, checks the seams *between* the artifacts, and ends with a sequencing recommendation the author can act on.

`$ARGUMENTS`, if given, is a strategic question to answer explicitly in the final assessment (e.g. "should we publish now or build M2 first?"). Without one, still end with a recommendation on the highest-value next step.

## Phase 1: Read the whole state

Run `make clean && make build` first (fresh `dist/evaluation.json` and rendered copies, freeze guard exercised), then read:

- `docs/ROADMAP.md` — including its "state as of" header, which claims to describe the present
- **The living paper, end-to-end**: `papers/02-demonstrator/proposal.typ` (since September 2026 it also carries the accounting that the former Paper 3 held)
- `docs/PRIOR-ART.md` — especially the **open verification debts** section
- `papers/README.md` and `AGENTS.md` — the corpus rules the papers must obey
- `openspec/changes/` — active (unarchived) change proposals
- Recent `git log --oneline` (~20 commits) — what has landed since the papers were last read end-to-end
- Paper 1 only as needed for cross-reference (it is frozen; findings about it become proposed `ERRATA.md` entries, never edits)

## Phase 2: The seam checks

These target the bug classes that single-paper review misses because each instance looks locally fine. Check every one; each has produced (or nearly produced) a real shipped defect.

### Numbers and their sources
- Every figure in Paper 2 §4 must be interpolated (`#ev`/`#d`) from `dist/evaluation.json`. A hand-typed number sitting beside interpolated ones is a defect *even if currently correct*.
- **Hand-written counts vs the tables they summarise.** Verdict counts must come from `verdicts(...)` over the `outcomes` array, never be typed; any "N of M nodes" prose vs the data. This exact bug shipped once — statuses were reclassified and three prose sites kept the old counts — which is why the counts are now computed.

### Staleness after artifact growth
- Prose written before the latest artifact changes: grep the limitations and evaluation sections for quantified claims ("two nodes", "four kinds", "N tests") and verify each against the current artifact.
- `AGENTS.md`'s recorded counts (tests, corpus cases, capability kinds) vs actual — it briefs every future session, and it has drifted before.
- `docs/ROADMAP.md`'s header vs reality: archived changes still listed as pending, done items still in the gap table.
- **Section numbers quoted outside the paper.** `AGENTS.md`, `docs/ROADMAP.md`, the `.claude/commands/` files, and `scripts/` comments cite "§3.2.1" and the like. Check each against the current numbering, which a restructure moves wholesale. `docs/PRIOR-ART.md` is a dated record and keeps its historical numbers under a mapping note at its top; check that the note covers every number it uses, rather than rewriting the entries.

### The history the corpus tells about itself
- Every claim about what was frozen, built, revised, or published, and in what order — in the paper, `AGENTS.md`, the READMEs, and `METHODOLOGY.md` — is checked against `git log` (for example, the first commit under `poc/`), `papers/01-vision/ERRATA.md`, and `PUBLISHED.json`. This seam has shipped a real error: "published and frozen before any of it was built", when only the freeze preceded the build.

### The two renderers
- The PDF is built by typst, while the Markdown and HTML are built by pandoc through `scripts/resolve-crossrefs.lua`, so a toolchain upgrade can break one and not the other. Grep the rendered `.md`/`.html` for unresolved references (`§` followed by a letter, `Table`/`Figure` followed by a label, `[sec]`), and spot-check that the tables and the process note survive. Every section reference once rendered as `§open` for weeks.

### The corpus contract
- What Paper 2 says about Paper 1 (title-block note, §5) is still true, and it cites no unpublished work.
- Demos: a mention, never a section; absent from contributions; no §5 verdict moved by a demo.
- Hedging parity: a claim conditional in Paper 1 must not appear factual in Paper 2 unless the artifact backs it, and then §5's verdict must say so.
- Shared `citations.bib`: run `scripts/check-citations.py`; confirm no orphans.

### Verification debts vs published text
- For each open debt in `docs/PRIOR-ART.md`, grep the living paper: a debt whose claim **appears in a paper's text** is a publication blocker; a debt confined to the survey record is post-publication work. Say which is which.

## Phase 3: Assessment and strategy

Deliver in this order:

1. **TLDR first** — the recommendation, in two or three sentences, before any supporting detail.
2. **Defects found** — the concrete bugs from Phase 2, each with file:line, ready to fix. These come before opinions.
3. **Per-paper assessment** — brief; strengths named honestly, soft spots with evidence. This is not a full `/review-proposal`; depth belongs there.
4. **Roadmap critique** — ordering tensions (an item that "widens the current paper's lead result" belongs *before* that paper's DOI, not after), scope risks, evaluation-design gaps (e.g. a milestone that implies benchmark comparability it won't deliver), missing threat-model residuals.
5. **Sequencing recommendation** — answer the strategic question. Reason from the corpus's own structure: living papers absorb later improvement (a fundamental rethink is a *new paper*, not a rewrite); a published paper cites no unpublished work, so a later paper waits for anything it cites; concurrent-work risk is real and dated (check `docs/PRIOR-ART.md`'s closest-work entries); the only work worth gating a publication on is work that changes what the paper can *claim*. Distinguish "strengthens the current paper" from "belongs to the next artifact" for every candidate work item.

## Important guidance

- **Findings before opinions.** A strategic recommendation earns trust by riding on verified concrete findings, not instead of them.
- **Verify before flagging.** Hedging and limitations are deliberate and may sit sentences away from the claim; the designated homes (Paper 2 §5 and §7) cover most known limits. False positives erode trust.
- **Check provenance, not arithmetic.** For any number, ask "who owns this?" before "is it right?".
- **Be concrete about costs.** When recommending sequencing, estimate the size of each option (a scoped OpenSpec change vs a milestone vs a paper cycle) rather than ranking abstractions.
- **Respect the freeze.** Paper 1 findings → proposed errata entries only.

Do NOT make any changes during the review. Present it for discussion — the author decides the sequencing, and implementation (fixes, then any pulled-forward change) follows their call.
