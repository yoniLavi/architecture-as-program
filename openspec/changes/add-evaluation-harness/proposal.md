# Change: A reproducible evaluation harness for the demonstrator

## Why
The demonstrator has the raw materials for an evaluation — a corpus of safe/unsafe graph mutations
(`poc`/`tests` already exercise `UNSAFE_VARIANTS`), a capability-boundary overhead benchmark
(`poc/sandbox/bench.py`), a prompt-injection demonstration (`poc/demo.py`), and a hostile-node suite that
contrasts the host and sandbox tiers — but no single harness that runs them and emits one **consolidated,
reproducible results artifact**. The demonstrator paper (Paper 2) needs an Evaluation section, and the honest
way to build one is to *generate* it from a harness that runs on every build, the way `dist/grammar.md` is
generated, so the numbers and verdicts in the paper cannot drift from the artifact that produced them.

## What Changes
- Add an evaluation harness that runs on build and emits a results artifact (e.g. `dist/evaluation.md`)
  consolidating:
  - **Mutation corpus verdicts** — for each safe/unsafe graph mutation, the *expected* verdict and the
    validator/runtime's *actual* verdict, with a summary (safe wirings accepted, unsafe wirings rejected, and
    the exact counts). The harness pins expected verdicts so a divergence **fails the build** — it is a
    regression guard, not merely a report.
  - **Overhead** — the capability-boundary crossing, per-node instantiation, and one-time compilation figures
    from the existing benchmark, folded into a table against the performance envelope.
  - **Prompt-injection attenuation** — what an adversarial message reaches and with what authority, and the
    host-vs-sandbox escape outcomes (the gap recorded as a test on the host tier; the escape *closed* on the
    sandbox tier).
- Keep the harness dependency-light and reuse the existing corpus/bench/demo rather than re-deriving them, so
  it is one seam over existing evidence, not a parallel implementation.
- Not in scope: new evaluation *dimensions* beyond what the artifact already supports (no user study, no
  at-scale performance claims, no new attack classes); the paper prose that consumes the artifact (that is the
  demonstrator-paper rewrite).

## Impact
- Affected specs: `evaluation` (ADDED — a new capability: the repository produces a reproducible evaluation
  artifact backing the demonstrator's claims, pinned as a regression guard).
- Affected code: a new harness script (e.g. `scripts/evaluate.py`) that imports the existing corpus, bench,
  and demo; `Makefile` (emit `dist/evaluation.md`); `.pre-commit-config.yaml` if the artifact is build-gated;
  `tests/` (the harness runs and its pinned verdicts hold).

## Dependencies
Complementary to `add-subgraph-execution` — once the composition runs end-to-end, the prompt-injection and
routing evidence can include the composed path — but not blocked by it (the corpus/bench/demo evidence exists
today). Feeds the Evaluation section of `rewrite-demonstrator-paper`.
