## ADDED Requirements

### Requirement: The derivation gate is shown rejecting a real binary
The evaluation harness SHALL hold at least one real, built component that imports an interface
its node's `with` clause does not grant against that clause, through the same derivation code
path as the agreeing rows, and SHALL pin both that it is caught and the interface it is caught
for. A gate that is only ever shown agreeing is indistinguishable from one that cannot fail, so
the failing direction SHALL have evidence from a real binary in the artifact and not only from a
constructed fixture in the test suite.

#### Scenario: The negative control is caught
- **WHEN** the evaluation harness runs
- **THEN** the negative control's component is reported as over-granting exactly its pinned
  interface, separately from the agreeing rows

#### Scenario: A negative control that stops being caught fails the build
- **WHEN** a negative control agrees with its `with` clause, or is caught for an interface other
  than the pinned one
- **THEN** the evaluation fails and no artifact is written
