## ADDED Requirements

### Requirement: The trace records crossings per call and derives the deduplicated view
An execution trace SHALL record each capability crossing a node makes as an ordered, undeduplicated
entry identifying the interface crossed, the capability instance it landed on, the operation invoked,
and its position in the node's call sequence. The deduplicated `(interface, instance)` view SHALL be
**derived** from those entries by projection rather than recorded separately, so the two views cannot
disagree.

The per-call layer SHALL be excluded from structural comparison between enforcement tiers, because the
tiers legitimately differ in call count and operation naming; the derived view SHALL remain
tier-comparable, and the existing structural-equality property SHALL continue to hold as a property of
the projection.

The per-call layer SHALL be documented as confined-tier-authoritative and host-tier-advisory: on the
host tier it is exactly as circumventable as every other host-tier guarantee, and SHALL NOT be
presented as stronger evidence than the deduplicated view it projects to.

#### Scenario: The deduplicated view is a projection of the per-call layer
- **WHEN** a node crosses one capability instance several times in a run
- **THEN** the per-call layer contains one entry per call in order
- **AND** the deduplicated view contains exactly one crossing for that interface and instance

#### Scenario: Tier equality survives as a property of the projection
- **WHEN** the same graph runs on the host tier and on the confined tier
- **THEN** the derived deduplicated views are structurally equal once the tier field is set aside
- **AND** the per-call layers may differ, and that difference does not fail the comparison
