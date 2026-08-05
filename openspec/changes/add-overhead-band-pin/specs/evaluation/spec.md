# Evaluation

## ADDED Requirements

### Requirement: The overhead measurement is pinned to its order of magnitude
The evaluation harness SHALL pin the measured per-crossing cost to a band, and SHALL refuse to write
the evaluation artifact when a measurement falls outside it, rather than emitting a figure the papers'
stated magnitude contradicts. Because the excursions this guards against are transient, the harness
SHALL re-measure before treating one as real, and SHALL fail only on a sustained excursion.

The band SHALL be enforced where the artifact is written and not inside the run itself. The evaluation's
other pins guard properties of the code, which must hold wherever it runs; this one guards a measurement,
whose usability is a fact about the machine that took it, and a caller that publishes no figure SHALL NOT
be failed by a loaded machine.

The band's ceiling SHALL coincide with the boundary of the magnitude the papers state, so that no
measurement admitted by the band can name a different one.

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

### Requirement: The evaluation emits the magnitude of every figure a paper states in prose
The evaluation harness SHALL emit, alongside a measured figure, the magnitude a paper states for it in
prose, derived from the same measurement. A magnitude is a claim about a measurement exactly as the
figure is, so it SHALL NOT be maintained by hand in a paper while the figure beside it is interpolated.

#### Scenario: The magnitude is derived, not transcribed
- **WHEN** the evaluation artifact's data is serialised
- **THEN** it carries the crossing cost's magnitude as a pre-formatted string derived from the same
  measurement as the figure

#### Scenario: The magnitude and the figure cannot disagree
- **WHEN** a paper states the crossing cost's magnitude and its value in the same document
- **THEN** both are interpolated from one run, and no admitted measurement makes them name different
  magnitudes
