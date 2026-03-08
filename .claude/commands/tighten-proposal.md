Please perform a tightening review of the research proposal in this repository. The proposal has been through multiple review cycles and is near-final. The goal now is to find small, safe improvements — not to expand scope.

## Phase 1: Read everything

Read all source files in parallel:
- `proposal.typ` (the proposal)
- `citations.bib` (bibliography)
- `AGENTS.md` (repo context)

## Phase 2: Review for tightening

Focus exclusively on these dimensions:

### Internal consistency
- Are there claims in the body that contradict or are hedged differently from Technical Note A?
- Are citations used correctly (right claim attributed to right source)?
- Does the concrete graph example match its prose description and diagram caption?

### Overstatement
- Are there places where the proposal asserts properties of the unbuilt system without conditional language?
- Are there unsupported empirical claims (trends stated without evidence)?

### Redundancy and verbosity
- Are there sentences or paragraphs that repeat a point already made elsewhere?
- Are there passages that could be shortened without losing meaning?
- Is anything present that a reviewer could reasonably ask to be cut?

### Surface quality
- Typos, grammar, awkward phrasing, inconsistent terminology.
- Formatting issues in the Typst source.

## Phase 3: Recommendations

**Constraints on recommendations:**
- Do NOT suggest adding new sections, subsections, or prior art references.
- Do NOT suggest expanding existing sections or adding detail.
- Every recommendation must be self-contained: implementing it should not open new questions or require follow-up changes elsewhere.
- Prefer cuts and rewrites over additions. The proposal should not get longer.

**Classify each recommendation:**
- **Safe fix:** corrects an error or inconsistency without changing any claim. Unlikely to draw reviewer attention.
- **Judgement call:** improves the text but touches framing, scope, or emphasis. Could open new questions.

Present findings as a flat prioritised list. For each recommendation:
- **What:** the specific problem, with line numbers
- **Classification:** safe fix or judgement call
- **Why it matters:** impact on credibility or clarity
- **Suggested fix:** concrete, minimal, and unlikely to prompt further review concerns

**If the proposal is clean enough that remaining issues are all judgement calls, say so.** A "no safe fixes remain" result is a valid and useful outcome.

Do NOT make any changes. Present the review for discussion first.
