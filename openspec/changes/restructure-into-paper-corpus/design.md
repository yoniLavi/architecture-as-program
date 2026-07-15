## Context
The repo is a writing project with a tested toolchain. One `proposal.typ` at the root has been continuously
rewritten as the artifact grew; the Makefile builds `dist/proposal.{pdf,md,html}` from it, and the graphs,
scripts, poc, and tests support it. We are splitting the single document into an ordered corpus while keeping
one shared artifact. The main decisions are the freeze point, how a frozen paper stays faithful as the shared
artifact moves, and how the build/citation tooling generalises to N papers.

## Goals / Non-Goals
- **Goals:** a `papers/` corpus with a faithfully frozen Paper 1 and a relocated Paper 2; a shared top-level
  artifact backing all papers; a per-paper build; paper-aware citation hygiene; an honest methodology record.
- **Non-Goals:** rewriting Paper 2 into paper form; the evaluation harness; changing artifact behaviour;
  preprint submission; any retroactive posting or re-dating of Paper 1.

## Decisions
- **Decision: the freeze point is `59898cc~1` (June 2026), the last state before `poc/`.** The executable
  runtime demonstrator — not the static validator — is where the document crossed from vision to
  artifact-backed claim. `poc/` was introduced at `59898cc` (2026-07-14); the validator/typesetting tooling
  (graph JSON, type parser, static checks) predates it (April 2026) and belongs with the vision as "early
  evidence the static analyses are codeable." The document dated itself *June 2026* at `59898cc~1`, so
  freezing it with that date is faithful — the version genuinely existed in that form. (An earlier candidate,
  `9923c74~1` / "March 2026 / pure vision, no tooling", was considered and rejected: it excludes the static
  validator the vision legitimately cites as feasibility evidence.)
- **Decision: frozen papers are self-contained w.r.t. their inputs.** Paper 1 references
  `dist/graphs/customer-support.svg`, `dist/graphs/support-platform.svg`, and
  `dist/diagrams/typed-wiring.svg`, generated from `graphs/` and diagram sources that have since changed
  (e.g. `support-platform.json` gained `capability_identities` in 2026-07). If Paper 1 rebuilt from the
  current shared artifact its figures would silently acquire content that did not exist at freeze time — the
  freeze would leak. So Paper 1 carries its **own** copies of the exact graph JSONs and diagram sources as of
  `59898cc~1` under `papers/01-vision/`, and its build target reads only those. Only living papers build from
  the shared top-level artifact.
- **Decision: shared artifact stays at the top level; only documents move.** `graphs/`, `scripts/`, `poc/`,
  `tests/`, `citations.bib`, `openspec/` remain at the root as cross-paper resources (per the maintainer's
  call). A paper is a directory of document sources (plus, for frozen papers, its pinned inputs). This keeps
  one artifact, one test suite, one bibliography — the corpus is a set of *views* onto a shared body of work.
- **Decision: per-paper build outputs under `dist/papers/<id>/`.** `make build` iterates papers. The living
  paper(s) depend on the shared generated figures (`dist/graphs/*`, `dist/diagrams/*`); frozen papers depend
  on their own pinned inputs. Backward-compatible aliases for `dist/proposal.*` may be kept pointing at
  Paper 2 during transition, or dropped — decided at implementation.
- **Decision: citation hygiene is paper-aware, over a shared bib.** One `citations.bib`. `check-citations.py`
  treats an entry as used if *any* paper cites it (so an entry used only by Paper 1 is not flagged orphan when
  Paper 2 drops it), and Typst's broken-ref error still guards each paper individually.
- **Decision: the methodology claim is human-directed, AI-executed.** `METHODOLOGY.md` states the division of
  authority explicitly and points to git history + `openspec/changes/` as the evidence. No autonomy claim;
  overclaiming would undermine the very record it rests on.

## Risks / Trade-offs
- **Freeze leakage.** A frozen paper rebuilding from evolving inputs corrupts the record. → Self-contained
  frozen inputs + a build target that reads only them; a check that Paper 1's source matches `59898cc~1`.
- **Build/tooling churn.** Generalising a single-document build to a corpus touches Makefile, hooks, and
  citation scripts. → Keep the shared-artifact generation unchanged; add a per-paper layer on top.
- **Two near-identical papers.** Paper 2 today is ~75% identical to the freeze point (measured: 68/34
  line delta since `59898cc~1`). → This change only relocates Paper 2; a *follow-up* rewrites it into paper
  form so it earns separate-paper status. Recorded here so the rewrite is not forgotten.
- **Provenance vs redundancy.** Git already holds history. → The value of the freeze is citability and
  legibility (a stable, dated document), not preservation; stated plainly so we do not over-engineer it.

## Migration Plan
1. Create `papers/01-vision/` and `papers/02-demonstrator/`.
2. Freeze Paper 1: extract `proposal.typ` and its referenced graph/diagram inputs at `59898cc~1` into
   `papers/01-vision/`; add `ERRATA.md`; add a build target reading only its pinned inputs.
3. Move current `proposal.typ` → `papers/02-demonstrator/`, re-point its includes to the shared artifact.
4. Rework `Makefile` for per-paper outputs; make citation checks paper-aware; update hooks.
5. Add `METHODOLOGY.md`; update `AGENTS.md`/`CLAUDE.md`/`README`.
6. Verify: full corpus builds; Paper 1 renders with June-2026 figures (no identity labels); Paper 2 renders
   with current figures; citation hygiene green.

## Open Questions
- Directory naming: `papers/01-vision/` + `papers/02-demonstrator/` (ordered, content-named; dates live inside
  the documents) vs date-stamped dir names. Leaning content-named + ordinal prefix.
- Keep `dist/proposal.*` aliases pointing at Paper 2 for one transition, or cut over cleanly?
- Should `METHODOLOGY.md` grow into its own paper later (a paper *about* the process)? Deferred; noted as a
  possible future corpus entry.
