# Paper 5: grants bound to values

> **Status: proposed, not approved.** It was written on 18 November 2026 at the author's
> request ("write that up as new changes for a follow-up paper"). No paper text is
> written before task 0.1.

## Why

Paper 4 measured review of an architect's authority. Its limits name the gap this work
closed: a grant bounds a kind and a scope, not a value, so inside `Payments<[any], …>`
every payee is reachable. Paper 4's future work mentions value-bound grants as
"exploratory work that has no figure here".

Three changes have since been built, verified by subagents, and archived. Their evidence
is committed, but no paper reports it:
- **`add-value-bound-grants`** (16 November 2026). A writer's grant can be bound to a
  value an upstream node produces ("this payee, this amount, once known"). Its re-run
  showed the rules stop the wide grant, but nothing leads an architect to the
  extractor-before-writer graph a bind needs.
- **`add-split-escalation`** (17 November 2026). A developer may ask for its node to be
  split, and a formal check judges the split. In the exploratory D2 re-run (5 runs,
  Haiku) a split was asked for in 5 and accepted in 4. The fifth failed only because the
  check matches field names exactly.
- **`add-payee-provenance`** (18 November 2026). `Payments<[known-payees], cap>` admits
  only a payee the account has paid before. Over 41 runs with no contradiction of the
  committed predictions, every payment attempt was refused: 16 to the attacker and 24
  to the bill. The cost over the 16 tasks: 1 of 7 legitimate payments is refused
  unavoidably (task 0, whose payee is as new as the attacker's), and 3 of 7 if merchant
  names are paid as ground truth spells them.

Each has pinned limits that must travel with its claim:
- **A bind is not a defence.** The wrong-extractor and injection cases are pinned as
  succeeding (`tests/test_bind_limits.py`).
- **Provenance pays an injected value that equals a known payee** (pinned in
  `tests/test_payee_provenance.py`).
- **A bind's trust label follows declarations, not sources.**

## What Changes

- **A new paper, `papers/05-…/`**, title and directory open (`design.md`). It reports
  the three changes as one argument:
  - binding authority to a value moves the question from the grant to the value's
    *provenance*;
  - one provenance rule at the crossing refuses every attacker payment measured;
  - the cost is that every new payee needs a decision outside the graph.
- **Evidence made quotable:** a report, `dist/grants.json`, built from the committed
  records (`poc/slice/runs/bind/`, `poc/slice/runs/split/`, the provenance records and
  predictions). It calls no model, and every figure the paper states is interpolated
  from it.
- **Corpus rules apply:**
  - The paper cites Paper 2 for the gate and Paper 4 for the pipeline.
  - **It cannot be stamped or published before Paper 4 is**, because a published paper
    cites no unpublished work.
  - Every result here is exploratory and unregistered, and the paper says so wherever
    one is cited.
- **A figure pin**, `tests/test_paper5_figures_pinned.py`, as Papers 2 to 4 have.

## Impact

- **New files:** `papers/05-…/proposal.typ`, a report module beside `poc/slice/report.py`,
  a `make grants` target in `make build`, and the figure pin.
- **Unchanged:** Paper 4's figures and text. Its future-work sentence may later cite
  Paper 5, but only once Paper 5 is published.
- **Modified capability:** `paper-corpus`.
- **End condition:** the paper is drafted, reviewed by subagents, read by the author,
  stamped and published, with its `RECORD.json` committed and the change archived.
