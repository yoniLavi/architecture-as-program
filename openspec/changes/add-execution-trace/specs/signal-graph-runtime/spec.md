## ADDED Requirements

### Requirement: The runtime emits a structured execution trace

Every graph execution SHALL produce a machine-readable trace recording, in execution order for each node run: the node name, the enforcement tier that ran it, the trust labels of its input and output values, and each capability crossing (the WIT interface crossed and the capability instance name). Sub-graph executions SHALL appear as nested traces under their sub-graph node. The trace format SHALL be pinned by a committed JSON Schema, and trace structure SHALL be deterministic across repeated runs of the same graph and input — timing data, if recorded, is an optional field excluded from structural comparison.

#### Scenario: A run yields a schema-valid trace

- **WHEN** the `CustomerSupport` graph executes on any tier configuration
- **THEN** the run returns a trace that validates against the committed schema, lists the taken path's nodes in execution order, and names the tier that ran each node

#### Scenario: Capability crossings are attributed to instances

- **WHEN** a node uses a granted capability handle during a run
- **THEN** the trace records the crossing with the WIT interface and the instance name the graph declared, so identity routing is visible in the trace

#### Scenario: Sub-graph runs nest

- **WHEN** `SupportPlatform` executes `CustomerSupport` as a sub-graph node
- **THEN** the child run appears as a nested trace under the sub-graph node's entry, and the nested entries carry their own tiers, trust labels, and crossings

#### Scenario: Trace structure is deterministic

- **WHEN** the same graph is executed twice with the same input
- **THEN** the two traces are structurally identical once optional timing fields are excluded
