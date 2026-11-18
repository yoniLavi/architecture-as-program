## ADDED Requirements

### Requirement: The validator checks contract implication on every edge
The validator SHALL check, for every edge whose consumer declares a `requires`, whether the producer's `ensures` implies it, per path and per sum variant, without a solver, and SHALL report each edge's verdict.

#### Scenario: A guarantee discharges a requirement
- **WHEN** a producer ensures `len(q) <= 400` and the consumer requires `len(q) <= 512`
- **THEN** the edge is reported as discharged

#### Scenario: A guarantee that does not imply the requirement
- **WHEN** a producer ensures `len(q) <= 600` and the consumer requires `len(q) <= 512`
- **THEN** the edge is reported as not implied, as a warning

### Requirement: A contradicted or vacuous contract is an error
The validator SHALL reject a graph with an edge on which the producer's guarantee excludes every input the consumer accepts, or with a contract no value can satisfy; every other non-discharged verdict SHALL be a warning that does not reject.

#### Scenario: A contradicted edge
- **WHEN** a producer ensures `len(q) > 600` and the consumer requires `len(q) <= 512`
- **THEN** validation fails with the contradicted reason class

### Requirement: A discharged edge keeps its run-time check
A discharged verdict SHALL NOT remove the consumer's run-time `requires` check.

#### Scenario: A discharged edge at run time
- **WHEN** an edge is discharged and the graph runs
- **THEN** the consumer's `requires` is still evaluated at run time

### Requirement: Every verdict is held to the evaluator
The implication check SHALL be fuzzed against the contract evaluator for every verdict class, so that no verdict claims an implication, contradiction or vacuity that the evaluator refutes.

#### Scenario: An unsound verdict is introduced
- **WHEN** the check is changed to report discharged for a pair the evaluator separates
- **THEN** the fuzz test fails
