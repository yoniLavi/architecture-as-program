Please perform a tightening review of one of this repository's living papers. The papers have been through multiple review cycles and are near-final. The goal now is to find small, safe improvements — not to expand scope.

**Which paper:** `$ARGUMENTS` — accept `2` (or `demonstrator`) for Paper 2, `3` (or `method`) for Paper 3. If no argument is given, tighten **Paper 2** (`papers/02-demonstrator/proposal.typ`). Paper 1 is **frozen**: never tighten it; a genuine error there is a proposed `ERRATA.md` entry, nothing more.

## Phase 1: Read everything

Read in parallel:
- The paper under review
- The other living paper (skim — needed to check cross-paper statements and to avoid recommending a cut whose content is *supposed* to live here rather than there)
- `citations.bib`
- `AGENTS.md` (the editing rules — especially the tightness conventions and hedging vocabulary)

## Phase 2: Review for tightening

Focus exclusively on these dimensions:

### Internal consistency
- Are claims hedged differently in different places? The hedging vocabulary ("would be", "in a well-typed realisation", "in a sound realisation of the type system") must be used equivalently for equivalent claims — no claim hedged in one place and stated as fact in another.
- Do body claims contradict the designated limits sections (Paper 2 §5/§7; Paper 3 §6)?
- Are citations used correctly (right claim attributed to right source)?
- Do the concrete graph examples match their prose descriptions and figure captions?
- Do prose counts match the tables they summarise? (Paper 3's outcome counts vs `tab:outcomes` is the known instance of this bug class — check it.)
- Are statements about the *other* paper (title-block note, cross-references) still accurate?

### Overstatement
- Properties of the unbuilt type system asserted without conditional language?
- Confined-tier-only properties stated as if universal (the host tier demonstrably escapes)?
- Unsupported empirical claims (trends stated without evidence)?
- Demos given more than a mention (they never get a section, never enter the contributions list)?

### Redundancy and verbosity
- The repo's rule is **one primary home per load-bearing point, cross-referenced elsewhere** (e.g. the free-text residual lives in §4.3, the trust-lattice mechanism in §3.2). Flag any second full explanation; the fix is to cut it down to a cross-reference to the primary home.
- Sentences or paragraphs that repeat a point already made.
- Passages that could be shortened without losing meaning; anything a reviewer could reasonably ask to be cut.
- Prior-art descriptions must earn their length through the positioning work they do (the gap statement at the end).
- Paper 2's working length target is roughly the low-to-mid 30s of pages. It is a target, not a quota: **never recommend cutting a stated limitation, a hedge, or (in Paper 3) the predictions-and-outcomes table** to hit it.

### Surface quality
- Typos, grammar, awkward phrasing, inconsistent terminology.
- Formatting issues in the Typst source.

## Phase 3: Recommendations

**Constraints on recommendations:**
- Do NOT suggest adding new sections, subsections, or prior-art references.
- Do NOT suggest expanding existing sections or adding detail.
- Do NOT touch interpolated figures (`#ev` / `#d` expressions): a wrong-looking number there is a `poc/evaluate.py` serialiser question, not a prose edit — flag it separately if suspected, don't "fix" the text.
- Every recommendation must be self-contained: implementing it should not open new questions or require follow-up changes elsewhere.
- Prefer cuts and rewrites over additions. The paper should not get longer.

**Classify each recommendation:**
- **Safe fix:** corrects an error or inconsistency without changing any claim. Unlikely to draw reviewer attention.
- **Judgement call:** improves the text but touches framing, scope, or emphasis. Could open new questions.

Present findings as a flat prioritised list. For each recommendation:
- **What:** the specific problem, with line numbers
- **Classification:** safe fix or judgement call
- **Why it matters:** impact on credibility or clarity
- **Suggested fix:** concrete, minimal, and unlikely to prompt further review concerns

## Important guidance

- **Verify before flagging.** Re-read the surrounding context before calling something a hedging gap or inconsistency — the qualifier may sit in the preceding or following sentence. False positives waste the author's time and erode trust in the review.
- **Check the designated limits sections** (Paper 2 §5/§7, Paper 3 §5–§6) before flagging an unacknowledged limitation.
- **Build the project.** Run `make build` to check for broken references, citation issues, freeze drift, and evaluation-pin divergence.
- **Verify factual claims.** Suspected factual errors (author name, date, claim about prior work): check the PDFs in `refs/` or do a quick web search before flagging. Only report confirmed errors.

**If the paper is clean enough that remaining issues are all judgement calls, say so.** A "no safe fixes remain" result is a valid and useful outcome.

Do NOT make any changes. Present the review for discussion first.
