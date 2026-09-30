# Serve the published Paper 1 from its published artifacts, not a rebuild

## Why

Paper 1 is published (Zenodo, doi:10.5281/zenodo.21473361) and frozen, but "frozen"
has so far meant *its source is frozen*. Every build still regenerated its PDF,
Markdown, HTML and figures from that source, through shared inputs that keep moving:
the Lua filter, the CSL, the shared `citations.bib`, and whatever typst and pandoc
the machine (or CI, which installs the latest of each on every push) happens to
have. The freeze guard checks none of those. Three effects were observed on
28 September 2026:

- A rebuilt PDF differs from the Zenodo record in its bibliography formatting (typst
  0.15, and a post-freeze bib fix). Body text is identical.
- pandoc 3.11 parses the centred "Note on process", the paper's AI-attribution
  paragraph, in a way the filter dropped. The web copies on GitHub Pages have been
  served without it, though the published PDF carries it.
- A fix to the shared filter, made for Paper 2, would have changed Paper 1's web
  copies as a side effect. The author stopped it: Paper 1 is published and should be
  frozen.

The author asked for Paper 1 to be *marked* published, so that the tooling leaves it
alone.

## What Changes

- **`papers/01-vision/PUBLISHED.json`** is the marker. It records the DOI, the record
  URL, the publication date, the source commit, the Zenodo file's MD5 as the record
  states it, and a SHA-256 for every stored artifact.
- **`papers/01-vision/published/`** holds what is served:
  - the Zenodo PDF, byte-for-byte (its MD5 matches the record's);
  - the Markdown and HTML web copies, the stylesheet, and the three figure SVGs they
    reference.

  The web copies are rendered **once more, deliberately**, with the "Note on process"
  restored so they match the published PDF's content. This is the author's decision
  of 28 September 2026. It is the last time they change, and it is recorded in
  `ERRATA.md`.
- **Build**: `make` copies the stored artifacts into `dist/papers/01-vision/` instead
  of running typst or pandoc over Paper 1, so no build input and no toolchain
  version can reach it.
- **Guard**: `scripts/check-freeze.py` also verifies the published artifacts. The
  build fails if a file is missing, differs from its recorded SHA-256, or sits
  unlisted in `published/`, or if the PDF no longer matches the record's MD5. Tests
  cover each failure path.
- **Hook config**: `check-added-large-files` exempts exactly the published PDF
  (683 KB, over the 500 KB cap), and `check-freeze` now also triggers on the marker
  and the stored artifacts.

## Impact

- Affected specs: `paper-corpus`
- Affected code: `Makefile`, `scripts/check-freeze.py`, `.pre-commit-config.yaml`,
  `tests/test_check_freeze.py` (new)
- Affected docs: `AGENTS.md`, `papers/README.md`, `papers/01-vision/ERRATA.md`
- Paper 1's sources are untouched and `FREEZE_REF` does not move. The source freeze
  remains in force: the sources remain the provenance of the record, and the
  published artifacts are what readers receive.
- CI needs no change. It still runs `make build`, which now copies Paper 1 instead of
  rebuilding it.
