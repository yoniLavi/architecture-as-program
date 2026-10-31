## ADDED Requirements

### Requirement: Utility is also reported beyond the tasks an idle run passes
Every report of AgentDojo utility SHALL give the figure over all user tasks and, beside it,
over the tasks whose utility predicate fails on an idle run (no tool call, an empty answer,
the environment as shipped). The idle-pass set SHALL be committed as a record and held to
AgentDojo's own predicates by a test. The scorer SHALL stay unchanged.

#### Scenario: A task the shipped environment already satisfies
- **WHEN** a task's utility predicate holds with no call and an empty answer
- **THEN** a success on it is counted in the all-task figure and left out of the other
- **AND** the report names the idle-pass tasks

### Requirement: A quoted dynamic payee name is not a payee
A `Payments` scope SHALL refuse a quoted payee that spells a dynamic payee set's name
(`'any'`, `'inbound-senders'`), so that the spelling can only mean the set. The validator
SHALL report the type as an unreadable scope.

#### Scenario: The architect quotes `any`
- **WHEN** a graph grants `Payments<['any'], '10.00'>`
- **THEN** validation fails with an unreadable scope, and no handle is provisioned
