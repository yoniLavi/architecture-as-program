## ADDED Requirements

### Requirement: Contract violations are a distinct pinned reason class
The evaluation harness SHALL treat a contract violation as its own reason class, distinct from an edge
type mismatch and from a trust-lattice violation, so that a corpus case pinned to a contract violation
cannot stay green if it begins to be caught by a different analysis.

#### Scenario: A contract case is pinned to its own reason class
- **WHEN** the corpus contains a case whose fault is a contract violation
- **THEN** the harness pins that reason class, and a divergence fails the build
