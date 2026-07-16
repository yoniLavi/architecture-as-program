## Context
Evidence is scattered across the test suite (`UNSAFE_VARIANTS` mutations, the two-tier hostile-node suite),
`poc/sandbox/bench.py` (overhead), and `poc/demo.py` (prompt injection). Each runs, but nothing collects them
into one artifact a paper can cite. This change adds a thin harness that runs the existing evidence and writes
a consolidated, build-time results file — the evaluation analogue of `dist/grammar.md`.

## Goals / Non-Goals
- **Goals:** one generated evaluation artifact; pinned mutation-corpus verdicts that fail on divergence;
  overhead and prompt-injection/tier results folded in; reuse of existing corpus/bench/demo.
- **Non-Goals:** new evaluation dimensions; a user study; at-scale performance; the paper prose consuming it.

## Decisions
- **Decision: generate the artifact, do not hand-maintain it.** The harness writes `dist/evaluation.md` on
  build, so every figure and verdict in the paper traces to a run. This mirrors the repo's existing
  "documented grammar generated from the parser" discipline — no number lives only in prose.
- **Decision: the corpus is a regression guard, not a report.** Each mutation carries an *expected* verdict
  (safe → accepted, unsafe → rejected, with the reason class where it matters — e.g. laundering caught as a
  lattice violation). The harness asserts actual == expected and fails otherwise. A report that cannot fail
  would let the central security claim rot silently.
- **Decision: reuse, don't re-derive.** The harness imports `UNSAFE_VARIANTS`, the bench, and the demo rather
  than re-implementing mutations or timing. It is a presentation/consolidation layer; the evidence stays owned
  by the code that already tests it.
- **Decision: state tiers honestly in the artifact.** The host tier's escapes *succeed* (recorded as the gap);
  the sandbox tier's *fail* (confinement). The artifact reports both, so the evaluation cannot be misread as a
  stronger guarantee than the demonstrator provides — the same honesty the proposal already keeps in prose.

## Risks / Trade-offs
- **Double source of truth (tests vs harness).** → The harness *imports* the test corpus/bench/demo; it does
  not copy them. One definition, two consumers (pytest and the harness).
- **Build-time cost.** Running the bench and demo on every build adds seconds. → Keep the harness's bench pass
  small (best-of-few, as the bench already does) and gate the heavier `--live` demo out of the default build.
- **Overclaiming from a curated corpus.** A hand-picked mutation set that is 100% caught can read as "provably
  secure." → The artifact states the corpus is curated and illustrative, and reports counts, not a soundness
  claim; Technical Note A's soundness caveat stands.

## Migration Plan
Additive. A new script and a new `dist/` artifact; existing tests unchanged (the harness reuses them). The
build gains one target.

## Open Questions
- ~~Artifact format~~ **Resolved: Markdown** (`dist/evaluation.md`), matching `dist/grammar.md`, so a paper
  can include it directly with no rendering step.
- Whether the prompt-injection section should run the composed (`SupportPlatform`) path once
  `add-subgraph-execution` lands, in addition to the single-graph `CustomerSupport` path. (Deferred to that
  change's completion. The corpus already *assembles* `SupportPlatform`; it cannot yet execute it.)

## Decisions taken during implementation
- **Decision: the harness lives in `poc/evaluate.py`, not `scripts/evaluate.py`.** The proposal said "e.g.
  `scripts/evaluate.py`", but `scripts/` is stdlib-only by a stated rule (`pyproject.toml`: "the stdlib-only
  validator/parser in scripts/ must never import these"). The harness is a *consumer* of `poc` — variants,
  runtime, bench, demo — so it belongs with the code it imports, and the layering rule stays literally true
  rather than surviving on a technicality about guarded imports. The Makefile invokes it as a module, exactly
  as `poc.demo` and `poc.sandbox.bench` are already run.
- **Decision: the full artifact is generated in every environment; the build gains the `poc` group.** The
  overhead and sandbox-tier sections need `wasmtime`, which was absent from the build path (`dependencies = []`,
  and CI ran `make build` with no `--group poc`). The alternative — degrade gracefully and label unmeasured
  sections — was rejected: it would mean the same commit produced a different paper on different machines, and
  the published Evaluation section would carry holes precisely where the artifact is supposed to remove
  hand-maintenance. `make build` therefore runs the harness via `uv run --group poc`, which installs the group
  on demand and so needs no CI change. The cost is honest and recorded: the build is no longer stdlib-only
  (noted in `pyproject.toml`), and the pre-commit `make-build` hook now depends on wasmtime.
- **Decision: pin the reason class, not just the verdict.** `launder_trust` type-checks on every edge and is
  rejected by the trust lattice; `bypass_pipeline` is rejected as an edge type mismatch. Pinning only
  "rejected" would let laundering start failing for the *wrong* reason — an edge typo — while the table stayed
  green and the trust-lattice claim quietly stopped being tested. The two signatures are disjoint on the
  current corpus, and `classify` treats a case matching both (or neither) as a divergence rather than guessing.
- **Decision: the corpus pins itself against silent growth.** `run_corpus` asserts its pinned mutation set
  *equals* `UNSAFE_VARIANTS`. Adding a variant without pinning it fails the build, rather than being counted as
  caught without ever being checked.
- **Decision: the canonical graphs are corpus cases too.** A validator that rejected everything would catch
  every unsafe wiring and be worthless, so the safe half is what keeps the unsafe half meaningful.
- **Decision: the artifact records the machine.** The overhead figures are wall-clock timings and therefore
  machine-dependent; the artifact states the platform/processor/python/wasmtime that produced them and claims
  only an order of magnitude against the envelope. This is a known consequence of generating rather than
  pinning the numbers: the same commit yields slightly different figures on different hardware.

## Known duplication (accepted, small)
`poc/demo.py` narrates the host-vs-sandbox escapes for a human; `poc/evaluate.py` probes them as structured
facts; `tests/test_poc_sandbox.py` asserts them. That is three derivations of the same underlying facts. The
mutations and the timings — the two things the design named — are genuinely imported, not re-derived. Folding
the escape probes into one definition would mean either the demo importing the harness or a new shared module;
both were judged more churn than the ~15 lines are worth *for now*. If a fourth consumer appears, collapse
them: `poc/demo.py` becoming a presenter over `poc/evaluate.py`'s facts is the natural shape.
