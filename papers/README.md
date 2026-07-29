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
| 3. *Predicting Before Building* | `03-method/` | Living | `citations.bib` only |

Papers 2 and 3 split one document. Paper 2 reports **what the artifact
establishes**; Paper 3 reports **what predicting-then-building taught**, and owns
the predictions-and-outcomes accounting. The division is enforced by a rule worth
stating: Paper 3 interpolates no evaluation data and cites Paper 2 for every
figure, so exactly one document in the corpus is the source of any given number.
Two documents able to state a number are two documents able to disagree.

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

### A note on the two symlinks in `01-vision/`

The frozen `proposal.typ` is byte-identical to the freeze commit and so cannot be
edited to re-point its file references. Two committed symlinks make its original
relative paths resolve correctly against the shared bibliography and its own
figure tree:

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
Paper 2's is `lavi-2026-signal-graph-demonstrator.pdf` (provisional until it
publishes; rename if the year slips). For one transition, `dist/proposal.{pdf,md,html}` are also emitted as
deprecated aliases to Paper 2, so existing inbound links keep working; they will
be removed once those links point at `dist/papers/02-demonstrator/`.
