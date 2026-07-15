## 1. Corpus scaffolding
- [ ] 1.1 Create `papers/01-vision/` and `papers/02-demonstrator/`
- [ ] 1.2 Decide and record final directory naming (content-named + ordinal prefix vs date-stamped)

## 2. Freeze Paper 1 (the founding vision)
- [ ] 2.1 Extract `proposal.typ` at `59898cc~1` into `papers/01-vision/` (keep its *June 2026* date verbatim)
- [ ] 2.2 Copy the exact inputs it references at that commit — `graphs/customer-support.json`,
      `graphs/support-platform.json`, `graphs/schema.json`, and the `typed-wiring` diagram source — into
      `papers/01-vision/` so the paper is self-contained and cannot drift
- [ ] 2.3 Add `papers/01-vision/ERRATA.md` (empty but for a header explaining the errata-only policy)
- [ ] 2.4 Add a build target that renders Paper 1 from *only* its pinned inputs (never the shared artifact)

## 3. Establish Paper 2 (the demonstrator paper)
- [ ] 3.1 Move the current root `proposal.typ` → `papers/02-demonstrator/`
- [ ] 3.2 Re-point its figure includes to the shared top-level artifact (`dist/graphs/*`, `dist/diagrams/*`)
- [ ] 3.3 Add a reference from Paper 2 to Paper 1 as the archived original vision (minimal; full rewrite is a
      follow-up)

## 4. Build + tooling for a corpus
- [ ] 4.1 Rework `Makefile`: per-paper outputs under `dist/papers/<id>/`; shared-artifact generation
      (graphs/diagrams/grammar) unchanged and reused by living papers
- [ ] 4.2 Make `scripts/check-citations.py` paper-aware (an entry is used if any paper cites it)
- [ ] 4.3 Update `.pre-commit-config.yaml` so `make build` / citation checks cover the corpus
- [ ] 4.4 Decide whether to keep `dist/proposal.*` aliases for one transition or cut over

## 5. Methodology + docs
- [ ] 5.1 Add top-level `METHODOLOGY.md`: human-directed, AI-executed, spec-driven; git + `openspec/changes/`
      as the evidence trail; explicit division of authority (no autonomy claim)
- [ ] 5.2 Update `AGENTS.md`/`CLAUDE.md` (new layout, per-paper build, freeze policy) and `README`

## 6. Verify + wrap-up
- [ ] 6.1 Full corpus builds: Paper 1 renders with June-2026 figures (no `capability_identities` labels);
      Paper 2 renders with current figures
- [ ] 6.2 Add a check that Paper 1's source matches `proposal.typ@59898cc~1` (guard against silent edits to a
      frozen paper)
- [ ] 6.3 Full gate green: ruff, pytest, corpus `make build`, citation hygiene

## Notes for whoever picks this up
- The freeze is only faithful if Paper 1 reads *its own* pinned graph/diagram inputs. Do not let it build from
  the shared `graphs/` — `support-platform.json` has drifted since June 2026 and would leak later content into
  the frozen figures.
- This change relocates Paper 2; it does not rewrite it. The ~75%-overlap problem is solved by the follow-up
  paper-form rewrite + evaluation harness, not here.
