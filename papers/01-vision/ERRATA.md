# Errata — Paper 1 (The Founding Vision)

This paper is **frozen**. Its pinned inputs (`graphs/`, `diagrams/`) reproduce
the repository's state at commit `7acf585~1` (`b28593a`; see *Commit identifiers*
below) — the last state before the
executable runtime demonstrator (`poc/`) was introduced. The document dates
itself *June 2026*, and its content is faithful to that date: the founding
vision genuinely existed in that form. A build check
(`scripts/check-freeze.py`) guards the sources against silent edits.

**One-time preprint revision (July 2026).** For posting as an arXiv preprint,
`proposal.typ` underwent a single editorial revision: typographic and phrasing
tidies, and the removal of one short passage that previewed an early
proof-of-concept implementation (out of place in a standalone vision paper, and
covered separately). **No prediction or argument of the vision was added,
removed, strengthened, or weakened** — the revision was diffed against the June
2026 freeze commit to keep it so, and its net effect versus that commit is
exactly the removal of that one passage. After the revision the paper was
**re-frozen at the published-preprint commit** (the `FREEZE_REF` in
`scripts/check-freeze.py` moved to it), and it is errata-only again thereafter.
The title page dates the paper June 2026, when the vision was formed and
circulated; the July copyedit is recorded here rather than in the paper, so the
paper stands on its own as a published artifact.

**Concluding step of that revision (21 July 2026).** The preprint was published
on Zenodo rather than arXiv: arXiv's October 2025 moderation practice for its CS
categories requires prior peer review for position papers, which a vision paper
is. Per the `paper-corpus` spec, the single publication revision concludes at
the actual publication event, and the concluding step is limited to
publication-day changes: the record's DOI
([10.5281/zenodo.21473361](https://doi.org/10.5281/zenodo.21473361)) and the
CC BY 4.0 licence line stamped onto the title block, plus one
rendering-legibility fix (the Figure 1 edge label overlapped its node boxes; it
now breaks across two lines with wider column spacing — content identical). No
prediction, hedge, or argument changed. The paper was then re-frozen at the
published commit (`FREEZE_REF` in `scripts/check-freeze.py` names it) and is
errata-only thereafter.

Apart from that one sanctioned revision, the text is **never rewritten in
place**. Corrections are recorded here instead, each dated, so the original
claims and any later corrections both remain legible. If you need to know what
the founding vision actually said, read `proposal.typ`; if you need to know what
was later found to be wrong with it, read this file.

For everything the demonstrator went on to substantiate, revise, or complicate,
see Paper 2 (`papers/02-demonstrator/`) and the change history under
`openspec/changes/`.

## Corrections

_None recorded yet._

## Served copies

**28 September 2026 — served from the published artifacts; web copies restored and
frozen.** Not a correction to the paper, whose text is unchanged. Until this date
every build regenerated the paper's PDF, Markdown, HTML and figures from the frozen
sources, through shared tooling that kept moving.
- A rebuilt PDF had drifted from the Zenodo record in bibliography formatting only.
- pandoc 3.11 had begun dropping the *Note on process* (the paper's AI-attribution
  paragraph, which the published PDF carries) from the Markdown and HTML web copies.

From this date the paper is marked published (`PUBLISHED.json`) and is **served, not
built**:
- the PDF is the Zenodo record's file byte-for-byte;
- the web copies and figure SVGs were rendered once more, with the *Note on process*
  restored and no other change, and are frozen.

`scripts/check-freeze.py` fails the build if any served file drifts from its
recorded checksum.

## Commit identifiers

**30 September 2026 — the freeze references re-pointed after a history rewrite.** Not
a correction to the paper, whose text and served files are unchanged. At some point
after 21 July the repository's history was rewritten, giving every commit from 14 July
onwards (the first `poc/` commit and after) a new identifier with an identical tree, so the identifiers this record and
the guard used stopped resolving in any fresh clone. The freeze guard then skipped
itself there without failing. The references now name the reachable commits with the
same trees:

| Before | Now | What it is |
|---|---|---|
| `59898cc~1` | `7acf585~1` (both are `b28593a`, which the rewrite left alone) | the last state before `poc/` |
| `0137aea` | `9ae2380` | the preprint preparation step |
| `c4ae487` | `5a551e0` | the published commit (`FREEZE_REF`, `source_commit`) |

The guard now fails, instead of skipping, when a full clone cannot reach its reference.
