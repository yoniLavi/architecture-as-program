## ADDED Requirements

### Requirement: Principal scope narrows monotonically
A principal-bound capability SHALL narrow monotonically wherever it is routed, including across a
sub-graph composition boundary: narrowing SHALL only reduce authority, never widen it, and SHALL be
expressed as intersection over a fixed set of dimensions rather than as an open predicate language.
This keeps the set of principals a node can ever act as enumerable from the graph without executing it,
which is the property the confused-deputy argument requires.

#### Scenario: Narrowing across a composition boundary cannot widen
- **WHEN** a parent routes a principal-bound capability into a sub-graph
- **THEN** the sub-graph's view of that capability is the same principal scope or a narrower one
- **AND** an attempt to widen it is rejected
