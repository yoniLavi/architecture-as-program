# Change: Execute sub-graph nodes in the runtime

## Why
The runtime *assembles* the `SupportPlatform` composition graph but cannot *run* it: `execute` is a
single-graph walk, and a node whose name matches another graph (a sub-graph, like `CustomerSupport`) has no
host-tier implementation registered, so running it raises. Hierarchical composition — the proposal's headline
structural claim — is therefore demonstrated statically (the cross-graph validator checks signatures) and at
assembly (capability identity now routes across one boundary), but never operationally. This change makes the
runtime execute a sub-graph node by recursively assembling and running the referenced graph, so a boundary
signal flows *into* a sub-graph and its output flows back out. It also forces, and resolves at the runtime
level, the narrowest form of Technical Note A's *hierarchical capability routing* question (option i: a flat
parameter list matched by the parent, with internal fan-out by the sub-graph's own `with` clauses).

## What Changes
- Teach `execute` to run a **sub-graph node**: when a node's name matches a loadable graph, the runtime
  assembles that graph as a nested unit, binds the handles the parent provisioned for the node to the
  sub-graph's capability parameters (position-by-position — the cross-graph validator already guarantees the
  arity and assignability), delivers the parent's data signal to the sub-graph's boundary input, runs it, and
  lifts its terminal output back as the node's output.
- **Capability routing across the boundary (option i):** the parent matches the sub-graph's flat capability
  parameter list by position/type; inside the sub-graph, fan-out to internal nodes uses the existing
  shared-by-type / by-identity provisioning. A routed *identity* instance (from the graph-source
  `capability_identities`) is the one the sub-graph's internal nodes use — the assembly-time routing already
  built now has an executable consequence.
- **Sibling isolation:** each sub-graph node receives only the handles the parent routed to it; one
  sub-graph's handles and node-local state are not visible to a sibling sub-graph.
- **Output side (minimal form):** a sub-graph with a single boundary output type delivers that value as the
  parent node's output. Multi-terminal aggregation (named output ports, union-typed boundaries) stays open
  (Technical Note A, "Sub-graph output aggregation").
- Demonstrate on the shipped graph: a customer request routed through `SupportPlatform` executes
  `RouteRequest` → `CustomerSupport` (as a sub-graph) → `RecordAudit`, needing host-tier implementations only
  for the parent's own leaf nodes actually reached on that path. The `agent`/`billing` branches and their
  leaf implementations are not required to exercise the mechanism and remain future content.
- Not in scope: multi-terminal output aggregation; routing options (ii) named slots / (iii) structural
  matching; a sub-graph on a *different* enforcement tier than its parent (cross-tier composition); replay
  fidelity across sub-graph boundaries; recursion-depth or cycle concerns beyond a straightforward guard.

## Impact
- Affected specs: `signal-graph-runtime` (ADDED: the runtime executes sub-graph nodes; a sub-graph's boundary
  output is delivered as the parent node's output).
- Affected code: `poc/runtime.py` (recursive execution + parameter→handle binding), possibly `poc/graph.py`
  (nested assembly helper / loading referenced graphs by name), `poc/nodes.py` (host-tier impls for the parent
  leaf nodes on the demonstrated path, e.g. `RouteRequest`, `RecordAudit`), `tests/`, and the proposal's §5
  composition text + Technical Note A "Hierarchical capability routing" (mark option i resolved at runtime;
  keep ii/iii and output aggregation open).

## Dependencies
Builds on `add-graph-level-capability-identity` (identity routed across the boundary at assembly — this makes
it run) and `add-write-and-append-db-handles` (so `SupportPlatform` assembles). Independent of the paper-corpus
restructure, but its result is the operational-composition evidence the demonstrator paper's Implementation
section describes.
