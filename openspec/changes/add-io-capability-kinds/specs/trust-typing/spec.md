## ADDED Requirements

### Requirement: An outbound-host allowlist narrows monotonically at composition
A parent routing an outbound HTTP capability into a sub-graph SHALL provide a handle whose permitted
host set is equal to or a superset of what the sub-graph declares, never a subset, so that composition
cannot silently grant a child reach the parent's own handle does not have. This extends the existing
capability-narrowing analysis to a scope that is a set rather than a mode or a name.

#### Scenario: A parent cannot route a narrower allowlist than the child declares
- **WHEN** a sub-graph declares an HTTP capability over a set of hosts and the parent routes one whose
  set omits any of them
- **THEN** validation rejects the composition
