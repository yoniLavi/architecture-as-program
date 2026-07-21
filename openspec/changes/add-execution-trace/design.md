## Context

The trace is the load-bearing artifact for two consumers with different needs: the evaluation harness (needs pinnable, deterministic structure) and the planned inspector UI (needs enough detail to render taint propagation). One format must serve both, in the repo's generated-from-checked-source pattern.

## Goals / Non-Goals

- Goals: deterministic, schema-pinned trace; both tiers report crossings identically; canonical injection traces in `dist/`.
- Non-Goals: replay (recording is not re-execution; §5.3 stands); tracing *inside* node bodies (the boundary is the unit of observation, consistent with the model's whole argument); log/telemetry infrastructure.

## Decisions

- **Determinism by construction, not by scrubbing.** No wall-clock timestamps or randomness in structural fields; timings live in one optional field that pinned comparisons and the determinism test exclude. This is why `Date`-free structure matters: the evaluation pins compare traces across builds.
- **Crossings are recorded at the handle, not in node bodies.** Host tier: the injected handle wrappers record. Sandbox tier: the host-side WIT implementations record. Node code cannot forge or suppress an entry on the confined tier — worth one sentence in §3; on the host tier recording is as circumventable as everything else there, and the paper must not imply otherwise.
- **Nesting mirrors execution.** The child's trace is collected by the same mechanism and attached under the parent's sub-graph node entry; the collector is passed alongside, never through, the backend-free child executor.
- **Schema lives with the graph schema** (one place readers already look for pinned formats) unless implementation shows a `poc/`-local home is cleaner; either way it is committed and tested, never inferred.

## Risks / Trade-offs

- Trace recording adds work per crossing → measure with the existing bench; the paper's overhead claim is only "inside the envelope", so record the new figure honestly if it moves.
- Two tiers recording identically is a claim, not a given → a test compares host-tier and confined-tier traces of the same graph for structural equality.

## Open Questions

- Whether the trace should carry the value payloads (useful for the inspector's display, but bloats the artifact and risks leaking `--live` model output into `dist/`) — lean: no payloads, only types + trust labels; the inspector renders shape, not content.
