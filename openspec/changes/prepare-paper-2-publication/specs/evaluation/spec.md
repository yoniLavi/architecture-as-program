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

### Requirement: Every reported outcome is measured where it is reported, and could have read otherwise
The evaluation harness SHALL compute each reported outcome from the run, tier, and object the report
attributes it to, and not from a separate probe. It SHALL count a denial as evidence only when the denial's
detail is the discriminating one, the reason that could not appear had the attempt reached the host. An
outcome that could not have read otherwise on the machine that built it is not evidence, and SHALL fail the
build rather than be reported as a denial. Specifically:
- the prompt-injection refusal SHALL be read from a run of the reported graph on the reported tiers, with a
  model that demands the out-of-scope tool, and SHALL be pinned on each tier;
- each host-tier escape SHALL be an attempt the harness performs, not a literal;
- a confined filesystem or socket denial SHALL count only when the guest reports the operation unsupported,
  and an environment denial only while the harness has set the variable being read;
- an ungranted-capability denial SHALL count only for the capability failure, never for a resource failure;
- the ambient-import figures SHALL be computed against each node's own `with` clause.

#### Scenario: A denial for the wrong reason fails the build
- **WHEN** a confined escape probe is denied with a detail other than its discriminating one (for example,
  file not found or connection refused rather than unsupported)
- **THEN** the evaluation fails, and no artifact is written

#### Scenario: The injection refusal regresses on one tier
- **WHEN** a fooled model's out-of-scope tool call is not refused in the run on either tier
- **THEN** the evaluation fails, rather than rendering a cross in the paper's table
