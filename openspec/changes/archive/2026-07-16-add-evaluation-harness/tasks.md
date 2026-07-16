## 1. Harness
- [x] 1.1 Add `poc/evaluate.py` that imports the existing mutation corpus (`UNSAFE_VARIANTS`), the overhead
      bench, and the prompt-injection demo — a consolidation layer, not a re-implementation
      (**`poc/`, not `scripts/`** — see the decision recorded in `design.md`)
- [x] 1.2 Pin an expected verdict per mutation (safe → accepted; unsafe → rejected, with reason class where it
      matters) and fail if actual diverges

## 2. Artifact
- [x] 2.1 Emit `dist/evaluation.md`: the corpus verdict table + summary counts, the overhead table against the
      performance envelope, and the prompt-injection/host-vs-sandbox tier results
- [x] 2.2 State in the artifact that the corpus is curated and illustrative (counts, not a soundness claim);
      report both tiers honestly (host escapes succeed = the gap; sandbox escapes fail = confinement)
- [x] 2.3 Wire `make build` to generate the artifact; keep the bench pass small and gate `--live` out of the
      default build (the harness runs in ~1.7s and is `StubLLM`-only — there is no `--live` path into it)

## 3. Tests
- [x] 3.1 The harness runs and produces the artifact; its pinned corpus verdicts hold
- [x] 3.2 A deliberately wrong expected verdict makes the harness fail (the guard actually guards)
      — and so does a rejection caught by the *wrong reason class*, and an unpinned mutation

## 4. Wrap-up
- [x] 4.1 Full gate green: ruff, pytest (`--group poc`), `make build` (artifact regenerates)

## Notes for whoever picks this up
- Import the corpus/bench/demo; do not copy them. One definition, two consumers (pytest + the harness).
- The artifact is a regression guard, not a brochure: a divergent verdict must fail the build.
- Keep the soundness caveat visible — a fully-caught curated corpus is illustrative, not a proof.
