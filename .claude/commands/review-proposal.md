Please perform a full critical review of the research proposal in this repository.

## Phase 1: Read everything

Read all source files in parallel:
- `proposal.typ` (the proposal)
- `citations.bib` (bibliography)
- `AGENTS.md` (repo context)
- `Makefile` and `.githooks/pre-commit` (build pipeline)
- All scripts in `scripts/`
- All graph definitions in `graphs/`

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

- **Verify before flagging.** If you think hedging is missing, re-read the surrounding paragraph carefully — the proposal uses a consistent pattern of conditional language that may appear several sentences before or after the claim. Don't flag a hedging gap without confirming it's actually absent.
- **Check cross-references.** When a claim seems unsupported, check whether Technical Note A addresses it before listing it as a gap.
- **Build the project.** Actually run `make build` to verify — don't just read the Makefile.
- **Be concrete.** Every recommendation should include specific line numbers and a suggested fix that could be implemented without further discussion.

Do NOT make any changes. Present the review for discussion first.
