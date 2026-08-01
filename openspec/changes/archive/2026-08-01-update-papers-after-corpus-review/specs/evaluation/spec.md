# evaluation

## ADDED Requirements

### Requirement: The evaluation reports the graph-to-binary derivation as a pinned figure
The evaluation harness SHALL report, for each node ported to the confined tier, the interface
set derived from that node's `with` clause in the canonical graph, the interface set its built
component actually imports, and whether the two agree — and SHALL fail the build on any
divergence rather than emitting a passing report. This is the demonstrator's lead claim, so it
SHALL have evidence in the evaluation artifact and not only in the test suite.

#### Scenario: The derivation is reported per node

- **WHEN** the evaluation harness runs
- **THEN** the evaluation artifact reports, per ported node, the derived interface set, the
  actual import set, and their agreement

#### Scenario: An over-granting world fails the build

- **WHEN** a component imports an interface its node's `with` clause did not grant, or fails to
  import one the clause did grant
- **THEN** the evaluation fails, so an over-grant cannot ship as a passing figure
