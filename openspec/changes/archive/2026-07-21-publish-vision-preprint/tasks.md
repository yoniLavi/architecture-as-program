# Tasks

## 1. Concluding step of the sanctioned publication revision
- [x] 1.1 Reserve the DOI on Zenodo (human: New upload → upload PDF → "Get a DOI now!") and supply it to the
      implementing session
- [x] 1.2 Stamp the title block of `papers/01-vision/proposal.typ`: preprint line with the reserved DOI and
      CC BY 4.0 licence; no other line of the paper changes
- [x] 1.3 Fix `papers/01-vision/diagrams/typed-wiring.typ`: widen column spacing and break the ill-typed edge
      label onto two lines so it no longer overlaps the node boxes (legibility only; content identical)
- [x] 1.4 Verify the diff against the current freeze commit is exactly those two hunks — no prediction,
      hedge, or argument touched
- [x] 1.5 Re-freeze: commit the revision, move `FREEZE_REF` in `scripts/check-freeze.py` to that commit,
      update its docstring, and record the concluding step in `papers/01-vision/ERRATA.md` under the one
      publication-revision entry
- [x] 1.6 Full gate green: `make build` (freeze guard, citations, tests) at the new freeze point

## 2. Publication and recording
- [x] 2.1 Publish on Zenodo (human): metadata per the session's checklist (Publication → Preprint, CC BY 4.0,
      abstract as description, keywords), using the final built `dist/papers/01-vision/proposal.pdf`
- [x] 2.2 Record the published DOI in `README.md` (badge/link) and mark the publication revision as spent in
      `AGENTS.md`'s freeze note
- [x] 2.3 `openspec validate publish-vision-preprint --strict`; archive this change once published
