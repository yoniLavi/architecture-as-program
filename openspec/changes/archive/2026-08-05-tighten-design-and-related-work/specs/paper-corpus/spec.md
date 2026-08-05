# Paper corpus

## ADDED Requirements

### Requirement: A revision preserves the hedging of the passage it revises
A revision of a passage stating an unproven property SHALL preserve that passage's hedging: the
conditional mood, and the tier restriction where a property holds only on the confined tier. Length
work SHALL NOT be paid for out of qualification. Where a rewrite cannot meet a length target without
weakening a hedge, the hedge SHALL win and the target SHALL be missed, because length is a target and
hedging is a claim.

This applies with most force to the demonstrator paper's design section, which describes intent inside
a paper otherwise written in the present tense, so a claim there reads as substantiated unless its mood
is deliberately kept conditional.

#### Scenario: A shortened passage keeps its qualification
- **WHEN** a passage stating an unproven property is rewritten shorter
- **THEN** every conditional marker and tier restriction it carried still qualifies the claim it
  qualified before

#### Scenario: A length target yields to a hedge
- **WHEN** a rewrite cannot reach its word target without weakening a hedge
- **THEN** the target is missed and the hedge is kept

### Requirement: The corpus states whether a discipline is checked or merely obliged
Where the corpus relies on a drafting discipline, it SHALL record whether that discipline is enforced by
a check or rests on review. A discipline believed to be checked when it is not is worse than one known
to rest on review, because a reader and an editor both stop looking. Where a guard exists over a
discipline that cannot be checked completely, no paper SHALL describe it as more than a regression
guard over the passages it pins.

#### Scenario: An unmechanised discipline is named as such
- **WHEN** the corpus relies on a discipline no check enforces
- **THEN** that is recorded as a review obligation rather than left to look like a guarantee

#### Scenario: A partial guard is not described as a complete one
- **WHEN** a paper or the corpus documentation refers to a guard over a drafting discipline
- **THEN** it states that the guard covers the passages it pins and not the property in general

## MODIFIED Requirements

### Requirement: No paper states that the artifact lacks a capability the artifact has
Every living paper SHALL describe the artifact's capabilities as they stand at build time. A
paper SHALL NOT state that the demonstrator lacks a capability it has; where a capability
exists but is weaker than the corpus once anticipated, the paper SHALL state the *restriction*
rather than the absence.

This closes the gap the corpus's other guards leave open. Interpolation prevents a *number*
from drifting and pinned verdicts prevent a *mechanism* from silently regressing, but a
sentence asserting an absence stays green forever after the thing is built. When a change adds
a capability, correcting every "the demonstrator has no X" claim across both living papers is
part of that change, not a later sweep.

This requirement rests on review and no check enforces it, which is recorded here because it
has already failed once undetected: the change that built principal binding left three passages
of the demonstrator paper (§2.3, and §2.5 twice) calling the binding *undesigned*, and they were
found four days later by a tightening pass that had no mandate to look for them. The evaluation
harness guards only the *overstating* direction — a paper cannot claim what the artifact cannot
do, because the harness runs the artifact — and there is no artifact against which to decide
that a sentence understates. The sweep is therefore a step in any change that lands a
capability, and the absence of a check on it SHALL stay stated rather than assumed.

#### Scenario: A newly built capability is swept through the prose

- **WHEN** a change gives the artifact a capability a living paper previously described as
  absent, undesigned, or unbuilt
- **THEN** that change also replaces each such statement with the capability's actual
  restriction, in both living papers

#### Scenario: An accounting verdict reflects the artifact

- **WHEN** the accounting records a prediction as *conditional* or *not attempted*
- **THEN** no evidence for that prediction exists in the artifact at build time; a prediction
  the artifact has partial evidence for is recorded as *partial* with its restriction stated

#### Scenario: The understating direction is known to be unguarded

- **WHEN** the corpus's drift guards are described, in documentation or in a paper
- **THEN** the overstating direction is attributed to the evaluation harness and the
  understating direction to the per-change sweep, rather than both being left to look checked
