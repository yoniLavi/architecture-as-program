Please perform a tightening review of this repository's living paper. It has been through multiple review cycles and is near-final. The goal now is to find small, safe improvements — not to expand scope.

**Which paper:** `$ARGUMENTS` — `2` (or `demonstrator`), or no argument: **Paper 2** (`papers/02-demonstrator/proposal.typ`), the only living paper. (The former Paper 3 was merged into it in September 2026.) Paper 1 is **frozen**: never tighten it; a genuine error there is a proposed `ERRATA.md` entry, nothing more.

## Phase 1: Read everything

Read in parallel:
- The paper under review
- `citations.bib`
- `AGENTS.md` (the editing rules — especially the tightness conventions and hedging vocabulary)

## Phase 2: Review for tightening

Focus exclusively on these dimensions:

### Internal consistency
- Are claims hedged differently in different places? The hedging vocabulary ("would be", "in a well-typed realisation", "in a sound realisation of the type system") must be used equivalently for equivalent claims — no claim hedged in one place and stated as fact in another.
- Do body claims contradict the designated limits sections (§5 and §7)?
- Are citations used correctly (right claim attributed to right source)?
- Do the concrete graph examples match their prose descriptions and figure captions?
- Do prose counts match the tables they summarise? (Verdict counts must be `verdicts(...)` over `outcomes`, never typed — the known instance of this bug class.)
- Are statements about Paper 1 (title-block note, §5) still accurate, including dates and orderings? Only the *freeze* preceded the build; Paper 1 was published afterwards. Check against `papers/01-vision/ERRATA.md` rather than memory.
- **Do summary sites match the body?** The abstract, contributions, §5's verdict notes, and the conclusion restate body claims. Put each one beside its body statement: the two must say the same thing, with the same qualifier. The failure is usually one-directional, with a summary quietly shedding "on the confined tier" or "checked, not verified".
- **Hand-maintained statements about the data that are not numbers** ("the one row", "both graphs", "every node but X"): flag each where an interpolation exists, as a safe fix.

### Overstatement
- Properties of the unbuilt type system asserted without conditional language?
- Confined-tier-only properties stated as if universal (the host tier demonstrably escapes)?
- Unsupported empirical claims (trends stated without evidence)?
- Demos given more than a mention (they never get a section, never enter the contributions list)?

### Redundancy and verbosity
- The repo's rule is **one primary home per load-bearing point, cross-referenced elsewhere** (e.g. the free-text residual lives in §4.4, the trust-lattice mechanism in §3.1). Flag any second full explanation; the fix is to cut it down to a cross-reference to the primary home.
- Sentences or paragraphs that repeat a point already made.
- Passages that could be shortened without losing meaning; anything a reviewer could reasonably ask to be cut.
- Prior-art descriptions must earn their length through the positioning work they do (the gap statement at the end).
- The approved length budget is ~12,000 words. It is a target, not a quota: **never recommend cutting a stated limitation, a hedge, or a row of the predictions-and-outcomes table** to hit it.

### Surface quality
- Typos, grammar, awkward phrasing, inconsistent terminology.
- **Compression damage.** The paper was condensed from ~27,000 words. Look for sentences that no longer parse, pronouns and "which" clauses whose antecedent was cut, phrasing that became ambiguous ("three of the four correct security claims"), and cross-references that now point at a section that no longer holds what the sentence promises.
- Formatting issues in the Typst source.

## Phase 3: Recommendations

**Constraints on recommendations:**
- Do NOT suggest adding new sections, subsections, or prior-art references.
- Do NOT suggest expanding existing sections or adding detail.
- Do NOT touch interpolated figures (`#ev` / `#d` expressions): a wrong-looking number there is a `poc/evaluate.py` serialiser question, not a prose edit — flag it separately if suspected, don't "fix" the text.
- Every recommendation must be self-contained: implementing it should not open new questions or require follow-up changes elsewhere.
- Prefer cuts and rewrites over additions. The paper should not get longer.
- Mind the hedge guard. `scripts/check-hedges.py` pins verbatim fragments in §2.3 and §2.4 (listed in the script). A rewording that touches a pinned fragment fails the build, so either leave it alone, or classify the change as a judgement call that needs a deliberate re-seed.

**Classify each recommendation:**
- **Safe fix:** corrects an error or inconsistency without changing any claim. Unlikely to draw reviewer attention.
- **Judgement call:** improves the text but touches framing, scope, or emphasis. Could open new questions.

Present findings as a flat prioritised list. For each recommendation:
- **What:** the specific problem, with line numbers
- **Classification:** safe fix or judgement call
- **Why it matters:** impact on credibility or clarity
- **Suggested fix:** concrete, minimal, and unlikely to prompt further review concerns. Give the exact replacement text.

One defect at several sites is one finding, listing every line number.

## Important guidance

- **Verify before flagging.** Re-read the surrounding context before calling something a hedging gap or inconsistency — the qualifier may sit in the preceding or following sentence. False positives waste the author's time and erode trust in the review.
- **Check the designated limits sections** (§5 and §7) before flagging an unacknowledged limitation.
- **Build the project.** Run `make build` to check for broken references, citation issues, freeze drift, evaluation-pin divergence, and lost hedge pins.
- **Prefer a fresh session.** Tightening prose you just wrote finds little. If this session drafted the text, say so.
- **Verify factual claims.** Suspected factual errors (author name, date, claim about prior work): check the PDFs in `refs/` or do a quick web search before flagging. Only report confirmed errors.

**If the paper is clean enough that remaining issues are all judgement calls, say so.** A "no safe fixes remain" result is a valid and useful outcome.

Do NOT make any changes. Present the review for discussion first.
