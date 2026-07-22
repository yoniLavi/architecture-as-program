# Change: Emit a structured execution trace from every run

## Why

The runtime already knows, per run, everything a reader has to reconstruct from prose today — execution order, which tier ran each node, which capability crossings occurred on which instances, and what trust label each value carried — but it reports only fragments (the tier table). A machine-readable trace makes the run itself a first-class, tested artifact in the repo's established pattern (every rendered output generated from a checked source), gives §3 an observability fact adjacent to the replay prediction (with the hedge kept: a trace is evidence you *could* journal crossings, not replay — replay stays §5.3/Phase 2), and is the artifact the planned graph inspector will render, keeping that UI a pure consumer.

## What Changes

- The runtime records a structured trace on every `execute`: per node — name, enforcement tier, input/output trust labels, capability crossings (WIT interface + instance name); sub-graph runs nest.
- A committed JSON Schema pins the trace format; traces validate against it in tests.
- Timings are carried as an optional field excluded from pinned comparisons, so trace structure is deterministic across runs.
- The evaluation harness emits canonical traces of the prompt-injection scenario on both tiers into `dist/`, with structural properties pinned (the untrusted taint reaching the tool-capable node through the permitted field — the §4.3 free-text residual, now visible in data rather than only in prose). These are reference/regression artifacts for the paper, not the demo's data source: the inspector renders traces generated live by each user-triggered run, through the same recording code path — the pins guarantee the live traces' shape, they do not replace them.
- Paper 2 §3 reports the trace artifact; no §5 verdict moves (replay stays untouched).

## Impact

- Affected specs: `signal-graph-runtime` (one ADDED requirement), `evaluation` (one ADDED requirement)
- Affected code: `poc/runtime` (trace recording), `poc/values.py` or a new `poc/trace.py` (trace model + schema), `poc/evaluate.py` (emission + pins), `tests/`
- Affected papers: `papers/02-demonstrator/proposal.typ` §3
- Ordering: independent of `strengthen-claim-evidence`; `add-graph-inspector-ui` depends on this change.
