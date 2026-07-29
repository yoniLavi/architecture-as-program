# Architecture as Program

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.21473361.svg)](https://doi.org/10.5281/zenodo.21473361)

A longitudinal research program on capability-injected, model-driven software
development in the age of AI agents — organised as a **corpus of papers** backed
by a single shared, tested research artifact.

The program is human-directed and AI-executed, driven through spec-driven change
proposals; see [`METHODOLOGY.md`](METHODOLOGY.md) for the division of authority
and the evidence trail.

## The corpus

Papers live under [`papers/`](papers/README.md), one directory per paper:

- **Paper 1 — The founding vision** (`papers/01-vision/`): the original proposal,
  **frozen** and dated *June 2026*, reproducing the repository's state before the
  executable demonstrator existed. Errata-only. Published as a preprint:
  [doi:10.5281/zenodo.21473361](https://doi.org/10.5281/zenodo.21473361)
  (CC BY 4.0).
- **Paper 2 — *Confinement by Construction*** (`papers/02-demonstrator/`): the
  living systems paper. A node's declared capabilities determine the import
  surface of its compiled WASM component, derived from the graph and checked
  against the built binary; alongside it, a trust lattice that catches laundering
  which type-checks on every edge. Reports the artifact and its evaluation.
- **Paper 3 — *Predicting Before Building*** (`papers/03-method/`): the living
  method paper. The corpus's pre-registration protocol — freeze the vision,
  publish it under a DOI, guard it in the build, report outcomes without revising
  predictions — and the prediction-by-prediction accounting of Paper 1 against
  the artifact, including the four design corrections building it forced.

All papers share one research artifact at the repository root (`graphs/`,
`scripts/`, `poc/`, `tests/`, `citations.bib`). See
[`papers/README.md`](papers/README.md) for how living and frozen papers build.

## Reading the papers

Built automatically from source on every push to `main` and published to GitHub
Pages:

- Paper 2 (*Confinement by Construction*):
  [PDF](https://yonilavi.github.io/architecture-as-program/papers/02-demonstrator/proposal.pdf) ·
  [HTML](https://yonilavi.github.io/architecture-as-program/papers/02-demonstrator/proposal.html) ·
  [Markdown](https://yonilavi.github.io/architecture-as-program/papers/02-demonstrator/proposal.md)
- Paper 3 (*Predicting Before Building*):
  [PDF](https://yonilavi.github.io/architecture-as-program/papers/03-method/proposal.pdf) ·
  [HTML](https://yonilavi.github.io/architecture-as-program/papers/03-method/proposal.html) ·
  [Markdown](https://yonilavi.github.io/architecture-as-program/papers/03-method/proposal.md)
- Paper 1 (frozen vision):
  [PDF](https://yonilavi.github.io/architecture-as-program/papers/01-vision/proposal.pdf) ·
  [HTML](https://yonilavi.github.io/architecture-as-program/papers/01-vision/proposal.html)

> The root-level `proposal.{pdf,md,html}` URLs still resolve (they are deprecated
> aliases to Paper 2) but will be removed; prefer the `papers/02-demonstrator/`
> links above.

## Building from source

### Prerequisites

- [Typst](https://typst.app/) — document compiler
- [Pandoc](https://pandoc.org/) — for markdown/HTML export (with citeproc)
- Python 3 via [uv](https://docs.astral.sh/uv/) — for build scripts and tests

### Build

```sh
make build     # Validate graphs, run tests, guard the freeze, build the whole corpus
make test      # Run the pytest suite
make clean     # Remove dist/
```

Outputs land under `dist/papers/<id>/`. Living papers build from the shared
root artifact; the frozen paper builds only from its own pinned inputs.

### Pre-commit hooks

Install once per clone:

```sh
uv run pre-commit install
```

The hooks run ruff, the graph validator, pytest, `make build`, citation hygiene,
and the frozen-paper guard.
