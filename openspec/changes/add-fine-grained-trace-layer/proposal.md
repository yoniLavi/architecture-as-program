# Change: Record crossings per call, and derive the coarse trace from them

## Why

The July 2026 survey (`docs/PRIOR-ART.md`) established that every durable-execution system that
actually replays — Temporal, Restate, DBOS, and Golem, which is architecturally closest since it
journals host calls across a component's WIT boundary — records **actual calls in order**. Our trace
records `(interface, instance)` **deduplicated per node**: the right kind of artifact at the wrong
granularity, necessary for replay and demonstrably not sufficient.

The dedup is not laziness. It is what makes host-tier and confined-tier traces structurally equal, a
property pinned by a passing test: the host tier calls a capability once where the confined tier's
component loops internally. So two desirable properties are in tension — tier-comparability, which the
dedup buys, and replay-sufficiency, which it forecloses.

They are not competing answers to one question; they are answers to two. An auditor asks *what
authority did this node exercise*; a debugger asks *what happened on this run*. The resolution is to
record the fine layer and make the coarse layer its **projection**, so tier-equality becomes a theorem
about that projection rather than two hand-maintained views that happen to agree.

Worth recording because it is ours alone: Golem has one substrate and Restate journals
developer-demarcated steps, so no surveyed system has had to make the same source unit yield
comparable evidence under two structurally different runtimes. The split is a cost of the migration
story, not an oversight.

## What Changes

- `NodeTrace` gains an ordered `calls` list — `(interface, instance, operation, index)` per crossing,
  in encounter order, undeduplicated.
- The existing `crossings` list becomes **derived**: project each call to `(interface, instance)`,
  deduplicate, sort. Nothing that consumes `crossings` changes, including the tier-equality test,
  which now compares a projection.
- `calls` is excluded from structural comparison and from the tier-equality assertion, because the
  tiers legitimately differ there — that difference is the point of having the layer.
- Honesty constraint, enforced in prose and schema docs: the fine layer is
  **confined-tier-authoritative, host-tier-advisory**. A hostile host-tier node can feed the wrapper
  fabricated calls exactly as it can fabricate anything else host-tier; a stronger-looking artifact
  must not smuggle in a stronger claim.
- Not in scope: capturing argument/return **values**, which is what replay would additionally need.
  The schema leaves room; this change does not fill it, and §3.5 continues to say replay was not
  attempted.

## Impact

- Affected specs: `signal-graph-runtime` (one ADDED requirement)
- Affected code: `poc/trace.py`, `poc/trace-schema.json`, `tests/test_poc_trace.py`
- Affected papers: `papers/02-demonstrator/proposal.typ` §3.5 — already states the projection design as
  noted-not-built; update to report it as built, with values still absent
- No evaluation figures change.
