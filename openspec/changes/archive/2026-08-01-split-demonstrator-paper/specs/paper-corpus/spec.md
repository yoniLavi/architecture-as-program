## RENAMED Requirements
- FROM: `### Requirement: The demonstrator paper is in paper form and positions against the vision`
- TO: `### Requirement: The demonstrator paper is in paper form and reports what the artifact establishes`
- FROM: `### Requirement: The demonstrator paper reports the inspector without overclaiming the editor prediction`
- TO: `### Requirement: Demonstration interfaces are reported as a mention, not as a contribution`

## MODIFIED Requirements

### Requirement: The demonstrator paper is in paper form and reports what the artifact establishes
The demonstrator paper SHALL be structured as a paper — an abstract, an introduction stating a falsifiable
central claim scoped to what the artifact substantiates, and design, implementation, evaluation,
related-work, threats-to-validity, and conclusion sections. It SHALL include an evaluation section whose
figures and verdicts are drawn from the generated evaluation artifact rather than hand-transcribed. It SHALL
preserve the project's hedging discipline: a claim is stated in present tense only where the artifact backs
it.

The demonstrator paper SHALL NOT carry the corpus's predictions-and-outcomes accounting, which belongs to the
method paper; it SHALL instead state concisely what it does and does not substantiate, and cite the method
paper for the accounting. It SHALL position itself against the prior art for LLM-agent security, including
capability- and provenance-based defences against prompt injection, wherever it claims prompt-injection
attenuation.

#### Scenario: The demonstrator paper carries an artifact-sourced evaluation
- **WHEN** the demonstrator paper is built
- **THEN** it contains an evaluation section whose figures and verdicts come from the generated evaluation
  artifact

#### Scenario: The accounting has exactly one owner
- **WHEN** a reader looks for the predictions-and-outcomes accounting
- **THEN** it appears in the method paper only, and the demonstrator paper cites it rather than restating it

#### Scenario: Prompt-injection claims engage the prior art
- **WHEN** the demonstrator paper claims prompt injection is attenuated
- **THEN** it cites and positions against existing capability- or provenance-based prompt-injection defences
  rather than claiming the problem is unaddressed

#### Scenario: Unproven claims stay hedged
- **WHEN** the paper states a property the artifact does not establish (for example, noninterference soundness)
- **THEN** that property is expressed conditionally rather than as an achieved result

### Requirement: Demonstration interfaces are reported as a mention, not as a contribution
A paper SHALL report a demonstration interface (such as the graph inspector) as a brief mention within the
section covering the underlying artifact, and SHALL NOT give it a dedicated section or list it as a
contribution. Any statement a paper makes about such an interface SHALL still correspond to a tested
requirement of the capability that provides it.

A demonstration interface SHALL NOT raise the verdict of any prediction in the predictions-and-outcomes
accounting. Where an interface partially exercises a predicted capability, the verdict SHALL follow the
underlying capability, and the interface MAY be noted alongside it.

#### Scenario: An interface gets a mention, not a section
- **WHEN** a paper reports a demonstration interface
- **THEN** it appears as a mention within an existing section, with at most one figure, and is absent from the
  contributions list

#### Scenario: A demo does not move a verdict
- **WHEN** the accounting records a prediction that a demonstration interface partially exercises (for example,
  the visual graph editor)
- **THEN** the verdict reflects the underlying capability — authoring, in that example — and the interface is
  noted rather than credited

## ADDED Requirements

### Requirement: The corpus separates evidence from accounting across two living papers
The corpus SHALL contain two living papers with distinct claims: a **demonstrator paper** reporting what the
artifact establishes, and a **method paper** reporting the research protocol and the accounting of the frozen
vision's predictions against the artifact. Each SHALL state a single central claim and SHALL be readable
without the other, with cross-citation rather than restatement.

The method paper SHALL NOT interpolate evaluation data; it SHALL cite the demonstrator paper for every figure
and measurement it refers to, so exactly one paper is the source of any given number.

#### Scenario: Each living paper carries one claim
- **WHEN** either living paper is built
- **THEN** its introduction states one central claim, and material serving the other paper's claim is cited
  rather than reproduced

#### Scenario: Only the demonstrator paper sources evaluation figures
- **WHEN** the method paper refers to a measurement from the artifact
- **THEN** it cites the demonstrator paper rather than interpolating the evaluation artifact itself

### Requirement: The method paper documents the pre-registration protocol and its mechanisation
The method paper SHALL describe the protocol by which the corpus records predictions before building —
freezing the founding vision, publishing it under a citable identifier, guarding it against silent edit by an
automated check in the build, permitting only dated errata, and reporting outcomes prediction by prediction
without revising the predictions. It SHALL present that protocol's **mechanisation** as its contribution and
the corpus's own history as one worked instance, and SHALL state the limits of generalising from a single
instance.

#### Scenario: The protocol is described with its enforcement
- **WHEN** a reader consults the method paper
- **THEN** it describes both the protocol and the automated check that enforces the freeze, rather than
  describing the protocol as an intention

#### Scenario: Single-instance generalisation is bounded
- **WHEN** the method paper draws conclusions from the corpus's own history
- **THEN** it states that the evidence is one instance and does not claim the protocol is validated generally
