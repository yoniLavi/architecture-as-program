## ADDED Requirements

### Requirement: Fetched feeds can be recorded without triaging them
The service SHALL provide a recorder that fetches each subscribed feed through the service's own HTTP capability and allowlist and archives the raw response with the time it was fetched, making no model call.

#### Scenario: A recording tick
- **WHEN** the recorder runs once
- **THEN** each feed's raw body is written under the gitignored `var/archive/`, no model is called, and a feed that fails is recorded as a failure with its reason

### Requirement: The service can be replayed over an archive
The driver SHALL be able to run the service once per archived snapshot, in order, with that snapshot's bodies as its fetches and that snapshot's time as its clock, carrying state from one tick to the next.

#### Scenario: A replay is repeated
- **WHEN** the same archive is replayed twice on the stub backend from an empty state
- **THEN** the two replays produce identical run records and digests

#### Scenario: An item seen in an earlier snapshot
- **WHEN** an item appears in two consecutive archived snapshots
- **THEN** the replay triages it once
