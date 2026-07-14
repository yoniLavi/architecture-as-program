# Project Context

## Purpose
"Architecture as Program" is primarily a **research proposal** (`proposal.typ`) arguing that
AI coding agents + functional reactive programming + object-capability security converge on a
new development paradigm: the **signal graph** as simultaneously architecture model, security
policy, and source of truth.

Alongside the prose, the repo carries a small, tested **proof-of-concept toolchain** that backs
the proposal's claims. We are now extending that PoC from static graph analysis toward an
**executable runtime**, to demonstrate the proposal's load-bearing claims (and to feed roadblocks
back into the proposal — chiefly Technical Note A). We dogfood spec-driven development (OpenSpec)
for this work, which is itself one of the trends the proposal describes.

## Tech Stack
- **Proposal:** Typst (`proposal.typ`), BibTeX (`citations.bib`), Pandoc (md/html export).
- **Existing PoC tooling:** Python 3.11+, **stdlib-only** (`scripts/type_parser.py`,
  `scripts/graph_validator.py`), driven by `uv`; pytest test suite under `tests/`.
- **New PoC runtime:** Python host (reuses the parser/validator). Real LLM nodes call the
  Anthropic API via the official SDK (isolated in an optional dependency group). A later increment
  ports node execution to WASM/WASI (wasmtime) for true no-ambient-authority enforcement.

## Project Conventions

### Code Style
- Ruff lint + format (`pyproject.toml`); line length 100; target py311.
- The **proposal toolchain stays stdlib-only** so the pre-commit hooks remain portable.
  Runtime-PoC dependencies (Anthropic SDK, wasmtime) live in a separate, optional dependency
  group and must not leak into the validator/parser import graph.

### Architecture Patterns
- `graphs/*.json` are the single source of truth; pseudocode and diagrams are generated from them.
- The runtime PoC **consumes the same graph JSON** and **reuses the existing validator** rather
  than reimplementing type checks — the "reject the unsafe wiring at assembly time" demo *is* the
  validator.
- Capability injection: nodes receive capability handles as explicit parameters and have no other
  mechanism to reach external authority. Enforcement is staged — host-level discipline first,
  WASM/WASI sandbox enforcement later.

### Testing Strategy
- pytest, run on every commit via pre-commit and in CI. New runtime code ships with tests.
- LLM-backed behaviour is exercised hybrid: real Anthropic calls for the adversarial/security
  demonstration, recorded fixtures for reproducible/replay paths.

### Git Workflow
- Work on `main` is committed only when the user asks. Commit message trailers are configured.
- PoC code lives under `poc/`; it does not alter the proposal build.

## Domain Context
See `AGENTS.md` for the full proposal structure and the canonical `CustomerSupport` /
`SupportPlatform` example graphs. Key vocabulary: signal graph, node, capability handle (`with`
clause), trust tainting (`Untrusted<T>`), trust discharge, capability scoping/narrowing.

## Important Constraints
- **Hedging discipline:** the Phase 1 type system does not exist yet. Neither the proposal nor the
  PoC may claim guarantees the implementation does not deliver. The PoC's enforcement fidelity
  (host-discipline vs sandbox vs hardware) must be stated honestly at each stage.
- Roadblocks encountered while building the PoC are first-class outputs: they update Technical
  Note A and the relevant proposal sections.

## External Dependencies
- Anthropic API (real LLM node execution; optional dependency group).
- `uv`, Typst, Pandoc, and (later) wasmtime for the WASI increment.
