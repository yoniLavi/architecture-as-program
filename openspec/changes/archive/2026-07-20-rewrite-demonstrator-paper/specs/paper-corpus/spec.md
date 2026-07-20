## ADDED Requirements

### Requirement: The demonstrator paper is in paper form and positions against the vision
The demonstrator paper SHALL be structured as a paper — an abstract, an introduction stating a falsifiable
central claim scoped to what the artifact substantiates, and design, implementation, evaluation, related-work,
research-agenda, and conclusion sections. It SHALL include an evaluation section whose figures and verdicts
are drawn from the generated evaluation artifact rather than hand-transcribed. It SHALL position itself against
the frozen vision paper by stating, for the vision's predictions, which the demonstrator substantiates and
which remain conditional, citing the vision as the archived original. It SHALL preserve the project's hedging
discipline: a claim is stated in present tense only where the artifact backs it.

#### Scenario: The demonstrator paper carries an artifact-sourced evaluation
- **WHEN** the demonstrator paper is built
- **THEN** it contains an evaluation section whose figures and verdicts come from the generated evaluation
  artifact

#### Scenario: The demonstrator paper distinguishes substantiated from open predictions
- **WHEN** a reader consults the demonstrator paper
- **THEN** it references the frozen vision paper and states which of the vision's predictions are substantiated
  by the artifact and which remain conditional

#### Scenario: Unproven claims stay hedged
- **WHEN** the paper states a property the artifact does not establish (for example, noninterference soundness)
- **THEN** that property is expressed conditionally rather than as an achieved result
