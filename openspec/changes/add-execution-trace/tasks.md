## 1. Trace model and schema

- [ ] 1.1 Define the trace model in `poc/trace.py` (node entries: name, tier, input/output trust labels, crossings with interface + instance; nested sub-traces; optional timings) — plain dataclasses, JSON-serialisable
- [ ] 1.2 Commit the JSON Schema (beside `graphs/schema.json` or under `poc/`; record the location choice in design.md) and add a test validating emitted traces against it

## 2. Runtime recording

- [ ] 2.1 Record node entries and capability crossings during `execute`; thread a trace collector through sub-graph nesting without giving the child executor anything backend-shaped
- [ ] 2.2 Instrument both tiers: host-tier handle wrappers and the sandbox tier's WIT boundary report crossings identically
- [ ] 2.3 Tests: execution-order and tier attribution; instance-name attribution (the `customer_session` crossing lands on the child's reply node); nested sub-graph trace; structural determinism across two identical runs (timings excluded)

## 3. Evaluation harness

- [ ] 3.1 Emit canonical injection-scenario traces for both tiers into `dist/`; extend `serialise()` if any trace-derived figure will be typeset
- [ ] 3.2 Pin the structural properties (taint reaches tool-capable node via permitted field on the confined tier; trust raised only at the discharge node) as build-failing checks in the existing pinned-verdict style

## 4. Paper 2

- [ ] 4.1 §3: report the trace artifact as a built fact, with the replay hedge explicit (journalled crossings are a prerequisite artifact, not replay; replay remains §5.3/Phase 2 — no verdict moves)
- [ ] 4.2 `make build` green; pinned verdicts pass
