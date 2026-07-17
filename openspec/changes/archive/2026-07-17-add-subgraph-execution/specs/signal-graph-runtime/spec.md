## ADDED Requirements

### Requirement: The runtime executes sub-graph nodes
The runtime SHALL execute a node that references another graph (a sub-graph) by assembling and running the
referenced graph as a nested unit. It SHALL bind the handles the parent provisioned for that node to the
sub-graph's capability parameters position-by-position, deliver the parent's data signal to the sub-graph's
boundary input, run the sub-graph, and return its terminal output as the node's output. A distinct capability
instance routed to the node (via graph-source `capability_identities`) SHALL be the instance the sub-graph's
internal nodes use. The runtime SHALL NOT let one sub-graph node's handles or node-local state be visible to a
sibling sub-graph node, and SHALL raise a clear error rather than recurse without bound on a self-referential
sub-graph.

#### Scenario: A parent executes through a sub-graph node
- **WHEN** a graph is executed whose node references another graph as a sub-graph
- **THEN** the boundary signal enters the sub-graph, the sub-graph runs, and its output is returned to the
  parent as that node's output

#### Scenario: A routed identity is used inside the sub-graph
- **WHEN** the parent routes a distinct capability instance to a sub-graph node
- **THEN** the internal nodes of that sub-graph that hold the capability use the routed instance, not a
  sibling's or the shared-by-type default

#### Scenario: Siblings are isolated
- **WHEN** two sibling sub-graph nodes are present and one is executed
- **THEN** the other sub-graph's handles and node-local state are untouched

#### Scenario: A self-referential sub-graph is rejected
- **WHEN** a sub-graph references itself transitively
- **THEN** execution raises a clear error rather than recursing without bound

### Requirement: A sub-graph's boundary output is delivered as the parent node's output
For a sub-graph with a single boundary output type, the runtime SHALL deliver that output value as the parent
node's output, which then routes along the parent's edges as any node output does. Collapsing several terminal
outputs of differing type into one boundary value (multi-terminal aggregation) is out of scope and remains an
open design question.

#### Scenario: The sub-graph's output flows on the parent's edges
- **WHEN** a sub-graph node with a single boundary output finishes
- **THEN** its boundary value becomes the parent node's output and is routed along the parent's outgoing edges
