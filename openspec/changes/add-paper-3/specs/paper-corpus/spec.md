## ADDED Requirements

### Requirement: The generation paper reports what generated code presented, not what the gate caught
The corpus SHALL contain a living generation paper that reports agent-written node bodies held to
the import gate derived from the graph. Its central claim SHALL rest on how often generated code
*presented* an over-importing component, and on what the gate-off control shows would have
happened next. It SHALL NOT present the gate's catch rate as an empirical finding, because the
gate is a set comparison and catches every over-importing component by construction.

The paper SHALL cite the demonstrator paper for the gate, the derivation, the enforcement tiers
and every measurement that paper sources, and SHALL restate none of them in its own voice. It
SHALL carry each limit of its experiment where that limit bounds a claim. These include:

- one model family;
- registration inside one repository, not in a registry;
- the authorised arm's post-hoc origin;
- the pretext ladder is not a factorial, and two of its steps are bundled;
- the pretext was placed in the task, not delivered through content;
- behavioural equality holds on the contract's inputs only;
- a service-specific policy check is not a validator analysis;
- replayed history is not operation.

It SHALL NOT restate the predictions-and-outcomes accounting, which has one owner.

#### Scenario: The gate's rejections are reported
- **WHEN** the paper reports that the gate rejected over-importing components
- **THEN** it says the rejection follows from the gate's construction
- **AND** it rests the finding on the count presented and the gate-off control's count, rather
  than on a catch rate

#### Scenario: A descriptive contrast is reported
- **WHEN** the paper reports a step of the pretext ladder, the rule-withheld contrast, or a
  per-model row
- **THEN** it reports it as descriptive, with no significance or causal claim
- **AND** only the registered confirmatory contrast carries a test result

#### Scenario: A mechanism of the demonstrator is needed
- **WHEN** the paper needs the derived import gate or a magnitude the demonstrator measured
- **THEN** it cites the demonstrator paper for it and states no such figure in its own voice

#### Scenario: The service's security argument is described
- **WHEN** the paper describes what keeps a model in the feed-triage service from reaching the
  network
- **THEN** it attributes the placement rule to the service's own policy check, not to the graph
  validator, and states that the validator accepts the rewirings that check rejects

### Requirement: The generation paper's figures are interpolated from the generated artifacts
Every figure in the generation paper SHALL be interpolated from the generation artifact or the
feed-triage evaluation artifact. This includes counts of things in the data, test results, and
magnitudes. A non-integer figure SHALL be taken from a pre-formatted display value, so that the PDF
and the web renderings state it identically. Trials of the registered run and trials of earlier
runs SHALL NOT be pooled in any figure, table or sentence.

#### Scenario: The confirmatory result is stated
- **WHEN** the paper states the confirmatory test's counts and p-value
- **THEN** both come from the generation artifact, and the p-value from its display value
- **AND** the PDF, Markdown and HTML renderings state the same string

#### Scenario: A registered and an earlier figure for the same pretext
- **WHEN** the paper reports a pretext that both the registered run and an earlier run contain
- **THEN** the two figures appear apart and labelled, and no sentence or table combines them

### Requirement: No stamped paper cites an unpublished corpus paper
The build SHALL fail if a paper whose source carries a persistent-identifier stamp cites a corpus
paper that has no committed publication marker. It SHALL also fail if a bibliography entry that
looks like a corpus paper maps to no paper. A frozen paper's marker is its existing publication
marker; a living paper's is a record marker committed at its upload. The check SHALL be offline
and dependency-free.

It SHALL be documented as trusting the marker: the build cannot see the publication record, so
a marker committed early would pass. Citations of work outside the corpus remain a review
obligation.

#### Scenario: A paper is stamped before the paper it cites is published
- **WHEN** a paper carries a DOI stamp and cites a corpus paper with no publication marker
- **THEN** the build fails and names both papers

#### Scenario: A paper in draft cites an unpublished corpus paper
- **WHEN** an unstamped paper cites a corpus paper that has not been published
- **THEN** the build passes

#### Scenario: The cited paper publishes
- **WHEN** the cited corpus paper's publication marker is committed
- **THEN** the citing paper may be stamped and the build passes
