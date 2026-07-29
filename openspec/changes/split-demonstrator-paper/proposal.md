# Change: Split Paper 2 into a systems paper and a method paper

## Why

Paper 2 is 45 pages against a stated target in the low-to-mid 30s, and the overrun is not fat — it is
two papers sharing one document. They have different claims, different evidence, and different readers:

- A **systems claim**: a graph carrying capability and trust annotations admits static analysis that
  rejects laundering which type-checks on every edge, and a node's declared capabilities mechanically
  determine the import surface of its compiled artifact — checkable against the built binary.
- A **method claim**: a design's predictions, frozen and published before implementation and then reported
  unrevised, is a usable research protocol; here is one complete instance and the four design corrections
  it produced.

Fused, each weakens the other. The systems reader wades through §5's prediction accounting and §7's
three-phase agenda to reach the evaluation; the method reader wades through WIT interfaces and µs timings
to reach the accounting. Neither paper fits a venue: no venue takes 45 pages of this, and the cut that
gets to ~18 has to drop one claim entirely — which is the split, made reluctantly instead of deliberately.

Two further defects are fixed in the same pass, because both are cheap now and expensive later:

- **The agent-security literature is entirely absent.** `citations.bib` has 80 entries and none on prompt
  injection or LLM-agent security, yet prompt-injection attenuation is a listed contribution with its own
  evaluation section. The closest prior art — CaMeL @debenedetti_defeating_2025, which enforces
  capability-based data-flow policies with value provenance to defeat prompt injection — is uncited. This
  is the single most likely cause of a hostile review, and engaging it *strengthens* the position: CaMeL
  enforces at runtime inside one agent's execution; the signal graph enforces statically, before anything
  runs, across a composed system, with the component import table as the backstop.
- **The inspector is over-reported.** §3.7 spends ~500 words and a figure on a renderer of two artifacts
  checked elsewhere, and `tab:outcomes` records "The visual graph editor — Partial" on its strength. Demos
  earn attention for the program and will keep being built to the repo's usual evidence discipline, but in
  the papers they get a mention, not a section.

## What Changes

- **Paper 2 becomes the systems paper**, retitled, in `papers/02-demonstrator/` (directory name kept —
  the published GitHub Pages URLs point at it). Target ~18 pages.
  - §2 (Design) cut from ~13pp to ~4pp: keep the signal graph, `with` clauses, trust annotations, and the
    concrete graph; drop the FRP history to a paragraph, and drop the workflow, time-as-structural-dimension,
    and intended-runtime subsections wholesale — they are Paper 1's argument and Paper 3's agenda.
  - Promote the artifact-vs-configuration confinement result from a §3.3 aside to the paper's lead claim:
    the abstract, the central-claim block, and the contributions list all currently lead with the validator,
    which is the *expected* result rather than the surprising one.
  - Add a related-work subsection on LLM-agent security and position against it.
  - Inspector: reduced to a mention inside the trace section, with the figure retained.
- **New Paper 3 (`papers/03-method/`), the method paper.** Target ~12 pages. Takes over §5 (predictions and
  outcomes, including the four corrections), §7 (research agenda), §8.5 (threats from the method), and
  Annex A; adds the protocol itself as its subject — freeze, publish under DOI, guard in CI via
  `scripts/check-freeze.py`, errata-only, report unrevised.
- **`tab:outcomes` moves to Paper 3** and its visual-editor row moves from *Partial* back to *Not attempted*,
  with the inspector noted in a footnote. The verdict follows the underlying capability (authoring), not the
  demo.
- **Zenodo sequencing**: Paper 2 publishes first and takes a DOI; Paper 3 cites that DOI. Publishing is an
  outward-facing act and stays a separate, explicitly-approved human step — this change makes the papers
  ready, it does not post them.
- Not in scope: any artifact or evaluation change; editing Paper 1; the act of publishing; the "useful toy"
  programme in `ROADMAP.md`, which is later work under its own proposals.

## Impact

- Affected specs: `paper-corpus` (2 MODIFIED requirements, 2 ADDED)
- Affected papers: `papers/02-demonstrator/proposal.typ` (rewrite + cut), `papers/03-method/` (new)
- Affected code/docs: `Makefile` (a P3 block mirroring P2), `citations.bib` (agent-security entries),
  `papers/README.md`, `README.md`, `AGENTS.md`/`CLAUDE.md` (the "paper you normally edit" pointer now names
  two living papers)
- No artifact behaviour change: the runtime, validator, evaluation harness, and inspector are untouched, so
  every interpolated figure keeps its provenance.

## Dependencies

Depends on `add-graph-inspector-ui` (archived 2026-07-29) — the inspector must exist before its reporting
can be deliberately bounded. Independent of the roadmap work.
