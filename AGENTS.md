# Architecture as Program — Agent Guide

## What this repo is

A research proposal arguing that AI coding agents + functional reactive programming + object-capability security converge on a new development paradigm: the **signal graph** as simultaneously architecture model, security policy, and source of truth.

This is a **writing project**, not a software project. The primary output is a formatted proposal document. There is no application code.

## Key files

| File | Role |
|---|---|
| `proposal.typ` | The proposal source (Typst markup). This is the artifact that matters. |
| `citations.bib` | BibTeX bibliography. Every entry must be cited in the proposal; every citation must have an entry. |
| `Makefile` | Builds `dist/proposal.pdf` and `dist/proposal.md` from source. |
| `.githooks/pre-commit` | Runs `make build` + citation check. Enable with `git config core.hooksPath .githooks`. |
| `scripts/` | Build support: pandoc cross-ref filter, markdown cleanup, unused citation checker. |

## Proposal structure

The proposal follows a deliberate argument arc:

1. **The window** (§1) — Why graph-based code representations are newly viable (AI agents removed the human objection)
2. **Central thesis** (§2) — Four interlocking properties: signal graph as source of truth, capabilities as injected parameters, code as compiled artifact, security by construction
3. **FRP as core** (§3) — Technical foundation in functional reactive programming, with capability annotation and trust tainting as extensions
4. **Prior art** (§4) — Positioning against C4, Haskell/Idris, Unison, Hazel, BEAM, ocap security, CHERI, WASM, SDD frameworks, Cedar, Roc, Darklang
5. **Proposed system** (§5) — Signal graph definition, concrete example, development workflow, runtime, performance, security properties
6. **Research agenda** (§6) — Three phases: demonstrator → hardening → formal foundations
7. **Why now** (§7) — Four converging developments
8. **Technical Note A** — Open problems (compositionality, coercion, replay, compilation, error handling, node-local state, graph-scale comprehension, graph evolution, distributed authority)
9. **Annex B** — Areas for collaboration

## When editing the proposal

- **Maintain hedging on unproven claims.** The type system does not exist yet. Claims about properties it would provide use conditional language ("would be inexpressible", "in a well-typed realisation", "in a sound realisation of the type system"). Do not strengthen these to present tense without an implementation to back them.
- **Keep citations accurate.** Every factual claim about prior work should be traceable to a citation. If adding a new claim, add the citation. Run `make build` to catch broken references (typst will error) and `scripts/check-citations.py` to catch orphaned bib entries.
- **Preserve the argument arc.** Each section builds on the previous. New content should slot into the existing structure, not break the flow.
- **Concrete over abstract.** The proposal's weakest mode is unsupported generality. Prefer specific examples (like the `CustomerSupport` graph or the `Untrusted<UserMessage>` type error) over sweeping claims.
- **Acknowledge limitations honestly.** Technical Note A exists for a reason. If a new claim has an open problem, name it there.

## Build

```sh
make build        # Build PDF + markdown
make clean        # Remove dist/
```

Requires: [Typst](https://typst.app/), [Pandoc](https://pandoc.org/) (with citeproc), Python 3.
