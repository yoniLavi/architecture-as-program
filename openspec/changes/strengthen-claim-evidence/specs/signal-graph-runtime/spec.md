## ADDED Requirements

### Requirement: Cross-language regeneration covers capability-holding nodes

The demonstrator SHALL include at least two nodes regenerated in a second language from the same graph signature and contract as their Python counterparts, with the graph JSON unchanged, and at least one of them SHALL hold a capability handle (a database or send capability), so that interchangeability is demonstrated for nodes that exercise the typed capability boundary and not only for pure transformations.

#### Scenario: A capability-holding node is regenerated with the graph unchanged

- **WHEN** a capability-holding node's implementation is replaced by its regenerated counterpart in the node registry
- **THEN** the graph JSON requires no edit, the graph assembles, and the end-to-end run produces the same wiring-visible outcome

#### Scenario: The regenerated node is still confined to its declared handles

- **WHEN** the regenerated capability-holding node runs on the confined tier
- **THEN** its component imports exactly the WIT interfaces derived from its `with` clause, and a capability it was not granted remains unreachable

### Requirement: Confined-tier coverage extends across the CustomerSupport graph

The `CustomerSupport` graph SHALL execute end-to-end with a majority of the nodes on its demonstrated execution path running on the confined tier, and the runtime SHALL continue to report which tier ran each node, so that the claim "a node cannot exceed its declared capabilities" holds for most of the demonstrated graph rather than for two nodes.

#### Scenario: Majority-confined execution succeeds

- **WHEN** the `CustomerSupport` graph is executed in its most-confined configuration
- **THEN** more than half of the nodes on the taken path run as WASM components, the run completes with the same outcome as the host-tier run, and the per-node tier report names each node's tier

#### Scenario: Hostile behavior still fails on every confined node

- **WHEN** any confined-tier node attempts filesystem, network, environment, or ungranted-capability access
- **THEN** the attempt fails at the WASM boundary, as asserted by the hostile-node suite

### Requirement: Sub-graph execution composes across enforcement tiers

A sub-graph node SHALL be executable when its child graph contains confined-tier nodes and its parent graph runs on the host tier, and the existing sub-graph confinement property (the child receives exactly the handles the parent routed, because `execute` holds no backend) SHALL hold unchanged across the tier boundary.

#### Scenario: Host-tier parent runs a child with confined nodes

- **WHEN** `SupportPlatform` executes `CustomerSupport` as a sub-graph node and nodes inside `CustomerSupport` run on the confined tier
- **THEN** the run completes end-to-end, the tier report attributes each child node to its tier, and capability-instance routing from parent to child is preserved

#### Scenario: Confinement holds across the composed boundary

- **WHEN** a confined-tier node inside the child graph attempts to use a capability the parent did not route to the child
- **THEN** the attempt fails, because the child's executor holds no backend from which to provision it

### Requirement: A sub-graph node's declared output is validated against the child graph's terminals

Cross-graph validation SHALL check the output side of a sub-graph node's signature: the declared output type MUST match the union of the child graph's terminal output types (compared structurally, in the paper's stated union-alias convention), so that a sub-graph node can no longer declare an arbitrary output type without any check objecting.

#### Scenario: A mismatched declared output is rejected at assembly time

- **WHEN** a graph declares a sub-graph node whose output type is not the union of the child graph's terminal types
- **THEN** validation rejects the graph before execution, with a cross-graph signature reason class, and a pinned mutation-corpus case guards this verdict and reason class

#### Scenario: The canonical graphs still validate

- **WHEN** the canonical `support-platform.json` and `customer-support.json` are validated with the output-side check active
- **THEN** both pass, with `ServiceOutcome` resolving to `DeliveryConfirmation | EscalationTicket`
