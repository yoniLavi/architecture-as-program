## ADDED Requirements

### Requirement: The architect paper states its registered result as registered
The architect paper SHALL state its one confirmatory test, its outcome and its threshold in
the abstract and the introduction exactly as registered. It SHALL NOT present a descriptive
rate as an effect. It SHALL state, beside every catch rate, that the architect and the reviewer
are the same model. It SHALL NOT present zero attack success as a defence where the graph
reached no writer, or as the absence of a residual.

#### Scenario: The registered test did not reach its threshold
- **WHEN** the confirmatory p-value is at or above the registered alpha
- **THEN** the abstract says the test was not supported
- **AND** the rates beside it are called descriptive

### Requirement: The architect paper's figures are interpolated from the generated artifacts
Every figure in the architect paper, counts of things in the data included, SHALL be
interpolated from `dist/architect.json` or `dist/agentdojo-banking.json`. Paper 2's figures
SHALL be cited from Paper 2, never typed. Registered, pilot and AgentDojo results SHALL never be
pooled.

#### Scenario: A count changes in the records
- **WHEN** a committed record changes a figure the paper states
- **THEN** the rebuilt paper states the new figure, with no edit to its text
