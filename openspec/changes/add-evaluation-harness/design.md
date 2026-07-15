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
- Artifact format: Markdown table (`dist/evaluation.md`) for direct inclusion, or JSON + a rendering step?
  (Leaning Markdown, matching `dist/grammar.md`.)
- Whether the prompt-injection section should run the composed (`SupportPlatform`) path once
  `add-subgraph-execution` lands, in addition to the single-graph `CustomerSupport` path. (Deferred to that
  change's completion.)
