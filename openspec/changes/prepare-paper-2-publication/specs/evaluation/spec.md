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
- an ungranted-capability denial SHALL count only for the capability failure, never for a resource failure,
  and only when it names the interface the component was built to over-grant; an off-allowlist denial only
  when it names the allowlist and the host;
- the injection refusal SHALL carry each tier's own reason (the host handle's scope check; the confined
  guest's report), so that a widened scope, which fails for another reason, is reported;
- the tier table SHALL be pinned in the build: a confined escape, or a host cell that stops escaping, fails
  it;
- the ambient-import figures SHALL be computed against each node's own `with` clause;
- each reason class SHALL be identified by its own check's message, and a case SHALL pin the class that
  must be *present* among its rejection's classes, so a second check firing on the same graph cannot mask
  a first that stopped firing (the sink rule once satisfied the lattice's signature, and the lattice could
  be removed with every laundering case still green).

#### Scenario: A denial for the wrong reason fails the build
- **WHEN** a confined escape probe is denied with a detail other than its discriminating one (for example,
  file not found or connection refused rather than unsupported)
- **THEN** the evaluation fails, and no artifact is written

#### Scenario: The injection refusal regresses on one tier
- **WHEN** a fooled model's out-of-scope tool call is not refused in the run on one of the tiers
- **THEN** the evaluation fails, rather than rendering a cross in the paper's table

## MODIFIED Requirements

### Requirement: The overhead measurement is pinned to its order of magnitude
The evaluation harness SHALL pin the measured per-crossing cost to a band, and SHALL refuse to write
the evaluation artifact when a measurement falls outside it, rather than emitting a figure the papers'
stated magnitude contradicts. Because the excursions this guards against are transient, the harness
SHALL re-measure before treating one as real, and SHALL fail only on a sustained excursion.

The band SHALL be enforced where the artifact is written and not inside the run itself. The evaluation's
other pins guard properties of the code, which must hold wherever it runs; this one guards a measurement,
whose usability is a fact about the machine that took it, and a caller that publishes no figure SHALL NOT
be failed by a loaded machine.

The band's ceiling SHALL be a decade boundary, so that no measurement the band admits names a magnitude
above the one the papers state. The band admits the upper half of the decade below as well, so the papers SHALL
interpolate whichever magnitude a run names rather than state one in their own hand.

#### Scenario: A contaminated measurement does not reach the artifact
- **WHEN** the per-crossing cost measures outside the band on every attempt
- **THEN** no evaluation artifact is written, and the failure names the band and says whether the
  likely cause is a loaded machine or a genuine change in the cost

#### Scenario: A transient excursion is retried rather than failing the build
- **WHEN** one measurement falls outside the band and a subsequent one falls inside it
- **THEN** the harness reports the measurement inside the band and the build proceeds

#### Scenario: A run that publishes no figure is unaffected by the band
- **WHEN** the evaluation is run by a test rather than to produce the artifact
- **THEN** an out-of-band measurement does not fail it

#### Scenario: Widening the band is a deliberate act
- **WHEN** the measured cost has genuinely moved out of the pinned band
- **THEN** the band is re-pinned deliberately, because the papers state the figure's magnitude and
  widening the band edits a claim
