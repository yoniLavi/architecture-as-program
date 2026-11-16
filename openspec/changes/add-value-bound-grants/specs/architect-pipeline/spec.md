# Spec Delta

## ADDED Requirements

### Requirement: A developer-written node holds no unbounded writer grant
The formal review SHALL fail a graph in which a `Custom` node holds a `Payments` grant unless the grant names only literal payees and a cap, or carries a bind of both payee and amount. It SHALL report the node and the grant.

#### Scenario: An open grant on developer code
- **WHEN** a `Custom` node holds `Payments<[any], uncapped>` with no bind
- **THEN** the formal review fails, naming the node and the grant

#### Scenario: A bound grant on developer code
- **WHEN** a `Custom` node holds `Payments<[any], '2000'>` bound to a payee and an amount from its input
- **THEN** this rule passes it

#### Scenario: A library writer
- **WHEN** a library `SendMoney` node holds `Payments<[any], uncapped>`
- **THEN** this rule does not apply, and the grant is left to the other checks

### Requirement: An accepted escalation grants no more than was asked
The formal review SHALL fail an escalation's edit if any grant it adds or widens is not assignable to the developer's request. A request that carries a bind SHALL be met only by a grant whose bind reads the same values or narrower ones, with no more uses. A failed edit SHALL go back for review and SHALL NOT run.

#### Scenario: A wider answer
- **WHEN** a developer asks for a payment bound to the bill's IBAN and total, and the edit grants `Payments<[any], uncapped>` with no bind
- **THEN** the formal review fails the edit, and the developer is not given the grant

#### Scenario: An exact answer
- **WHEN** the edit grants exactly the bound payment the developer asked for
- **THEN** this check passes it, and it goes on to the reviewer

### Requirement: The human review records where authority is held
The human review page and its verdict file SHALL offer, for each grant, the verdict `misplaced`: needed by the task, but held by the wrong node. It sits beside `needed`, `wider` and `not-needed`. The registered reviewer's prompt and verdict scale MUST NOT change.

#### Scenario: Needed, but held by developer code
- **WHEN** a human reviewer judges that a payment grant is needed but should sit on a library writer, not on a `Custom` node
- **THEN** the verdict file records `misplaced` for that grant, with the reviewer's note

#### Scenario: The registered reviewer
- **WHEN** the registered reviewer's prompt and scale are hashed after this change
- **THEN** the hashes equal those registered
