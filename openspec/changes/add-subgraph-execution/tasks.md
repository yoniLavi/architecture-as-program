## 1. Nested execution
- [ ] 1.1 In `poc/runtime.py`, detect a node whose name resolves to a loadable graph and execute it by nested
      assembly + run instead of raising for a missing implementation
- [ ] 1.2 Bind the parent-provisioned handles (including any routed identity instance) to the sub-graph's
      capability parameters position-by-position; deliver the parent's data signal to the sub-graph boundary
- [ ] 1.3 Lift the sub-graph's single boundary output back as the parent node's output and route it normally
- [ ] 1.4 Add a recursion/cycle guard that raises a clear `ExecutionError` on a self-referential sub-graph

## 2. Loading + leaf implementations
- [ ] 2.1 Let the runtime resolve referenced sub-graphs by canonical name (like `load_graph_dict`), with an
      override hook for tests
- [ ] 2.2 Add host-tier implementations for the parent leaf nodes on the demonstrated path (`RouteRequest`,
      `RecordAudit`) so a customer request executes `RouteRequest` → `CustomerSupport` → `RecordAudit`

## 3. Tests
- [ ] 3.1 A parent executes through a sub-graph node: the boundary signal enters the sub-graph, it runs, and
      its output returns to the parent
- [ ] 3.2 A graph-declared identity routed to a sub-graph node is the instance its internal nodes use at run
      time (ties assembly-time routing to execution)
- [ ] 3.3 Sibling isolation: a sibling sub-graph's handle/state is untouched by another sub-graph's run
- [ ] 3.4 `SupportPlatform` executes a customer request end-to-end through `CustomerSupport` into the audit log
- [ ] 3.5 The recursion guard rejects a self-referential sub-graph

## 4. Proposal + wrap-up
- [ ] 4.1 §5 composition text: note the composition graph now runs end-to-end (customer path), not only
      assembles; Technical Note A "Hierarchical capability routing" — mark option (i) resolved at the runtime,
      keep (ii)/(iii) and output aggregation open
- [ ] 4.2 Full gate green: ruff, pytest (`--group poc`), `make build`

## Notes for whoever picks this up
- Reuse `assemble`/`execute` recursively — a sub-graph is a node whose body is another graph; do not fork a
  second execution model.
- Only the leaves on the *taken* path need impls. The `agent`/`billing` branches are not required to prove the
  mechanism; say so rather than implementing them to look complete.
- Keep the single-boundary-output constraint explicit; multi-terminal aggregation is a separate open item.
