# Tasks

## 1. The derivation's negative control

- [x] 1.1 Add `NEGATIVE_CONTROLS` to `poc/evaluate.py`: `hostile_ungranted` held against
      `ParseMessage`'s `with` clause, pinned to over-grant exactly `aap:caps/kb-read`
- [x] 1.2 Add `check_controls()`; `run()` refuses to write the artifact if a control is
      not caught, or is caught for a different interface
- [x] 1.3 Report the control in `dist/evaluation.md` and `evaluation.json`, separate
      from the agreeing rows
- [x] 1.4 Tests: the real control is caught; a control that agrees fails the pin; a
      control caught on the wrong interface fails the pin

## 2. Paper 2

- [x] 2.1 Abstract and conclusion: scope the opening claim; `crossing_us` → `crossing_magnitude`
- [x] 2.2 §4.1: report the negative control, interpolated
- [x] 2.3 §6.2: CAmkES/capDL, conceding the stronger link and stating the difference
- [x] 2.4 §6.1: Language-Based Agent Control
- [x] 2.5 §6.6: McCann's purity gate and Wassette
- [x] 2.6 Date line; single-line title-block note so pandoc keeps its spaces

## 3. Paper 3

- [x] 3.1 Date line
- [x] 3.2 Lattice agenda item: Filament keeps the lattice user-defined

## 4. Records

- [x] 4.1 `citations.bib`: Klein et al. 2018, Kuz et al. 2010, Zhou et al. 2026, McCann 2026,
      Wassette, Filament
- [x] 4.2 `docs/PRIOR-ART.md`: debts resolved; new findings recorded
- [x] 4.3 `docs/ROADMAP.md` "Start here" refreshed
- [x] 4.4 Publication checklist and Zenodo metadata in this change directory
- [x] 4.5 `AGENTS.md` test count

## 5. Verification

- [x] 5.1 `make build`, `check-citations`, `check-freeze`, `check-hedges`, pre-commit green
- [x] 5.2 Rendered PDF/MD read at the changed passages
- [x] 5.3 `openspec validate prepare-paper-2-publication --strict`

## 6. Found in the doing

- [x] 6.1 Abstract: "only the latter survives a misconfigured deployment" referred to the host's
      configuration, which inverts the claim; now "the former"
- [x] 6.2 §6 opening: "generated implementations executing within capability-restricted sandboxes"
      implied the demonstrator generates bodies; "generated" removed
- [x] 6.3 `scripts/resolve-crossrefs.lua`: pandoc 3.11 parses a centred prose block as a `Div`,
      which the filter silently dropped, taking the living papers' process and corpus notes out of
      the Markdown and HTML. Now kept under an opt-in `keep-centred-notes` metadata flag that only
      Papers 2 and 3 set, so Paper 1's outputs are byte-identical to a build from the pre-change
      commit (checked for the Markdown, the HTML, and the PDF text)

## 7. Publication (handed over from `merge-and-condense-papers`, 30 September 2026)

- [ ] 7.1 Author's end-to-end read of the merged paper
- [ ] 7.2 Upload per `publication-checklist.md`, with *Continues* as the only relation to
      Paper 1
- [ ] 7.3 `openspec archive prepare-paper-2-publication`
