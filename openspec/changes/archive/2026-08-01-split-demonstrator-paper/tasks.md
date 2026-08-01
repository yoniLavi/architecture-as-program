## 1. Bibliography and related work (independent of the split; do first)

- [x] 1.1 Add agent-security entries to `citations.bib`: Greshake et al. (indirect prompt injection,
      AISec'23), Debenedetti et al. (CaMeL, "Defeating Prompt Injections by Design", 2025),
      Beurer-Kellner et al. (design patterns for securing LLM agents, 2025), Debenedetti et al.
      (AgentDojo, NeurIPS D&B 2024). Verify each against its primary source before citing.
- [x] 1.2 Write the LLM-agent-security related-work subsection positioning the signal graph against CaMeL
      (static/architectural/pre-execution + import-table backstop vs runtime/interpreter/intra-agent) and
      against the pattern catalogue (the canonical graph instantiates several patterns, typed)
- [x] 1.3 Note AgentDojo in `sec:threats` as an available benchmark not used, so the curated-corpus limit
      names its own remedy

## 2. Paper 2 → the systems paper

- [x] 2.1 Retitle (title block, `#set document`, Makefile citable-name target); update abstract to lead with
      the confinement-derivation result
- [x] 2.2 Rewrite `sec:claim` so the central claim leads with capability-surface derivation and keeps the
      trust-lattice result second
- [x] 2.3 Cut §2: drop `sec:workflow`, `sec:time`, `sec:runtime`; compress `sec:frp-brief` to one paragraph;
      keep `sec:signal-graph`, `sec:concrete-graph`, `sec:security`
- [x] 2.4 Reduce `sec:inspector` to a mention inside `sec:trace`, retaining `fig:inspector`
- [x] 2.5 Move §5, §7, §8.5, Annex A out (to Paper 3); leave a two-paragraph "what this does and does not
      substantiate" in its place
- [x] 2.6 Split §6: technical prior art stays, method/SDD framing moves; add the §1.2 subsection
- [x] 2.7 Verify no dangling cross-reference to a moved section; confirm page count ≤ ~18

## 3. Paper 3 → the method paper

- [x] 3.1 Scaffold `papers/03-method/proposal.typ` and the `Makefile` P3 block mirroring P2 (PDF/md/HTML +
      citable name); confirm `dist/papers/03-method/` builds
- [x] 3.2 Draft the protocol section: freeze, publish under DOI, guard via `scripts/check-freeze.py`,
      errata-only, report unrevised — with the mechanisation as the contribution, not the aspiration
- [x] 3.3 Move in the predictions-and-outcomes accounting (`tab:outcomes`) and the four corrections; set the
      visual-editor row to *Not attempted* with an inspector footnote
- [x] 3.4 Move in the research agenda and threats-from-method; add Annex A
- [x] 3.5 Cite Paper 2 for every figure and number; assert Paper 3 interpolates no evaluation data

## 4. Corpus plumbing

- [x] 4.1 Update `papers/README.md` (three papers, two living), root `README.md` links, `AGENTS.md`/`CLAUDE.md`
      ("the paper you normally edit" now depends on whether the change is evidence or accounting)
- [x] 4.2 Decide the `dist/proposal.*` deprecated-alias question from `design.md` — **decided: keep them.**
      `design.md` leaned toward dropping, but Paper 2's directory and therefore its published GitHub Pages
      URLs are unchanged by the split, so the aliases still resolve correctly and dropping them would break
      live inbound links for no benefit. Removing them is outward-facing and stays the author's call.
- [x] 4.3 `make build` green; `scripts/check-citations.py` clean over three papers; freeze guard still passes;
      full test suite unchanged

## 5. Publication readiness (no publishing)

- [x] 5.1 Confirm both PDFs emit under citable names and carry no stale "July 2026" / provisional-year drift
- [x] 5.2 Draft Zenodo metadata for Paper 2 → `zenodo-metadata.md` in this change directory. Publishing
      itself stays a separate, explicitly-approved step and has **not** been done.

## 6. Outcome notes

- **Page counts**: Paper 2 landed at **34pp** (from 45), Paper 3 at **15pp**. The proposal targeted ~18pp for
  Paper 2; that figure came from Onward!'s limit, and the venue decision is Zenodo, which has no page limit.
  The cuts that improved the paper — one claim, no duplicated accounting, related work consolidated from 13
  subsections to 8 — are applied. Cutting the remaining ~16pp would mean removing evidence, limitations, or
  hedges, which the repo's own rule forbids ("length is a target, not a quota"). Revisit only if a
  page-limited venue is chosen later.
- **`tab:outcomes` visual-editor row** moved from *Partial* to *Not attempted*, per the new spec requirement
  that a demo cannot move a verdict. Paper 3 §3.4 reports that change *as an instance of the protocol* — an
  earlier draft read generously and was corrected by review rather than by tooling — which is a stronger use
  of it than silently fixing the row.
