## Context

The trace is the load-bearing artifact for two consumers with different needs: the evaluation harness (needs pinnable, deterministic structure) and the planned inspector UI (needs enough detail to render taint propagation). One format must serve both, in the repo's generated-from-checked-source pattern.

## Goals / Non-Goals

- Goals: deterministic, schema-pinned trace; both tiers report crossings identically; canonical injection traces in `dist/`.
- Non-Goals: replay (recording is not re-execution; §5.3 stands); tracing *inside* node bodies (the boundary is the unit of observation, consistent with the model's whole argument); log/telemetry infrastructure.

## Decisions

- **Determinism by construction, not by scrubbing.** No wall-clock timestamps or randomness in structural fields; timings live in one optional field that pinned comparisons and the determinism test exclude. This is why `Date`-free structure matters: the evaluation pins compare traces across builds.
- **Crossings are recorded at the handle, not in node bodies.** Host tier: the injected handle wrappers record. Sandbox tier: the host-side WIT implementations record. Node code cannot forge or suppress an entry on the confined tier — worth one sentence in §3; on the host tier recording is as circumventable as everything else there, and the paper must not imply otherwise.
- **Nesting mirrors execution.** The child's trace is collected by the same mechanism and attached under the parent's sub-graph node entry; the collector is passed alongside, never through, the backend-free child executor.
- **Schema lives with the graph schema** (one place readers already look for pinned formats) unless implementation shows a `poc/`-local home is cleaner; either way it is committed and tested, never inferred. *Resolved in implementation: the schema is committed at `poc/trace-schema.json`, not `graphs/`.* `graph.graphs_by_name` globs every `graphs/*.json` as a **graph definition** (skipping only `schema.json`), so a trace schema placed there would be loaded as a graph and fail on its missing `name`. Colocating it with `poc/trace.py` — the model it pins — avoids that and keeps the runtime concept in the runtime package. It is validated by a stdlib-only checker in `poc/trace.py` (the project carries no JSON-Schema library, matching the graph validator's hand-rolled mirror of `graphs/schema.json`), so traces are schema-checkable in the pre-commit path with no new dependency.
- **Crossings are (interface, instance), deduplicated per node — not a per-call log.** This is what makes "both tiers record identically" *true* rather than aspirational: the host tier calls a capability method once while the confined tier's component runs its own internal loop crossing the same interface a different number of times, under a different function name (`respond` vs `generate`, `read` vs `lookup`). The set of typed interfaces a node crossed, and the instance each landed on, is the one representation both tiers produce identically. Multiplicity is a timing fact and lives nowhere in the structural trace.

## Risks / Trade-offs

- Trace recording adds work per crossing → measure with the existing bench; the paper's overhead claim is only "inside the envelope", so record the new figure honestly if it moves.
- Two tiers recording identically is a claim, not a given → a test compares host-tier and confined-tier traces of the same graph for structural equality.

## Open Questions

- Whether the trace should carry the value payloads (useful for the inspector's display, but bloats the artifact and risks leaking `--live` model output into `dist/`) — lean: no payloads, only types + trust labels; the inspector renders shape, not content.
