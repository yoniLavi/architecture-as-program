## ADDED Requirements

### Requirement: Assembly validates a graph together with every graph it executes
The runtime SHALL, when assembling a graph, validate it together with every canonical graph it
reaches through sub-graph nodes, transitively, so that the cross-graph analyses (signature
matching, capability narrowing, and the boundary-output check) run before execution and not only
when graphs are validated as a batch at build. A graph validated alone leaves the cross-graph layer
silent, and a runtime that executes a composition the validator rejects makes "rejected before
anything runs" false for composed systems. Capability narrowing is checked here and SHALL NOT be
described as enforced: the parent's wider handle is routed to the child unattenuated.

#### Scenario: A composition the cross-graph checks reject does not assemble
- **WHEN** a parent graph routes a capability into a sub-graph parameter it cannot satisfy (for
  example, a billing store into the sub-graph's knowledge-base parameter), or declares a sub-graph
  node's output narrower than the child's terminals
- **THEN** assembly raises an assembly error naming the cross-graph reason, and nothing executes

#### Scenario: The canonical composition still assembles
- **WHEN** the canonical `support-platform.json` is assembled
- **THEN** it assembles and runs as before

## MODIFIED Requirements

### Requirement: A component node imports no ambient WASI functions
The runtime SHALL, on the component tier, produce node components whose import set contains only their
typed capability interfaces, the function-free type vocabulary, and no WASI function their node's `with`
clause did not grant. This strengthens "no ambient authority" from a property of an empty runtime context
(behind powerless WASI stubs, as on the core-wasm tier) to the absence of the imports themselves. Whether a
vocabulary interface such as the clock was granted is a per-node question, checked against the node's own
clause rather than against the whole capability vocabulary.

#### Scenario: The component's import set contains no WASI functions
- **WHEN** a node component is inspected for its imports
- **THEN** the import set contains only the node's declared capability interfaces and the function-free type
  vocabulary
- **AND** no filesystem, socket, or environment function appears among the imports at all, and a clock
  appears only where the node's clause grants `Clock`

#### Scenario: The hostile-node suite still denies every escape on the component tier
- **WHEN** the hostile-node attacks (filesystem, network, environment, ungranted capability) are run
  against a node on the component tier
- **THEN** each attempt fails, as it does on the core-wasm tier, so the confinement result is
  preserved rather than weakened by the port
