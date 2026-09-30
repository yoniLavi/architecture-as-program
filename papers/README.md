# The paper corpus

The written outputs of this research program live here, one directory per paper,
ordered by an ordinal prefix. The date each paper claims lives *inside* the
document, where it is authoritative; the directory name carries only the sequence
and a content label.

All papers are backed by a single **shared research artifact** at the repository
root — `graphs/`, `scripts/`, `poc/`, `tests/`, and `citations.bib`. The corpus
is a set of *views* onto one evolving body of work: one artifact, one test suite,
one bibliography.

| Paper | Directory | Status | Builds from |
|---|---|---|---|
| 1. The founding vision | `01-vision/` | **Frozen** (errata-only) | Its own pinned inputs |
| 2. *Confinement by Construction* | `02-demonstrator/` | Living | The shared root artifact |

Paper 2 reports **what the artifact establishes** and owns the
predictions-and-outcomes accounting of Paper 1 against it. From August to
September 2026 the accounting lived in a separate method paper, Paper 3
(*Predicting Before Building*, `03-method/`). The two cited each other while
neither was published, so neither could publish first, and on 30 September 2026
they were merged into one condensed Paper 2. Paper 3's last text is at the git tag
`paper-3-before-merge`. The rule that came out of it: **a published paper cites no
unpublished work.**

The directory name `02-demonstrator/` is kept for its published GitHub Pages
URLs; per the convention below, a directory label carries sequence and a rough
content hint, not the title.

## Living vs frozen papers

A **living** paper (Paper 2) builds from the shared artifact at the root and is
rewritten as the artifact evolves. Its figures are the current, canonical ones.

A **frozen** paper (Paper 1) is a historical record: it reproduces the
repository's state at a freeze commit — for Paper 1, the last state before the
executable demonstrator (`poc/`) existed, which the document dates *June 2026*.
A frozen paper is **self-contained**: it carries its *own* copies of the graph
JSONs and diagram sources it references as of the freeze (`01-vision/graphs/`,
`01-vision/diagrams/`) and builds only from them, so later evolution of the
shared artifact can never alter its rendered figures. A frozen paper is changed
only by **dated errata** (`01-vision/ERRATA.md`), never by silent rewriting;
`scripts/check-freeze.py` fails the build if its sources drift from the freeze
commit.

A frozen paper that has been **published** (Paper 1, since 21 July 2026) goes one
step further. It carries a `PUBLISHED.json` marker, which records the DOI, the
record, the date, the source commit, the record's MD5 of its file, and a SHA-256
for every served file. From then on it is **served, not built**: `make` copies
`01-vision/published/` into `dist/`, and no typst, pandoc, filter, CSL or
bibliography change can reach it. The PDF is the Zenodo record's file
byte-for-byte. The web copies and figures were rendered once and frozen.
`check-freeze.py` fails the build if a served file is missing, altered, unlisted,
or (for the PDF) no longer the record's file.

A source freeze alone was not enough. The sources did not move, but the tooling
that rendered them did, and a rebuilt Paper 1 had drifted from its published copy
in September 2026 (see `01-vision/ERRATA.md`).

### A note on the two symlinks in `01-vision/`

The frozen `proposal.typ` is byte-identical to the freeze commit and so cannot be
edited to re-point its file references. Since Paper 1 is served rather than built,
these now matter only if the frozen source is ever rendered again deliberately. Two
committed symlinks make its original relative paths resolve correctly against the
shared bibliography and its own figure tree:

- `01-vision/citations.bib → ../../citations.bib` — the shared bibliography.
- `01-vision/dist → ../../dist/papers/01-vision` — its frozen figure outputs, so
  the paper's relative `dist/…` figure references resolve for both typst
  (file-relative) and pandoc (cwd-relative).

## Building

`make build` (from the repository root) builds the whole corpus. Outputs land
under `dist/papers/<id>/` — `proposal.{pdf,md,html}` plus the figures each paper
references.

Each paper's PDF is additionally emitted under a citable, self-identifying
name: `lavi-<year>-<slug>.pdf`. That copy is the file to upload to venues;
internal build names stay `proposal.*` (stable paths, no link churn). The year
is finalised at publication: Paper 1's is `lavi-2026-architecture-as-program.pdf`
(published — Zenodo,
[doi:10.5281/zenodo.21473361](https://doi.org/10.5281/zenodo.21473361));
Paper 2's is `lavi-2026-confinement-by-construction.pdf` (provisional until it
publishes; rename if the year slips). For one transition, `dist/proposal.{pdf,md,html}` are also emitted as
deprecated aliases to Paper 2, so existing inbound links keep working; they will
be removed once those links point at `dist/papers/02-demonstrator/`.
