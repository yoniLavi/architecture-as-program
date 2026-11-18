# Contracts that compose along edges: a warning-strength validator analysis

> **Status: proposed, not approved.** It was written on 18 November 2026, after the author
> accepted spike S2's recommendation (`explore-specified-architecture`, archived).
> Nothing is implemented before task 0.1.

## Why

Nodes carry `requires` and `ensures` contracts (`poc/contracts.py`), and the runtime
checks each one at run time, node by node. Nothing checks, before a run, whether a
producer's `ensures` implies the consumer's `requires` on the edge between them.

S2 (`spikes/specified-architecture/s2/`, 25 tests, `RESULT.md`) built that check:
- **Solver-free**, per path and per sum variant.
- **Six verdicts:** discharged, contradicted, not-implied, no-guarantee, vacuous and
  undecided.
- **Held to `poc.contracts`' own evaluator** by a fuzz.

Over the canonical graphs it found 6 requirement-edges: 3 discharged and 3 with no
guarantee. It also found that **a guarantee does not survive a pass-through node**: the
contract vocabulary cannot relate a node's output to its input.

The adversarial review of the spike found:
- the fuzz checks only three of the six verdicts;
- one verdict is mislabelled conservatively;
- a 20,000-case fuzz found no unsound verdict.

## What Changes

- **A seventh validator analysis, at warning strength.**
  - **Errors:** a contradicted edge (the producer's guarantee rules out every input the
    consumer accepts) and a vacuous contract.
  - **Warnings, listed:** not-implied and no-guarantee edges, and undecided ones.
  - **Discharged edges** are reported, but the run-time `requires` check stays. Dropping
    it needs a proof that the producer keeps its `ensures`, which is `add-proved-cores`.
- **Stdlib-only**, in `scripts/`, like the other six analyses, so the pre-commit hook
  stays portable.
- **The fuzz covers every verdict**, with a widened value set (length 4, fractional
  values), against `poc.contracts`' evaluator. The spike's conservative mislabel is fixed
  or pinned.
- **Not in scope:** a relational atom (`len(out) <= len(in)`). It is what would carry a
  guarantee through a node, and it belongs with proofs, where a body can establish it.

## Impact

- **Code:** `scripts/graph_validator.py` (a new analysis), `scripts/validate-graphs.py`
  (warnings printed, not failing), and tests.
- **Paper 2's figures must not move.** Paper 2 says "six validator analyses". A seventh
  analysis changes no figure in `dist/evaluation.json`. The corpus verdicts are unchanged
  because warnings do not reject. `tests/test_paper2_figures_pinned.py` must stay green.
  The AGENTS.md line "six classes of analysis" is updated to name the seventh as
  post-Paper 2.
- **New capability:** `contract-composition`.
- **End condition:** the tasks are done, `make build` is green, two verifying subagents
  have reported, and the change is archived.
