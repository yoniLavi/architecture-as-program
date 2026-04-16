Please perform a full critical review of the research proposal in this repository.

## Phase 1: Read everything

Read all source files in parallel:
- `proposal.typ` (the proposal)
- `citations.bib` (bibliography)
- `AGENTS.md` (repo context)
- `Makefile` and `.githooks/pre-commit` (build pipeline)
- All scripts in `scripts/`
- All graph definitions in `graphs/` — treat these as reviewable design artifacts, not just support files. Check that type names, variants, capability annotations, and edge-port names in the prose match the JSON.

## Phase 2: Evaluate the proposal

Assess the proposal on each of these dimensions. For each, give a clear judgement (strong / adequate / weak) with specific evidence (quote lines, name sections):

### Argument
- Is the core thesis clearly stated and well-motivated?
- Does the "why now" argument hold up? Are all legs evidenced?
- Does each section build on the previous, or are there logical gaps?

### Prior art
- Is the literature survey accurate and fairly positioned?
- Are there significant missing references that would strengthen or challenge the argument?
- Does the proposal clearly distinguish its contribution from existing work?

### Technical claims
- Are claims appropriately hedged relative to what has actually been built?
- Are there places where the proposal asserts properties that depend on an unbuilt type system without acknowledging this?
- Is the concrete graph example sufficient, or does it need more detail?
- Does the composition example (SupportPlatform) convincingly demonstrate hierarchical composition?

### Completeness
- Is the cost model / performance discussion adequate?
- Is the migration story convincing for practitioners?
- Are open problems honestly acknowledged?
- Does Technical Note A cover the right set of problems, or are there gaps?

### Cross-section consistency
- Does the framing in §2 (thesis) match the refined descriptions in §5 (proposed system) and Technical Note A? Terminology for nodes, capabilities, purity, and trust annotations should be stable across sections.
- Do the strong claims in §5.4 (security properties) cohere with the caveats named elsewhere (§5.1's coercion problem, Technical Note A's open items)? Flag places where a later-section caveat undermines an earlier-section claim without cross-reference.
- Do type names, variants, capabilities, and figure captions in the examples match between prose, JSON, and rendered diagrams?

### Presentation
- Is the abstract effective?
- Is the authorship / AI collaboration note appropriate?
- Are there structural or readability issues?
- Is the length appropriate, or are there sections that should be cut or expanded?

### Tooling
- Does the build pipeline work correctly? Run `make build` and `scripts/check-citations.py`.
- Are there missing scripts, broken dependencies, or documentation gaps?

## Phase 3: Recommendations

Present findings as a prioritised list. For each recommendation:
- **What:** the specific problem, with line numbers
- **Why it matters:** impact on the proposal's credibility or clarity
- **Suggested fix:** concrete enough to act on

Separate into:
1. **Must fix before sharing** — issues that would cause informed readers to dismiss the proposal
2. **Should fix** — issues that weaken the argument but don't break it
3. **Nice to have** — polish items

## Important guidance

- **Verify before flagging hedging.** The proposal uses a consistent hedging vocabulary for claims about properties of the unbuilt system: *"would"*, *"in a sound realisation of the type system"*, *"in a well-typed realisation"*, *"the Phase 1 target"*, *"a design obligation"*. Before flagging a hedging gap, grep for these patterns nearby — the qualifier may sit several sentences before or after the claim it qualifies.
- **Check cross-references.** When a claim seems unsupported, check whether Technical Note A addresses it before listing it as a gap. New gaps you identify should usually be proposed as Technical Note A additions rather than surfaced only in-section.
- **Build the project.** Actually run `make build`, `scripts/check-citations.py`, and — if you have concerns about bibliographic accuracy — `scripts/validate-bib.py` (which cross-checks bib entries against Semantic Scholar). Don't just read the Makefile.
- **Be concrete.** Every recommendation should include specific line numbers and a suggested fix that could be implemented without further discussion.
- **Verify factual claims.** If you have concerns about factual accuracy, verify before reporting. Common risk zones:
  - Author names, publication years, venue names → check the PDFs in `refs/` first, `scripts/validate-bib.py`, then web search as a fallback
  - Tool/language version claims (e.g. "Unison 1.0 was released in November 2025") → web search with the current year
  - Acronym expansions (CHERI, WASI, SDD, BEAM) → verify before suggesting changes
  - Claims about what a cited paper says → read the PDF excerpt in `refs/` before disputing
  - Don't list unverified suspicions as recommendations. Silence is better than a false flag.
- **Terminology drift.** If you propose a type rename or terminology change (e.g. `CustomerQuery` → `ModeratedQuery`), list every location that needs updating: prose in proposal.typ, graph JSON in `graphs/`, figure captions, Technical Note A entries, and diagram output. Incomplete renames introduce consistency bugs worse than the original issue.

Do NOT make any changes during the review itself. Present the review for discussion first.

## If asked to address the findings afterwards

If, after presenting the review, the user asks you to implement the findings:
- Work in priority order: must-fix first, then should-fix, then nice-to-have.
- Use `TaskCreate` to track progress across items — the review will often produce enough changes to benefit from explicit tracking.
- After edits, run `make build` to verify Typst compiles and cross-references resolve; run `scripts/check-citations.py` to catch orphans.
- Do a consistency sweep before reporting done: terminology changes propagated to all locations (see "Terminology drift" above), framing in §2 aligned with refinements in §5, captions updated.
- Report what changed, grouped by the review's own priority tiers, so the user can see which findings were addressed.
