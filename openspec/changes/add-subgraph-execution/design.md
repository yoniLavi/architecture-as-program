## Context
`execute(graph, boundary_value)` in `poc/runtime.py` walks a single `AssembledGraph`: it finds the entry node
(the one consuming the boundary data parameter), runs each node's registered host/sandbox implementation with
its capability handles, and routes outputs along edges (selecting the variant for sum-typed outputs). A
sub-graph node has no implementation in `REGISTRY`; today that is an `ExecutionError`. The cross-graph
validator already proves a sub-graph node's inputs satisfy the referenced graph's parameters position-by-
position (data by equality, capabilities by assignability), so the wiring is known-good before we run it. This
change turns "no implementation" into "run the referenced graph."

## Goals / Non-Goals
- **Goals:** execute a sub-graph node by nested assembly + run; bind parent-provisioned handles to the
  sub-graph's parameters; route identity across the boundary at run time; isolate siblings; deliver the
  sub-graph's single boundary output as the node's output.
- **Non-Goals:** multi-terminal output aggregation; routing options (ii)/(iii); cross-tier composition; replay
  across boundaries; implementing every leaf of every `SupportPlatform` branch.

## Decisions
- **Decision: a sub-graph node is executed by recursion, not by a registered implementation.** When a node's
  name resolves to a loadable graph, `execute` (a) assembles that graph — reusing `assemble`, so the same
  validator gate and capability provisioning apply — with the parent's routed handles supplied for its
  capability parameters, (b) runs it from its boundary input via the same `execute`, and (c) returns its
  terminal output. This keeps one execution model; a sub-graph is just a node whose body is another graph.
- **Decision: bind parent handles to sub-graph parameters positionally.** The parent node's inputs line up
  with the sub-graph's parameters (the cross-graph check enforces this). Data positions carry the signal;
  capability positions carry the handle the parent provisioned — including a distinct instance where the
  parent declared `capability_identities` for that node. This is routing option (i): the sub-graph exposes a
  flat parameter list, the parent matches by position/type, internal fan-out is by the sub-graph's own `with`
  clauses. Options (ii) named slots and (iii) structural matching remain the open language-design surface.
- **Decision: siblings are isolated by construction.** Each sub-graph node gets its own nested
  `AssembledGraph` with only the handles routed to it; there is no shared mutable capability state between two
  sub-graph nodes unless the parent deliberately routes them the same identity. A test asserts a sibling's
  channel/state is untouched by another sub-graph's run.
- **Decision: single boundary output for now.** The sub-graph's terminal output (its one boundary output type,
  e.g. `ServiceOutcome`) becomes the parent node's output value, then routes on the parent's edges normally.
  Multi-terminal sub-graphs (several terminal types collapsed to one boundary) are the open aggregation
  question; this change requires the demonstrated sub-graph to have a single boundary output.
- **Decision: guard recursion.** A sub-graph that (transitively) references itself would not terminate;
  a simple visited-set / depth guard raises a clear `ExecutionError` rather than recursing unboundedly. The
  canonical graphs are acyclic at the composition level, so this is a safety rail, not a feature.

## Risks / Trade-offs
- **Leaf-implementation scope.** Executing `SupportPlatform` end-to-end for a customer request needs host-tier
  impls for the parent leaves reached (`RouteRequest`, `RecordAudit`). → Implement only those on the
  demonstrated path; the untaken `agent`/`billing` branches need no impls to prove the mechanism, and that is
  stated, not hidden.
- **Nested-assembly cost/semantics.** Re-assembling a sub-graph per execution re-provisions its handles. →
  Acceptable for the PoC (assembly is microseconds-to-milliseconds per the bench); a caching pass is a
  possible later optimisation, not needed here.
- **Boundary output ambiguity.** Forcing a single boundary output sidesteps the aggregation question. → Stated
  as a scope boundary and cross-referenced to Technical Note A so stronger enforcement is not misread.

## Migration Plan
Additive. Single-graph execution is unchanged; only a node that resolves to a loadable graph takes the new
path. Existing `customer-support` execution is byte-for-byte the same.

## Open Questions
- Should the runtime load referenced sub-graphs by canonical name from `graphs/` (as the parent is loaded), or
  should the caller pass a graph registry? (Leaning: load by name, matching `load_graph_dict`, with an
  optional override for tests.)
- How to surface a sub-graph-internal execution error at the parent level so the message is comprehensible at
  the composition altitude (Technical Note A, "Graph-scale comprehension"). Minimal: wrap with the sub-graph
  node's name; the richer story is deferred.
