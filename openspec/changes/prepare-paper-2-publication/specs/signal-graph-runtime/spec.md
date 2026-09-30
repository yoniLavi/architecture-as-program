## ADDED Requirements

### Requirement: Assembly validates a graph together with every graph it executes
The runtime SHALL, when assembling a graph, validate it together with every canonical graph it
reaches through sub-graph nodes, transitively, so that the cross-graph analyses (signature
matching, capability narrowing, and the boundary-output check) run before execution and not only
when graphs are validated as a batch at build. It SHALL also validate a parent together with a
sub-graph a caller's resolver supplied before running it, SHALL refuse a resolved sub-graph whose
name differs from its node's, and SHALL reject a graph containing a node of its own name and a batch
in which two graphs share a name, since graphs are resolved by name and each collision would skip
the cross-graph checks. A sub-graph node's `requires` contract SHALL be checked as a leaf's is. A graph validated alone leaves the cross-graph layer
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

#### Scenario: A name collision does not skip the checks
- **WHEN** a parent is named after its own sub-graph node, or a resolver returns a sub-graph under
  another name
- **THEN** the composition is rejected before the sub-graph runs

## MODIFIED Requirements

### Requirement: Capability crossings record the acting principal
Every recorded capability crossing SHALL carry, where a run binds a principal, the principal on whose
authority it was made, together with the chain of parties acting on that principal's behalf, so that
delegation is visible in the trace rather than inferred. Sub-graph runs SHALL record it at every
altitude.

This SHALL make the confused-deputy property checkable: no crossing anywhere in a run SHALL record a
principal outside the scope bound at entry unless it passed through a node declared to bind one.

#### Scenario: The confused-deputy property is checkable from the trace
- **WHEN** a run binds a principal and executes, including through a sub-graph
- **THEN** every crossing at every altitude records that principal (narrowing it is designed, not
  implemented)
- **AND** a crossing recording a principal outside that scope, absent a declared binder, is detectable

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
