# Tasks

Every session first checks the feed recorder (`operate-feed-triage` 0.2) and `git status`.

## 0. Approval

- [ ] 0.1 The author approves this proposal. Record the date here. Nothing below starts
  before this box is checked.

## 1. Grammar and assignability

- [ ] 1.1 `type_parser`: budget arguments (`Calls`, `Tokens`, `Requests`, `Bytes`) on
  their kinds. A smaller budget is assignable to a larger one; a budget is never
  assignable to an unbudgeted handle's slot. Verify: parser tests, and `dist/grammar.md`
  regenerated.
- [ ] 1.2 Validator: a budget that widens at composition is rejected, in the same class
  as a widening scope. Verify: a corpus case pinned to that reason class.

## 2. Meters

- [ ] 2.1 `BudgetExhausted`, a sibling of `CapabilityError`, never its subclass. The
  `uses` counter is reclassified to raise it. Verify: a test that a spent `uses` is not
  caught by `except CapabilityError`.
- [ ] 2.2 Backend meters for `Calls` and `Tokens`, shared down the routing chain (a
  child's meter draws on its parent's), on both tiers. Verify: a two-level composition in
  which the child exhausts the parent's meter.
- [ ] 2.3 `Requests` on `HTTPClient` and `Bytes` on `StateHandle`, metered at the
  crossing. Verify: one test per kind, on both tiers.

## 3. Store budgets

- [ ] 3.1 `engine_config()` gains fuel and epoch interruption. A node's `budget`
  annotation sets fuel, memory and a deadline. Verify:
  - S1's runaway guest is stopped and classed `Fuel`;
  - the overshoot is pinned at one check interval or less.
- [ ] 3.2 Keep the four failure classes apart: budget, resource, incomplete binding, and
  ungranted import. Verify: one test per class, each asserting its message.
- [ ] 3.3 Re-measure the crossing band on the new engine. Verify: `make build` green, and
  `tests/test_paper2_figures_pinned.py` unmoved.

## 4. Close

- [ ] 4.1 Two read-only verifying subagents (conformance and adversarial). Record their
  findings here.
- [ ] 4.2 `make build` and `make spec-check` green; archive with the author's go.
