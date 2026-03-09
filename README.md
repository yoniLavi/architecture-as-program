# Architecture as Program

A research proposal for capability-injected, model-driven software development in the age of AI agents.

## Reading the proposal

- [**PDF**](https://yonilavi.github.io/architecture-as-program/proposal.pdf) (formatted)
- [**HTML**](https://yonilavi.github.io/architecture-as-program/proposal.html) (web-readable)
- [**Markdown**](https://yonilavi.github.io/architecture-as-program/proposal.md) (plain text, for pasting into Google Docs, etc.)

These are built automatically from source on every push to `main`.

## Building from source

### Prerequisites

- [Typst](https://typst.app/) — document compiler
- [Pandoc](https://pandoc.org/) — for markdown export (with citeproc)
- Python 3 — for post-processing scripts

### Build

```sh
make build
```

This compiles the Typst source to PDF and exports a cleaned markdown version with resolved citations and cross-references.

### Git hooks

To enable the pre-commit hook (which runs the build and blocks on errors):

```sh
git config core.hooksPath .githooks
```
