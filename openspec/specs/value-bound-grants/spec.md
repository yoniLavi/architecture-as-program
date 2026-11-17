# value-bound-grants Specification

## Purpose
Narrows a capability grant at run time to values an upstream node produced, such as "this
payee, this amount, once". The static type stays the upper bound, and the bound is checked
before anything runs, labelled for trust, and enforced at the crossing on both tiers. A
bind holds the writer to its input and cannot make the input right: a wrong extractor's
value and an injected payee are both still paid, and both are pinned as succeeding.

## Requirements

### Requirement: A node may bind a grant it holds to values from its inputs
A node MAY declare a `bind` that narrows one `Payments` grant it holds to a payee, an amount and a number of uses, each read from one of the node's data inputs by an `inN.field` path. The grant's declared type SHALL remain its static upper bound, and a bind SHALL only narrow it.

#### Scenario: A bound payment
- **WHEN** a node holding `Payments<[any], '2000'>` binds `payee` to `in0.iban`, `amount` to `in0.total` and `uses` to 1, and its input carries `iban` X and `total` 120
- **THEN** the node may make one payment, to X, of at most 120, and no other

#### Scenario: A bound value outside the static bound
- **WHEN** the bound payee is not in the grant's literal payee set, or the bound amount exceeds its cap
- **THEN** the payment is refused at the crossing

### Requirement: The validator checks a bind's structure
The validator SHALL reject a bind that names a grant the node does not hold or a kind that is not bindable, a path that names a capability input or an input index out of range, or a `uses` that is not a positive integer. These checks MUST stay dependency-free.

#### Scenario: A bind on an ungranted capability
- **WHEN** a node binds `Payments<[any], uncapped>` but its inputs hold no such grant
- **THEN** validation fails, naming the node and the bind

#### Scenario: A path into a capability
- **WHEN** a bind's path names the input position of a capability handle
- **THEN** validation fails

### Requirement: The node library checks a bind's field types
Where a node's input record schema is known, the library check SHALL reject a bind whose path names a field the record lacks, a payee path whose field is not a string, or an amount path whose field is not a number.

#### Scenario: A payee bound to a number
- **WHEN** a bind's `payee` path names a numeric field of an `Extract` output
- **THEN** the library check fails, naming the field

### Requirement: Every bind carries a trust label
The validator SHALL label each bind `trusted` or `untrusted` from the trust label of every input its paths read. A bind reading an `Untrusted<_>` input SHALL be labelled `untrusted`, and it SHALL be allowed.

#### Scenario: A payee read from a bill
- **WHEN** a bind's payee path reads an input of type `Untrusted<Bill>`
- **THEN** the bind is accepted and labelled `untrusted`

### Requirement: A bind claimed trusted is enforced
A bind MAY claim `trusted`. The validator SHALL reject a bind that claims `trusted` when any input it reads is `Untrusted<_>`.

#### Scenario: A false trusted claim
- **WHEN** a bind claims `trusted` and its amount path reads an `Untrusted<_>` input
- **THEN** validation fails, naming the bind and the untrusted input

### Requirement: A bind is enforced at node activation on both tiers
The runtime SHALL, before a binding node runs, resolve the bind's paths against that activation's inputs and give the node a handle narrowed to the bound values. It SHALL refuse at the crossing any call outside the bound, on the host tier and on the confined tier. The confined component's import set MUST NOT change.

#### Scenario: A body pays another payee
- **WHEN** a body holding a bound grant calls the payment operation with a payee other than the bound one, on either tier
- **THEN** the call is refused at the crossing and the bank is not touched

#### Scenario: The import surface
- **WHEN** a confined node's grant is bound
- **THEN** its component imports exactly the interfaces its `with` clause derives, as without the bind

### Requirement: A bound grant is spent by use
The runtime SHALL count each successful call against a bind's `uses`, and SHALL refuse any call once the count is spent. The count SHALL last one activation. With a per-item map, each item's activation SHALL have its own count.

#### Scenario: A second payment
- **WHEN** a body with `uses` 1 makes a successful payment and then a second one
- **THEN** the second is refused at the crossing

#### Scenario: A refused call
- **WHEN** a call is refused by the bound or by the bank
- **THEN** it spends no use

### Requirement: An unresolvable bind fails the run
The runtime SHALL fail the run when a bind's path does not resolve against the activation's inputs, or resolves to a value of the wrong type. It MUST NOT fall back to the grant's static bound.

#### Scenario: A missing field at run time
- **WHEN** a bind's payee path names a field absent from the input that arrived
- **THEN** the run fails before the node runs, and no payment is made

### Requirement: Every rendering of a grant shows its bind
Every rendering of a graph for review SHALL print a bound grant with its bind and trust label, on one line: the canonical graph the reviewers see, the behaviour view, and the human review page.

#### Scenario: The human review page
- **WHEN** a graph with a bound grant is rendered for human review
- **THEN** the grant reads as its static type, then `bound`, each bound field and its path, the uses, and the trust label

### Requirement: The limits of a bind are pinned as limits
The test suite SHALL pin, as succeeding, a payment to a wrong value that the binding input itself carries, and a payment to a payee that an injection placed in the bound input, including where the bound input comes from a node a split inserted. No report or paper SHALL describe a bind or a split as a defence against either.

#### Scenario: The extractor is wrong
- **WHEN** a writer is bound to the output of a node that produced a truncated IBAN
- **THEN** the payment to the truncated IBAN succeeds, and the test asserts that it does

#### Scenario: The bill names the attacker
- **WHEN** an injected bill makes the extractor return the attacker's IBAN
- **THEN** the bound payment to it succeeds, and the test asserts that it does

#### Scenario: A split answer, under injection
- **WHEN** the graph a split answer produced runs on a bill that names the attacker's IBAN, with a stand-in model that obeys the injection
- **THEN** the bound payment to the attacker succeeds, and the test asserts that it does
