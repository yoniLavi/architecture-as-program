# feed-triage-service Specification

## Purpose
The feed-triage service: a canonical signal graph that fetches feeds, triages each item with a
model and writes a digest, run by a driver on a schedule. Its security argument is that one
node holds outbound HTTP, no model sits upstream of it, and fetched content is labelled
untrusted where it enters. It is evidence for a later paper, and moves no Paper 2 figure.

## Requirements

### Requirement: The feed-triage service is a canonical graph that runs
The repository SHALL ship `graphs/feed-triage.json`, a canonical graph that fetches allowlisted feeds, drops items already seen, triages each new item in its own child run, and publishes one dated digest to a local file and HTML page, runnable once or on an interval by the driver.

#### Scenario: One tick against fixtures
- **WHEN** the driver runs one tick against the fixture server with the stub backend
- **THEN** a digest is written under `var/digests/`, the seen-store records the new items, and a second tick writes no item twice

### Requirement: Only the fetch node holds outbound HTTP, upstream of every model
The feed-triage graph SHALL give `HTTPClient` to exactly one node, and no node holding an `LLMClient` SHALL be upstream of it, so that no model output can reach a fetch.

#### Scenario: A wiring that puts HTTP downstream of a model
- **WHEN** a mutation gives `HTTPClient` to `ComposeDigest`
- **THEN** the service's own structural check rejects it, the driver refuses to run it, and the feed corpus pins both the rejection and the fact that the general validator accepts the graph

### Requirement: Fetched feed content is labelled untrusted where it enters
The node that receives fetched feed content SHALL declare its output `Untrusted<_>`, so that feed content enters the trust lattice labelled, and the write-up SHALL state that this label is declared at that node, not inferred.

#### Scenario: Removing the label
- **WHEN** a mutation declares `FetchFeeds`'s output clean
- **THEN** the feed corpus records that the general validator accepts the graph, as a stated limit, and pins its rejection by the service's own structural check

### Requirement: The service writes nothing outside the repository
The service SHALL keep its state, fetched data, run records and digests under the repository's gitignored `var/` directory, and SHALL make no network request other than allowlisted fetches and the model backend.

#### Scenario: A default run
- **WHEN** the driver runs with default settings
- **THEN** every file it writes is under `var/`

### Requirement: Fetched feeds can be recorded without triaging them
The service SHALL provide a recorder that fetches each subscribed feed through the service's own HTTP capability and allowlist and archives the raw response with the time it was fetched, making no model call.

#### Scenario: A recording tick
- **WHEN** the recorder runs once
- **THEN** each feed's raw body is written under the gitignored `var/archive/`, no model is called, and a feed that fails is recorded as a failure with its reason

#### Scenario: A second recorder
- **WHEN** a recorder starts while another holds the archive's lock
- **THEN** it exits with an error and records nothing

#### Scenario: A gap in recording
- **WHEN** no recorder ran for some hours between two ticks
- **THEN** the index shows the gap, and the evaluation reports the recorded span's coverage rather than treating it as continuous

### Requirement: The service can be replayed over an archive
The driver SHALL be able to run the service once per archived snapshot, in order, with that snapshot's bodies as its fetches and that snapshot's time as its clock, carrying state from one tick to the next.

#### Scenario: A replay is repeated
- **WHEN** the same archive is replayed twice on the stub backend from an empty state
- **THEN** the two replays produce identical run records and digests

#### Scenario: A replay pointed at the live service
- **WHEN** a replay is asked to write into the live service's data directory
- **THEN** it refuses, and writes nothing

#### Scenario: An item seen in an earlier snapshot
- **WHEN** an item appears in two consecutive archived snapshots
- **THEN** the replay triages it once
