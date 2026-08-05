# Paper corpus

## ADDED Requirements

### Requirement: No paper states a measured magnitude in its own hand
No paper in the corpus SHALL state the magnitude of a measured figure — "tens of microseconds",
"single-digit milliseconds" — as hand-maintained prose. A magnitude is a claim about a measurement
exactly as the figure is, and a hand-typed magnitude beside an interpolated figure is the same defect
as a hand-typed count beside an interpolated one: it stays green while the data moves underneath it.
Such a magnitude SHALL be interpolated from the evaluation artifact.

The one-owner-per-number rule SHALL apply to magnitudes as it applies to figures: the method paper
SHALL cite the demonstrator paper for a magnitude rather than stating one in its own voice.

#### Scenario: A magnitude in the demonstrator paper is interpolated
- **WHEN** the demonstrator paper states the magnitude of a measured figure anywhere, including
  outside its evaluation section
- **THEN** that magnitude is interpolated from the evaluation artifact rather than typed

#### Scenario: The method paper cites rather than states a magnitude
- **WHEN** the method paper refers to the magnitude of a demonstrator measurement
- **THEN** it cites the demonstrator paper for it and states no magnitude in its own voice

### Requirement: A falsifiable central claim rests on properties a reader can re-derive
The demonstrator paper's central claim SHALL be scoped to properties of the artifact that a reader can
re-derive from the repository. A single-machine wall-clock measurement, particularly one obtained by
differencing two timings, SHALL NOT be a component of the central claim, because it can be falsified by
the conditions of the reader's machine rather than by the artifact. Such a measurement SHALL be reported
as a supporting result in the evaluation section instead.

#### Scenario: The claim block excludes a fragile measurement
- **WHEN** a reader reads the demonstrator paper's central claim
- **THEN** every component of it is a property of the artifact, and the measured overhead is reported
  in the evaluation section rather than asserted in the claim

### Requirement: A stated limitation tracks the artifact's current behaviour
A limitation a paper states SHALL describe the artifact as it now behaves, not only a fault that has
since been corrected. Where a correction bounded a fault without removing the underlying weakness, the
paper SHALL state the residue and what now bounds it, so that a reader is not left believing a live
fragility was retired.

#### Scenario: A corrected fault does not conceal a live one
- **WHEN** a paper describes a measurement defect that was corrected
- **THEN** it also states whether the underlying fragility remains and what bounds it now
