# Change: Bound provisioned authority to the assembly's scope

## Why

This is the first change in the corpus taken *from* a community-of-practice system rather than
cited alongside one after the fact, and the provenance is the point.

Effect @effect_ts_2026 types every computation as `Effect<Success, Error, Requirements>` and cannot
run one until its requirements are discharged — close to a node's `with` clause. Reading its
resource model surfaced something the demonstrator does not have. In Effect, a resource acquired
within a `Scope` is *guaranteed* finalised when that scope exits: release is a property of the
structure, not an operation the programmer remembers. Our revocation is the opposite. It is
targeted and opt-in, which is right, but it is also entirely manual: `AssembledGraph.revoke(...)`
must be called, and nothing bounds a provisioned handle's authority to the run that provisioned it.
A caller that assembles a graph, executes it, and drops the reference leaves every caretaker live
and every node-held handle still usable.

That is a real gap in a design whose central claim is about bounded authority, and it is cheap to
close with machinery that already exists.

## What Changes

- `AssembledGraph` becomes a context manager. Exiting the scope severs every revocable instance the
  assembly minted, so authority granted for a run cannot outlive the run.
- An explicit `close()` for callers not using `with`, idempotent and safe to call twice.
- Existing behaviour is unchanged for callers that do not use the scope: `assemble(...)` without
  `with` behaves exactly as before, so no test, demo, or the inspector API needs to change.
- Paper 2 §3.4 gains a sentence stating the property **and its limit**, which is where the honesty
  lives: scope exit can only sever instances declared revocable. Instances provisioned bare have no
  caretaker to sever and therefore *do* outlive the scope. This is weaker than Effect's `Scope`,
  which finalises everything it acquired, and the difference is stated rather than glossed.

## Impact

- Affected specs: `signal-graph-runtime` (one ADDED requirement)
- Affected code: `poc/graph.py` (`AssembledGraph`), `tests/test_poc_capabilities.py`
- Affected papers: `papers/02-demonstrator/proposal.typ` §3.4 — no evaluation figure changes, so
  every interpolated number is untouched
- Not in scope: making *all* instances revocable by default (universal caretakers). That is the
  stronger, more Effect-like design, and it is a real design decision with a cost — every capability
  crossing would route through a proxy — so it belongs in the agenda, not smuggled in here.
