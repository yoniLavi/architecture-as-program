<!-- OPENSPEC:START -->
# OpenSpec Instructions

These instructions are for AI assistants working in this project.

Always open `@/openspec/AGENTS.md` when the request:
- Mentions planning or proposals (words like proposal, spec, change, plan)
- Introduces new capabilities, breaking changes, architecture shifts, or big performance/security work
- Sounds ambiguous and you need the authoritative spec before coding

Use `@/openspec/AGENTS.md` to learn:
- How to create and apply change proposals
- Spec format and conventions
- Project structure and guidelines

Keep this managed block so 'openspec update' can refresh the instructions.

<!-- OPENSPEC:END -->

# Architecture as Program — Notes for all Agents (This AGENTS.md is also symlinked for Claude Code to access as CLAUDE.md)

## What this repo is

A research proposal arguing that AI coding agents + functional reactive programming + object-capability security converge on a new development paradigm: the **signal graph** as simultaneously architecture model, security policy, and source of truth.

This is a **writing project**, not a software project. The primary output is a formatted proposal document. There is no application code.

## Key files

| File | Role |
|---|---|
| `proposal.typ` | The proposal source (Typst markup). This is the artifact that matters. |
| `citations.bib` | BibTeX bibliography. Every entry must be cited in the proposal; every citation must have an entry. |
| `graphs/*.json` | Canonical signal graph definitions. Single source of truth for both pseudocode and diagrams. |
| `Makefile` | Builds `dist/proposal.pdf`, `dist/proposal.md`, and `dist/proposal.html` from source. |
| `.pre-commit-config.yaml` | Pre-commit hooks (ruff, graph validation, pytest, `make build`, citation check). Install once per clone with `uv run pre-commit install`. |
| `scripts/` | Build support: graph generator, pandoc cross-ref filter, markdown cleanup, unused citation checker. |

## Proposal structure

The proposal follows a deliberate argument arc:

1. **The window** (§1) — Why graph-based code representations are newly viable (AI agents removed the human objection)
2. **Central thesis** (§2) — Four interlocking properties: signal graph as source of truth, capabilities as injected parameters, code as compiled artifact, security by construction
3. **FRP as core** (§3) — Technical foundation in functional reactive programming, with capability annotation and trust tainting as extensions
4. **Prior art** (§4) — Positioning against C4, Haskell/Idris, Effekt/capture checking, Unison, Hazel, BEAM, ocap security, CHERI, WASM, SDD frameworks, Cedar, Roc, Darklang
5. **Proposed system** (§5) — Signal graph definition, concrete example, development workflow, runtime, performance, security properties
6. **Research agenda** (§6) — Three phases: demonstrator → hardening → formal foundations
7. **Why now** (§7) — Four converging developments
8. **Technical Note A** — Open problems (compositionality, coercion, replay, compilation, error handling, contract incompleteness, node-local state, graph-scale comprehension, capability routing/aggregation, user-level authorisation, revocation, covert channels, graph evolution, soundness, distributed authority)
9. **Annex B** — Areas for collaboration

## When editing the proposal

- **Maintain hedging on unproven claims.** The type system does not exist yet. Claims about properties it would provide use conditional language ("would be inexpressible", "in a well-typed realisation", "in a sound realisation of the type system"). Do not strengthen these to present tense without an implementation to back them.
- **Keep citations accurate.** Every factual claim about prior work should be traceable to a citation. If adding a new claim, add the citation. Run `make build` to catch broken references (typst will error) and `scripts/check-citations.py` to catch orphaned bib entries.
- **Preserve the argument arc.** Each section builds on the previous. New content should slot into the existing structure, not break the flow.
- **Concrete over abstract.** The proposal's weakest mode is unsupported generality. Prefer specific examples (like the `CustomerSupport` graph or the `Untrusted<UserMessage>` type error) over sweeping claims.
- **Acknowledge limitations honestly.** Technical Note A exists for a reason. If a new claim has an open problem, name it there.

## Tooling (present and tested)

Although this is a writing project, the proposal ships with a working, tested PoC toolchain that backs the claims in §5 and @sec:phase1. It is not vapourware: it builds and passes its tests on every commit (via the pre-commit `make-build` and `pytest` hooks) and in CI.

- **Canonical graph sources** — `graphs/*.json` are the single source of truth. `graphs/schema.json` is the JSON Schema they validate against; `customer-support.json` and `support-platform.json` are the two graphs rendered in the proposal. Pseudocode listings *and* SVG diagrams are generated from them (`scripts/generate-graph.py`), so the figures cannot drift from the text.
- **Type parser** — `scripts/type_parser.py` parses the capability-annotated type grammar (angle-bracketed generics, capability scopes/modes, sum types with role labels). `scripts/emit-grammar.py` emits `dist/grammar.md` from it, so the documented grammar is generated from the implementation, not maintained by hand.
- **Graph validator** — `scripts/graph_validator.py` (driven by `scripts/validate-graphs.py`) runs the six classes of analysis described in @sec:phase1: edge type-compatibility (with sum-variant resolution), trust propagation (`discharges_trust`), variant completeness, capability narrowing at composition, intra-graph consistency, and cross-graph signature matching.
- **Executable runtime** (`poc/`) — loads the same graph JSON, instantiates each node with **injected capability handles**, and propagates signals. Reuses the validator to reject unsafe wiring at assembly time. Ships a prompt-injection demonstration (`uv run python -m poc.demo`, `--live` for real Claude calls). See `poc/README.md`. **Enforcement is host-discipline only** — it shows the *shape* of capability confinement, not unforgeable containment; the WASM/WASI tier is a named follow-up.
- **Tests** — `tests/` is a pytest suite covering the parser, the validator, and the runtime: **82 tests + 11 subtests, all passing** (`make test` or `uv run pytest`). The validator and parser stay dependency-free so the pre-commit hook remains portable; the runtime's optional Anthropic dependency lives in the `poc` dependency group (`uv sync --group poc`) and must never leak into `scripts/`.
- **Build outputs** — `make build` produces `dist/proposal.{pdf,md,html}`, the rendered graph/diagram SVGs, and `dist/grammar.md`. `dist/` is gitignored.
- **Citation hygiene** — `scripts/check-citations.py` (orphaned bib entries) and `scripts/validate-bib.py` run as checks; every bib entry must be cited and every citation must resolve (Typst errors on broken refs).

The toolchain is **not** the Phase 1 language: it implements no noninterference proof, flow-sensitive wiring, or coercion lattice (see Technical Note A), and the runtime does not make capability confinement unforgeable. It is early evidence that the graph-level analyses are implementable with modest tooling.

## Spec-driven development (OpenSpec)

Work on this repo is driven through **OpenSpec** (`openspec/`). Read `openspec/AGENTS.md` before planning changes. Non-trivial work gets a change proposal (`openspec/changes/<id>/` with `proposal.md`, `tasks.md`, optional `design.md`, and spec deltas), validated with `openspec validate <id> --strict`, and approved before implementation. This dogfoods the proposal's own thesis: structured intent as the primary artifact.

## Build

```sh
make build        # Validate graphs, run tests, build PDF + markdown + HTML + grammar card
make test         # Run the type-parser and graph-validator unit tests (pytest)
make clean        # Remove dist/
```

Requires: [Typst](https://typst.app/), [Pandoc](https://pandoc.org/) (with citeproc), Python 3 via [uv](https://docs.astral.sh/uv/). All three are present and working in the current environment (typst 0.14, pandoc 3.8, uv 0.6).
