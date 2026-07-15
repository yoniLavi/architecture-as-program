## ADDED Requirements

### Requirement: Capability identity is expressible in the canonical graph source
The runtime SHALL allow a node in the canonical graph JSON to declare a capability *identity* — a label
naming a specific instance of a capability type the node holds — and SHALL derive its per-node instance
routing from those declarations, so identity lives in the source of truth rather than only in the assembly
API. A node with no identity declaration SHALL be provisioned by type exactly as before. The graph schema
and the graph validator SHALL check identity declarations, rejecting an identity declared for a capability
the node does not hold, at validation time.

#### Scenario: Identity declared in the graph routes distinct instances
- **WHEN** a graph declares two nodes of the same capability type with distinct identity labels in the graph
  JSON and the graph is assembled without any identity argument
- **THEN** each node receives its own handle instance, as if the identities had been supplied to the
  assembly API

#### Scenario: An identity for an unheld capability is rejected at validation
- **WHEN** a node declares a capability identity for a capability type it does not hold
- **THEN** the graph validator rejects the graph, mirroring the runtime's assembly-time rejection

#### Scenario: Graphs without identity are unchanged
- **WHEN** a graph declares no capability identity
- **THEN** it validates, renders, and assembles exactly as before this change

### Requirement: Capability identity routes across sub-graph boundaries
The runtime SHALL allow a parent graph to bind a named capability instance to a sub-graph's capability, so
that identity — not merely capability type — is carried across a composition boundary. The sub-graph node
that holds the capability SHALL receive the specific instance the parent routed to it.

#### Scenario: A parent routes a distinct instance into a sub-graph node
- **WHEN** a parent graph provisions a capability to a sub-graph and names a distinct instance for it
- **THEN** the sub-graph node that holds that capability receives the named instance
- **AND** a sibling instance the parent did not route is not visible to that node
