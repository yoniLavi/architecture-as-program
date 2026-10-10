## ADDED Requirements

### Requirement: Replayed history is reported apart from operation
The feed-triage evaluation SHALL report replayed history, failures observed while recording, and live ticks in separate tables, and SHALL NOT describe a replay as operation of the service.

#### Scenario: A claim about scheduling
- **WHEN** the evaluation reports on the scheduler, the lock, or a tick overrunning its interval
- **THEN** the figures come from live ticks only

#### Scenario: A claim about volume
- **WHEN** the evaluation reports items triaged over a period that was replayed
- **THEN** the table is labelled as a replay and names the backend and tier it was replayed on
