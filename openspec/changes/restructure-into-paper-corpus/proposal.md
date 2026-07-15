# Change: Restructure the repository into a longitudinal paper corpus

## Why
The repository began as a single research *proposal* (`proposal.typ`) and has since grown a tested
demonstrator (validator, executable runtime, two enforcement tiers, capability identity/revocation/rotation).
The document has quietly outgrown "proposal": it now makes artifact-backed claims a proposal cannot. But it is
still one live, continuously-rewritten file, which blurs two things that should be kept distinct — the
*founding vision* (conditional claims, no artifact) and the *demonstrator paper* (substantiated claims +
evaluation + agenda) — and erases the provenance that makes this repo interesting: a research program carried
out incrementally, with human direction and an AI agent as the instrument, recorded in git history and
OpenSpec change proposals.

This change reframes the repository as a **corpus of papers backed by a shared, evolving research artifact**.
The founding vision is frozen as Paper 1 (faithful to its pre-demonstrator state); the current document
becomes Paper 2, the demonstrator paper, which references Paper 1 and is rewritten into paper form over
subsequent changes. The shared artifact (`graphs/`, `scripts/`, `poc/`, `tests/`, `citations.bib`) stays at
the top level and backs every paper. This makes the longitudinal, AI-driven-with-human-direction nature of
the work explicit and citable, and gives each paper a clean, bounded identity.

## What Changes
- Introduce a top-level `papers/` directory holding one sub-directory per paper. Documents live here; the
  shared research artifact stays at the repository root and backs all papers.
- **Freeze Paper 1 (the founding vision).** Copy `proposal.typ` as it stood at commit `59898cc~1` (the last
  state *before* the executable runtime demonstrator `poc/` was introduced; the document dates itself
  *June 2026*) into `papers/01-vision/`. Frozen papers are **self-contained**: Paper 1 carries its own copies
  of the graph JSONs and diagram sources it references as of that commit, so it rebuilds identically and never
  drifts as the shared artifact evolves. Paper 1 is errata-only thereafter (corrections recorded in an
  `ERRATA.md`, dated, never silent rewrites).
- **Establish Paper 2 (the demonstrator paper).** Move the current `proposal.typ` to `papers/02-demonstrator/`.
  Paper 2 builds from the shared top-level artifact and, in later changes, is rewritten into paper form
  (Intro-with-claim → Design → Implementation → Evaluation → Related Work → Research Agenda) and references
  Paper 1 as the archived original vision. This change only relocates and re-points it; the rewrite is
  follow-up work.
- **Rework the build for a corpus.** `make build` produces per-paper outputs under `dist/papers/<id>/`; the
  living paper(s) build from the shared artifact, frozen papers build from their own self-contained inputs.
  Citation hygiene becomes paper-aware (each paper's citations resolve against the shared `citations.bib`; the
  unused-entry check accounts for all papers).
- **Document the methodology.** Add a top-level `METHODOLOGY.md` describing the research process honestly:
  human-directed, AI-executed, spec-driven via OpenSpec, with git history and `openspec/changes/` as the
  evidence trail. State the division of authority plainly (the human is the principal investigator setting
  scope and decisions; the agent is the instrument) — no claim of autonomous research.
- Update `AGENTS.md`/`CLAUDE.md`, pre-commit hooks, and `README` to the new layout.
- Not in scope: rewriting Paper 2 into paper form (a follow-up); the evaluation harness that Paper 2's
  Evaluation section needs (a follow-up); any change to artifact behaviour (`poc/`, validator, graphs) beyond
  copying frozen inputs for Paper 1; posting anything as a preprint.

## Impact
- Affected specs: `paper-corpus` (ADDED — a new capability describing the repository's paper-corpus structure
  and its invariants).
- Affected code/layout: new `papers/` tree; `Makefile` (per-paper targets); `.pre-commit-config.yaml`
  (paper-aware `make build` / citation checks); `scripts/check-citations.py` (paper-aware); `AGENTS.md` /
  `CLAUDE.md`, `README`; new `METHODOLOGY.md`; frozen copies of graph/diagram inputs under `papers/01-vision/`.
- Provenance: git already records the history; freezing Paper 1 as a self-contained, dated document makes that
  history legible and citable rather than reconstructable only via SHAs.

## Dependencies
Independent of the artifact-extending changes. It unblocks the paper-form rewrite of Paper 2 and the
evaluation-harness change, which together make Paper 2 preprint-ready.
