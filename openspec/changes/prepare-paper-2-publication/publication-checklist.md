# Paper 2 publication checklist (Zenodo)

Prepared 28 September 2026 for the author's upload. This file prepares the record
and nothing more. **Publishing is the author's step, taken with an explicit go.** It
supersedes `archive/2026-08-01-split-demonstrator-paper/zenodo-metadata.md`, which it
updates. Zenodo pitfalls hit while publishing Paper 1 (the preview-pointer bug, and
drafts discarding metadata edits) are recorded in the agent memory, and step 3 below
avoids both.

> **Amended 30 September 2026 by `merge-and-condense-papers`.** Paper 3 is merged into
> Paper 2, and the steps below still govern the upload, with these changes:
> - Steps 2.1–2.2 are done: the DOI is reserved and stamped (`58211c8`); only 2.3 remains. Its `lavi_confinement_2026` bib step is moot,
>   because that entry was deleted: it was only Paper 3's citation of Paper 2.
> - The title is unchanged. The **description** is the *new* abstract, which now also
>   reports the accounting of Paper 1's predictions. Consider adding the keyword
>   *pre-registration*.
> - Related identifiers: **Continues** Paper 1 is the only relation to it (the author's
>   decision; *Reviews* was declined as a likely misreading).
> - Step 4's "Paper 3 can now publish" no longer applies.
> - **Before step 1:** the author's end-to-end read of the merged paper, carried over from
>   `merge-and-condense-papers` (archived 30 September after five review rounds; see its
>   `tasks.md`). The three decisions those rounds left open were settled on the author's
>   instruction on 30 September: the trust-lattice unification is a simplification, so
>   the corrections are **three**; the contracts row stays *Partial*, with §3.3.3 now
>   stating that no canonical graph attaches a contract; and the ordinal 3 is retired.
> - The pre-flight spot-checks still hold after renumbering: §4.1 names
>   `hostile_ungranted`, §4.3 is the overhead table, and §6.2 carries CAmkES. The PDF
>   also shows the outcomes table in §5, with 19 rows.

## 1. Pre-flight (local)

- [ ] `git status` is clean and `main` holds the commits of this change.
- [ ] **`make clean && make build`, not only `make build`.** Make skips targets whose
      inputs have not changed, so an older `dist/` can survive a toolchain upgrade
      unnoticed. That happened on 28 September: every paper's Markdown carried a
      process note that the current pandoc no longer produces. Build on an idle
      machine, because §4.3's table carries one run's timings (the overhead band will
      refuse a contended run).
- [ ] Open `dist/papers/02-demonstrator/lavi-2026-confinement-by-construction.pdf` and
      check the following:
  - the date line reads *September 2026*
  - the abstract's crossing cost reads *tens of microseconds* (a magnitude, not a
    per-run figure)
  - §4.1 names `hostile_ungranted` as the negative control
  - §6.2 carries the CAmkES paragraph
- [ ] The filename's year (2026) matches the publication year, so no rename is needed.

## 2. Reserve the DOI, then stamp it (before uploading)

This is the order that worked for Paper 1. The DOI is in the PDF, so it has to be known
before the final build.

1. On Zenodo, create a **new upload** (not a new version of Paper 1: they are separate
   works) and click **Reserve DOI**.
2. Stamp it. This is a one-commit change, and Claude can make it given the DOI:
   - In `papers/02-demonstrator/proposal.typ`, below the date line, add a line in
     the same form as Paper 1's:
     `Preprint · #link("https://doi.org/<DOI>")[doi:<DOI>] · CC BY 4.0`
   - ~~In `citations.bib`, complete `lavi_confinement_2026`~~ — moot since the merge:
     that entry was deleted, because only Paper 3 cited it.
3. `make clean && make build` again, then upload the freshly built
   `lavi-2026-confinement-by-construction.pdf`. Set it as the preview file *before* the
   first publish, so the preview-pointer bug has nothing to trip on.

## 3. Record metadata

- **Resource type:** Publication → Preprint
- **Title:** Confinement by Construction: Capability Surfaces Derived from an Architecture Model
- **Creator:** Lavi, Yoni. The affiliation is *Codeliance*. Set it on the record
  itself, because ORCID autofill does not re-sync.
- **Publication date:** the upload date
- **Licence:** Creative Commons Attribution 4.0 International (CC BY 4.0), as for Paper 1
- **Language:** English
- **Version:** 1.0.0. Paper 2 is a *living* paper, so later revisions become new
  versions of this record under the same concept DOI.
- **Description:** the abstract, verbatim from the built PDF. It now states the
  crossing cost as a magnitude, so it will stay true across rebuilds.
- **Keywords:** capability-based security; object capabilities; WebAssembly Component
  Model; software architecture; functional reactive programming; information-flow
  control; prompt injection; LLM agents; architecture as code

**Related identifiers**

| Relation | Identifier | Resource type |
|---|---|---|
| Continues | `10.5281/zenodo.21473361` (Paper 1, the founding vision) | Publication / Preprint |
| Is supplemented by | the GitHub repository URL (the artifact this paper reports) | Software |

Optionally, tag the published commit (for example `paper-2-v1.0.0`) and link the tag's
URL instead of the bare repository, so that the supplement points at the exact artifact
the PDF reports. Pushing a tag is outward-facing too, so it is the author's call.

## 4. After publishing

- [ ] Paper 1's record is untouched. Its single publication revision is spent.
- [ ] Commit the DOI stamp (step 2) if it was not committed before the upload.
- [ ] Archive this change: `openspec archive prepare-paper-2-publication`.
- ~~Paper 3 can now publish.~~ Moot since the merge: there is no Paper 3.

## A note on Paper 1 that this surfaced

Paper 1 stays frozen. This change does not alter its source, and does not alter its
built PDF text, Markdown or HTML (each was compared against a build from the
pre-change commit). But a PDF rebuilt from the frozen source today **differs from the
copy on Zenodo in bibliography formatting only**:
- `pp.` becomes `p.` for article-number page ranges
- `July` becomes `Jul.`
- some line breaks move
- the ASIAN 2003 entry renders with its editors, after the post-freeze bib fix

The causes are the Typst upgrade (0.14 → 0.15) and that shared-bib fix. No body text
differs. **Resolved the same day by `mark-published-papers`**, at the author's request.
Paper 1 is now marked published and served from its stored artifacts, starting with
the Zenodo PDF byte-for-byte, and is never rebuilt, so this drift cannot reach
readers.
