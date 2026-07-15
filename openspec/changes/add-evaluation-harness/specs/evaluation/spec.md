## ADDED Requirements

### Requirement: The demonstrator ships a reproducible evaluation artifact
The repository SHALL produce, as a build output, a reproducible evaluation artifact that consolidates the
demonstrator's evidence: the accept/reject verdicts of the graph-mutation corpus, the capability-boundary
overhead measurements, and the prompt-injection attenuation outcome across the host and sandbox enforcement
tiers. The artifact SHALL be generated from the existing corpus, benchmark, and demonstration rather than
hand-maintained, so its contents cannot drift from the code that produces them. The artifact SHALL state that
the corpus is curated and illustrative and SHALL report both tiers honestly, so it cannot be read as a
soundness proof or a stronger guarantee than the demonstrator provides.

#### Scenario: The evaluation artifact is generated on build
- **WHEN** the build runs
- **THEN** the evaluation artifact is produced from the corpus, benchmark, and demonstration
- **AND** it reports the corpus accept/reject counts, the overhead figures, and the host-vs-sandbox tier
  outcomes

#### Scenario: The artifact does not overclaim
- **WHEN** a reader consults the evaluation artifact
- **THEN** it states the corpus is curated and illustrative and reports the host tier's escapes as a recorded
  gap alongside the sandbox tier's confinement

### Requirement: The evaluation pins expected verdicts as a regression guard
The evaluation SHALL pin, for each mutation in the corpus, its expected verdict, and SHALL fail if the actual
verdict diverges, so the evaluation guards the demonstrator's central claims against regression rather than
merely reporting a snapshot.

#### Scenario: A divergent verdict fails the evaluation
- **WHEN** a mutation's actual verdict differs from its pinned expected verdict
- **THEN** the evaluation fails rather than emitting a passing report
