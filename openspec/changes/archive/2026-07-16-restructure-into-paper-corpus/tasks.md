## 1. Corpus scaffolding
- [x] 1.1 Create `papers/01-vision/` and `papers/02-demonstrator/`
- [x] 1.2 Use `papers/01-vision/` and `papers/02-demonstrator/` (content-named + ordinal; dates inside docs)

## 2. Freeze Paper 1 (the founding vision)
- [x] 2.1 Extract `proposal.typ` at `59898cc~1` into `papers/01-vision/` (keep its *June 2026* date verbatim)
- [x] 2.2 Copy the exact inputs it references at that commit — `graphs/customer-support.json`,
      `graphs/support-platform.json`, `graphs/schema.json`, and the `typed-wiring` diagram source — into
      `papers/01-vision/` so the paper is self-contained and cannot drift
- [x] 2.3 Add `papers/01-vision/ERRATA.md` (empty but for a header explaining the errata-only policy)
- [x] 2.4 Add a build target that renders Paper 1 from *only* its pinned inputs (never the shared artifact)

## 3. Establish Paper 2 (the demonstrator paper)
- [x] 3.1 Move the current root `proposal.typ` → `papers/02-demonstrator/`
- [x] 3.2 Re-point its figure includes to the shared top-level artifact (`dist/graphs/*`, `dist/diagrams/*`)
- [x] 3.3 Add a reference from Paper 2 to Paper 1 as the archived original vision (minimal; full rewrite is a
      follow-up)

## 4. Build + tooling for a corpus
- [x] 4.1 Rework `Makefile`: per-paper outputs under `dist/papers/<id>/`; shared-artifact generation
      (graphs/diagrams/grammar) unchanged and reused by living papers
- [x] 4.2 Make `scripts/check-citations.py` paper-aware (an entry is used if any paper cites it)
- [x] 4.3 Update `.pre-commit-config.yaml` so `make build` / citation checks cover the corpus
- [x] 4.4 Emit `dist/proposal.{pdf,md,html}` as deprecated aliases to Paper 2 for one transition (note in
      Makefile + README that they will be removed once inbound/GitHub Pages links are updated)

## 5. Methodology + docs
- [x] 5.1 Add top-level `METHODOLOGY.md`: human-directed, AI-executed, spec-driven; git + `openspec/changes/`
      as the evidence trail; explicit division of authority (no autonomy claim)
- [x] 5.2 Update `AGENTS.md`/`CLAUDE.md` (new layout, per-paper build, freeze policy) and `README`

## 6. Verify + wrap-up
- [x] 6.1 Full corpus builds: Paper 1 renders with June-2026 figures (no `capability_identities` labels);
      Paper 2 renders with current figures
- [x] 6.2 Add a check that Paper 1's source matches `proposal.typ@59898cc~1` (guard against silent edits to a
      frozen paper)
- [x] 6.3 Full gate green: ruff, pytest, corpus `make build`, citation hygiene

## Notes for whoever picks this up
- The freeze is only faithful if Paper 1 reads *its own* pinned graph/diagram inputs. Do not let it build from
  the shared `graphs/` — `support-platform.json` has drifted since June 2026 and would leak later content into
  the frozen figures.
- This change relocates Paper 2; it does not rewrite it. The ~75%-overlap problem is solved by the follow-up
  paper-form rewrite + evaluation harness, not here.

## Implementation notes (as built)
- **How the frozen paper's figures resolve without editing its byte-identical source.** Paper 1's
  `proposal.typ` references figures relatively (`dist/…`) and the shared bibliography (`citations.bib`).
  Two committed symlinks make these resolve correctly: `papers/01-vision/dist → ../../dist/papers/01-vision`
  (its own figure tree; works for both typst's file-relative and pandoc's cwd-relative resolution) and
  `papers/01-vision/citations.bib → ../../citations.bib` (the shared bib). typst compiles with `--root $(ROOT)`
  so the symlinked figures (real path under `dist/`) stay inside the project root; pandoc runs from the paper
  directory so its cwd-relative `dist/…` paths resolve through the symlink.
- **Living paper path convention.** Paper 2 references the shared artifact root-absolutely (`/dist/…`,
  `/citations.bib`), which resolves for typst (`--root $(ROOT)`) and pandoc (cwd = repo root) alike, with no
  duplication of the shared graph JSONs into the paper directory.
- **Freeze guard.** `scripts/check-freeze.py` compares the frozen sources against `59898cc~1` and fails on any
  drift; it is wired into `make build` and as a dedicated pre-commit hook (`check-freeze`). It skips with a
  warning when the freeze commit is unavailable (shallow checkout), and CI now checks out with `fetch-depth: 0`
  so the guard is effective there too.
- **Cleanup scripts** (`clean-html.py`, `clean-markdown.py`) now strip both relative (`dist/…`, frozen paper)
  and root-absolute (`/dist/…`, living paper) figure prefixes; `generate-graph.py` takes an optional output dir
  so the frozen paper can regenerate its figures into its own tree.
