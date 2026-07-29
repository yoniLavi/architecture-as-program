# Zenodo metadata draft — Paper 2

For author review. **Publishing is a separate, explicitly-approved step**; this
file only prepares the record. Mechanics and known pitfalls: see the session
memory on Zenodo publish quirks (preview-pointer publish bug, two-step rename
workaround, drafts discarding metadata edits).

- **Upload type**: Publication → Preprint
- **Title**: Confinement by Construction: Capability Surfaces Derived from an Architecture Model
- **Authors**: Lavi, Yoni (Codeliance)
- **File to upload**: `dist/papers/02-demonstrator/lavi-2026-confinement-by-construction.pdf` (PDF/A-2b)
- **Licence**: Creative Commons Attribution 4.0 International (CC BY 4.0) — same as Paper 1
- **Language**: English
- **Version**: 1.0.0

**Related identifiers**

| Relation | Identifier |
|---|---|
| `isContinuedBy` ← this record continues | `10.5281/zenodo.21473361` (Paper 1, the founding vision) |
| `isSupplementedBy` | the GitHub repository URL (the artifact this paper reports) |

Paper 3 (*Predicting Before Building*) publishes **after** this record and cites
its DOI, so its `isSupplementTo` / `cites` relation can only be filled in once
this DOI exists. Do not publish them in the reverse order.

**Keywords**: capability-based security; object capabilities; WebAssembly
Component Model; software architecture; functional reactive programming;
information-flow control; prompt injection; LLM agents; architecture as code

**Description** (Zenodo abstract field): use the paper's abstract verbatim from
`papers/02-demonstrator/proposal.typ`. It already carries the honest bounds
(curated corpus, no soundness result, attenuation not elimination) that the
record should not overstate.

**Before publishing, check**

- [ ] `make build` green and the uploaded PDF is the freshly built one
- [ ] The paper's date line and the record date agree
- [ ] The citable filename's year matches the actual publication year — rename
      both the Makefile target and the file if the year has slipped
- [ ] Paper 1's record is untouched (its single publication revision is spent)
