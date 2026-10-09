## ADDED Requirements

### Requirement: The feed-triage service is a canonical graph that runs
The repository SHALL ship `graphs/feed-triage.json`, a canonical graph that fetches allowlisted feeds, drops items already seen, triages each new item in its own child run, and publishes one dated digest to a local file and HTML page, runnable once or on an interval by the driver.

#### Scenario: One tick against fixtures
- **WHEN** the driver runs one tick against the fixture server with the stub backend
- **THEN** a digest is written under `var/digests/`, the seen-store records the new items, and a second tick writes no item twice

### Requirement: Only the fetch node holds outbound HTTP, upstream of every model
The feed-triage graph SHALL give `HTTPClient` to exactly one node, and no node holding an `LLMClient` SHALL be upstream of it, so that no model output can reach a fetch.

#### Scenario: A wiring that puts HTTP downstream of a model
- **WHEN** a mutation gives `HTTPClient` to `ComposeDigest`
- **THEN** a structural check rejects it and the case is pinned in the feed corpus

### Requirement: Fetched feed content is labelled untrusted where it enters
The node that receives fetched feed content SHALL declare its output `Untrusted<_>`, so that feed content enters the trust lattice labelled, and the write-up SHALL state that this label is declared at that node, not inferred.

#### Scenario: Removing the label
- **WHEN** a mutation declares `FetchFeeds`'s output clean
- **THEN** the feed corpus pins the rejection that results downstream, or records that none does, as a stated limit

### Requirement: The service writes nothing outside the repository
The service SHALL keep its state, fetched data, run records and digests under the repository's gitignored `var/` directory, and SHALL make no network request other than allowlisted fetches and the model backend.

#### Scenario: A default run
- **WHEN** the driver runs with default settings
- **THEN** every file it writes is under `var/`
