# Tasks

Every session first checks the feed recorder (`operate-feed-triage` 0.2) and `git status`.

## 0. Approval

- [ ] 0.1 The author approves this proposal and answers `design.md`'s open questions.
  Record the date and the answers here. Nothing below starts before this box is checked.

## 1. The gate

- [ ] 1.1 Move the hardened gate and `Audit.lean` out of the spike, with the sandbox
  property for Linux (D2). Verify, as tests:
  - the review's attacks are refused (a `macro_rules` rewrite of `#print axioms`,
    `sorryAx`, and a build-time `#eval` write);
  - a theorem of the wrong type is refused;
  - a correct proof is accepted.
- [ ] 1.2 The gate generates each statement and its prose from the graph (D1, D3).
  Verify: changing a node's contract changes its pinned statement, and its prose with it.

## 2. Cores

- [ ] 2.1 Split the three spiked nodes into a core and a shell, with differential tests.
  Strengthen `respond`'s effects to carry the tool (D3). Verify:
  - the derivation rows are unchanged, or any byte change is reported to the author;
  - `tests/test_paper2_figures_pinned.py` stays green.
- [ ] 2.2 Prove the generated statements for the three nodes, `respond`'s tool-scope
  clause included. Verify: the gate accepts them.
- [ ] 2.3 Call bounds: the proved bound narrows the node's `Calls` budget (needs
  `add-resource-budgets`). Verify: a test that a declared budget larger than the proved
  bound is narrowed, and a smaller one is kept.

## 3. Evidence (if open question 3 is yes)

- [ ] 3.1 A registration, committed before any call, and a registered generation run
  under the hardened gate. Verify: the harness refuses an uncommitted registration and a
  dirty tree, as Paper 3's does.

## 4. Close

- [ ] 4.1 Two read-only verifying subagents (conformance and adversarial). Record their
  findings here.
- [ ] 4.2 `make build` and `make spec-check` green; archive with the author's go.
