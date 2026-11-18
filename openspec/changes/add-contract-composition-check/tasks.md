# Tasks

Every session first checks the feed recorder (`operate-feed-triage` 0.2) and `git status`.

## 0. Approval

- [ ] 0.1 The author approves this proposal. Record the date here. Nothing below starts
  before this box is checked.

## 1. The analysis

- [ ] 1.1 Port the implication check from `spikes/specified-architecture/s2/implication.py`
  into `scripts/`, stdlib-only. Verify: the spike's 25 tests, moved to `tests/`, pass.
- [ ] 1.2 Wire it into the validator as warnings, with contradicted and vacuous edges as
  errors. Verify:
  - a corpus case pinned to the contradicted reason class;
  - the canonical graphs still validate, their warnings listed.
- [ ] 1.3 Fuzz every verdict class against `poc.contracts`' evaluator, with the widened
  value set. Fix or pin `x >= 0 ⇒ len(x) >= 0`. Verify: the fuzz fails if any verdict is
  made unsound by hand.

## 2. Close

- [ ] 2.1 `tests/test_paper2_figures_pinned.py` green; `AGENTS.md` updated.
- [ ] 2.2 Two read-only verifying subagents (conformance and adversarial). Record their
  findings here.
- [ ] 2.3 `make build` and `make spec-check` green; archive with the author's go.
