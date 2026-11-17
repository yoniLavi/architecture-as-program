## ADDED Requirements

### Requirement: A developer may ask for its node to be split
A developer's escalation request MAY ask for a split: a node inserted before its own that produces named fields of given types, with the requested grant bound to those fields. Each bind path in such a request SHALL name a requested field, a payee field SHALL be a string and an amount field a number. A split request that breaks this SHALL fail closed.

#### Scenario: A well-formed split request
- **WHEN** a developer asks for `Payments<[any], uncapped>` bound to `payee=in0.iban`, `amount=in0.total`, once, with a split producing `{iban: string, total: number}`
- **THEN** the request parses, and the architect receives the split, the capability and the bind as one structured reason

#### Scenario: A bind path outside the split
- **WHEN** a split request binds `payee=in0.account` and the split names no `account` field
- **THEN** the request fails closed, and no answer to it can pass the no-wider check

#### Scenario: An amount bound to a string
- **WHEN** a split request binds `amount` to a field the split types as a string
- **THEN** the request fails closed

### Requirement: A split answer is held to the split asked for
The formal review SHALL accept an answer to a split request only when a node new in the edit produces every requested field with its type, holds no grant but `LLMClient<inference>`, and the grant's holder binds each requested field to that node's field. A bind MAY reach the field through `Compose` fields that are plain paths. Anything else SHALL fail.

#### Scenario: The developer's node pays, bound to an extractor
- **WHEN** the edit inserts an `Extract` producing `{iban, total}` before the `Custom` node, and binds that node's payment grant to `in0.iban` and `in0.total`, once
- **THEN** the no-wider check passes the edit, and the `Extract`'s inference grant is not counted as a widening

#### Scenario: A library writer pays, through a plain-path `Compose`
- **WHEN** the edit inserts an `Extract`, then a `Compose` whose `recipient` is `=in0.iban` and whose `amount` is `=in0.total`, then a `SendMoney` bound to `in0.recipient` and `in0.amount`
- **THEN** the no-wider check traces both bound values to the `Extract`'s fields and passes the edit

#### Scenario: A value computed on the way
- **WHEN** the `Compose` between the extractor and the writer computes `amount` as `=in0.total * 2`
- **THEN** the bound amount does not trace to a requested field, and the check fails the edit

#### Scenario: The inserted node holds an effect
- **WHEN** the node the edit inserts holds a `Payments` grant
- **THEN** the check fails the edit

#### Scenario: The writer is left unbound
- **WHEN** the edit inserts the extractor but grants the payment with no bind
- **THEN** the check fails the edit

#### Scenario: More uses than asked
- **WHEN** the answer's bind allows two uses and the request asked for one
- **THEN** the check fails the edit

#### Scenario: A selector stands in for the extractor
- **WHEN** the node the bind traces to is new in the edit but is a reader, a selector or a writer, not an `Extract` or `Custom` node naming the fields
- **THEN** the check fails the edit

#### Scenario: A request whose uses is not a positive integer
- **WHEN** a split request's bind gives `uses` as a string, a fraction, zero or a boolean
- **THEN** the request fails closed, and no answer to it can pass

## MODIFIED Requirements

### Requirement: An accepted escalation grants no more than was asked
The formal review SHALL fail an escalation's edit if any grant it adds or widens is not assignable to the developer's request. A request that carries a bind SHALL be met only by a grant whose bind reads the same values or narrower ones, with no more uses. A split request SHALL be met only as a split answer is held to the split asked for. A failed edit SHALL go back for review and SHALL NOT run.

#### Scenario: A wider answer
- **WHEN** a developer asks for a payment bound to the bill's IBAN and total, and the edit grants `Payments<[any], uncapped>` with no bind
- **THEN** the formal review fails the edit, and the developer is not given the grant

#### Scenario: An exact answer
- **WHEN** the edit grants exactly the bound payment the developer asked for
- **THEN** this check passes it, and it goes on to the reviewer

#### Scenario: An unparseable request
- **WHEN** the request names a cap that is not a number, such as `Payments<[any], 'bill-total'>`
- **THEN** the check fails every answer to it closed, as it did before splits existed
