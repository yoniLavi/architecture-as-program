## 1. Bibliography and related work (independent of the split; do first)

- [ ] 1.1 Add agent-security entries to `citations.bib`: Greshake et al. (indirect prompt injection,
      AISec'23), Debenedetti et al. (CaMeL, "Defeating Prompt Injections by Design", 2025),
      Beurer-Kellner et al. (design patterns for securing LLM agents, 2025), Debenedetti et al.
      (AgentDojo, NeurIPS D&B 2024). Verify each against its primary source before citing.
- [ ] 1.2 Write the LLM-agent-security related-work subsection positioning the signal graph against CaMeL
      (static/architectural/pre-execution + import-table backstop vs runtime/interpreter/intra-agent) and
      against the pattern catalogue (the canonical graph instantiates several patterns, typed)
- [ ] 1.3 Note AgentDojo in `sec:threats` as an available benchmark not used, so the curated-corpus limit
      names its own remedy

## 2. Paper 2 → the systems paper

- [ ] 2.1 Retitle (title block, `#set document`, Makefile citable-name target); update abstract to lead with
      the confinement-derivation result
- [ ] 2.2 Rewrite `sec:claim` so the central claim leads with capability-surface derivation and keeps the
      trust-lattice result second
- [ ] 2.3 Cut §2: drop `sec:workflow`, `sec:time`, `sec:runtime`; compress `sec:frp-brief` to one paragraph;
      keep `sec:signal-graph`, `sec:concrete-graph`, `sec:security`
- [ ] 2.4 Reduce `sec:inspector` to a mention inside `sec:trace`, retaining `fig:inspector`
- [ ] 2.5 Move §5, §7, §8.5, Annex A out (to Paper 3); leave a two-paragraph "what this does and does not
      substantiate" in its place
- [ ] 2.6 Split §6: technical prior art stays, method/SDD framing moves; add the §1.2 subsection
- [ ] 2.7 Verify no dangling cross-reference to a moved section; confirm page count ≤ ~18

## 3. Paper 3 → the method paper

- [ ] 3.1 Scaffold `papers/03-method/proposal.typ` and the `Makefile` P3 block mirroring P2 (PDF/md/HTML +
      citable name); confirm `dist/papers/03-method/` builds
- [ ] 3.2 Draft the protocol section: freeze, publish under DOI, guard via `scripts/check-freeze.py`,
      errata-only, report unrevised — with the mechanisation as the contribution, not the aspiration
- [ ] 3.3 Move in the predictions-and-outcomes accounting (`tab:outcomes`) and the four corrections; set the
      visual-editor row to *Not attempted* with an inspector footnote
- [ ] 3.4 Move in the research agenda and threats-from-method; add Annex A
- [ ] 3.5 Cite Paper 2 for every figure and number; assert Paper 3 interpolates no evaluation data

## 4. Corpus plumbing

- [ ] 4.1 Update `papers/README.md` (three papers, two living), root `README.md` links, `AGENTS.md`/`CLAUDE.md`
      ("the paper you normally edit" now depends on whether the change is evidence or accounting)
- [ ] 4.2 Decide and apply the `dist/proposal.*` deprecated-alias question from `design.md`
- [ ] 4.3 `make build` green; `scripts/check-citations.py` clean over three papers; freeze guard still passes;
      full test suite unchanged

## 5. Publication readiness (no publishing)

- [ ] 5.1 Confirm both PDFs emit under citable names and carry no stale "July 2026" / provisional-year drift
- [ ] 5.2 Draft Zenodo metadata for Paper 2 (title, abstract, keywords, licence CC BY 4.0) for the author to
      review — publishing itself stays a separate, explicitly-approved step
