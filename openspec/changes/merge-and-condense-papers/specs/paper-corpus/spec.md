## MODIFIED Requirements

### Requirement: The demonstrator paper is in paper form and reports what the artifact establishes
The demonstrator paper SHALL be structured as a paper — an abstract, an introduction stating a falsifiable
central claim scoped to what the artifact substantiates, and design, implementation, evaluation,
predictions-and-outcomes, related-work, threats-to-validity, and conclusion sections. It SHALL include an
evaluation section whose figures and verdicts are drawn from the generated evaluation artifact rather than
hand-transcribed. It SHALL preserve the project's hedging discipline: a claim is stated in present tense only
where the artifact backs it.

The demonstrator paper SHALL carry the corpus's predictions-and-outcomes accounting of the frozen vision, in
condensed form: the protocol under which the vision was frozen before building, every prediction with its
verdict, and the design corrections the artifact forced. It SHALL position itself against the prior art for
LLM-agent security, including capability- and provenance-based defences against prompt injection, wherever it
claims prompt-injection attenuation.

#### Scenario: The demonstrator paper carries an artifact-sourced evaluation
- **WHEN** the demonstrator paper is built
- **THEN** it contains an evaluation section whose figures and verdicts come from the generated evaluation
  artifact

#### Scenario: The accounting has exactly one owner
- **WHEN** a reader looks for the predictions-and-outcomes accounting
- **THEN** it appears in the demonstrator paper, with every prediction of the frozen vision and its verdict,
  and no other paper restates it

#### Scenario: Prompt-injection claims engage the prior art
- **WHEN** the demonstrator paper claims prompt injection is attenuated
- **THEN** it cites and positions against existing capability- or provenance-based prompt-injection defences
  rather than claiming the problem is unaddressed

#### Scenario: Unproven claims stay hedged
- **WHEN** the paper states a property the artifact does not establish (for example, noninterference soundness)
- **THEN** that property is expressed conditionally rather than as an achieved result

### Requirement: No paper states a measured magnitude in its own hand
No paper in the corpus SHALL state the magnitude of a measured figure — "tens of microseconds",
"single-digit milliseconds" — as hand-maintained prose. A magnitude is a claim about a measurement
exactly as the figure is, and a hand-typed magnitude beside an interpolated figure is the same defect
as a hand-typed count beside an interpolated one: it stays green while the data moves underneath it.
Such a magnitude SHALL be interpolated from the evaluation artifact.

The one-owner-per-number rule SHALL apply to magnitudes as it applies to figures: a corpus paper that does
not itself source a measurement SHALL cite the paper that does rather than state a magnitude in its own voice.

#### Scenario: A magnitude in the demonstrator paper is interpolated
- **WHEN** the demonstrator paper states the magnitude of a measured figure anywhere, including
  outside its evaluation section
- **THEN** that magnitude is interpolated from the evaluation artifact rather than typed

#### Scenario: The method paper cites rather than states a magnitude
- **WHEN** a later corpus paper (a methods paper, or a successor to the demonstrator) refers to the
  magnitude of a measurement the demonstrator paper sources
- **THEN** it cites the demonstrator paper for it and states no magnitude in its own voice

## REMOVED Requirements

### Requirement: The corpus separates evidence from accounting across two living papers
**Reason**: The two living papers are merged into one condensed paper
(`merge-and-condense-papers`, 30 September 2026). The split's cross-citation became a
circular dependency between a paper about to be published and one that was not ready, and
the length it was meant to cure is cured by condensing instead.
**Migration**: The accounting moves into the demonstrator paper (see its modified
requirement). With a single paper sourcing every figure, the rule that the method paper
interpolates no evaluation data has nothing left to govern.

### Requirement: The method paper documents the pre-registration protocol and its mechanisation
**Reason**: There is no separate method paper. The protocol is described, in brief, inside
the demonstrator paper's predictions-and-outcomes section.
**Migration**: The protocol description and its single-instance limit move into the
demonstrator paper's predictions-and-outcomes and threats sections.

## ADDED Requirements

### Requirement: A published paper cites no unpublished work
A paper that is published under a persistent identifier SHALL NOT cite work that has no published record.
A citation of work in preparation cannot be followed by a reader, and between two papers of the corpus it
creates a dependency that forces them to publish in an order neither can satisfy. Where a published paper
needs material that is not yet published, it SHALL state that material, or its absence, in its own voice.

#### Scenario: The paper is prepared for publication
- **WHEN** a corpus paper is stamped with its identifier for publication
- **THEN** every entry in its bibliography has a published record, and none is marked in preparation
