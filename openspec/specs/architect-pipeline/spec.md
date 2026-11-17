# architect-pipeline Specification

## Purpose
The architect and its reviewers: a model that writes a signal graph from a natural-language task
without seeing tool output, a formal review that checks each grant's quoted justification and
compares the graph with registered least-authority labels, an isolated reviewer tested before
use, authority that changes only through the graph, and the registration and spending rules
under which any of it is measured.

## Requirements

### Requirement: The architect authors a graph from a prompt, and sees no tool output
The repository SHALL provide an architect that turns a natural-language task into a signal graph
over the node library. It SHALL work in two stages: an abstract graph from the prompt alone, then
a mapping to the narrowest library nodes and kinds. The validator SHALL be in the loop, reporting
structured reason classes. The architect SHALL NOT see tool output, injected content, or a
reviewer's verdict.

#### Scenario: The validator rejects a draft
- **WHEN** the architect's graph fails validation
- **THEN** the architect receives the reason classes, and at most a bounded number of repairs
- **AND** a graph still invalid after them is recorded as a failure, not retried silently

#### Scenario: A tool returns injected text
- **WHEN** a tool's result contains an injection
- **THEN** no part of it reaches the architect

### Requirement: Every grant is justified by the prompt, and checked
Every grant in an architect's graph SHALL cite a verbatim span of the prompt that justifies it,
and a deterministic check SHALL fail any grant whose citation is missing or is not a span of
the prompt. Each graph SHALL also be compared with least-authority labels, which are approved
by the author and registered before any measured run, and every grant beyond them SHALL be
reported as a widening.

#### Scenario: A fabricated justification
- **WHEN** a grant's citation does not occur in the prompt
- **THEN** the formal review fails the graph

#### Scenario: A widening
- **WHEN** a graph grants more than its task's label, by kind or by scope
- **THEN** the widening is reported, with the grant and the label

### Requirement: The reviewer is isolated and tested before use
The independent reviewer SHALL see only the prompt and a canonicalised graph for its primary
verdict, and SHALL give a structured verdict for every grant. A second verdict, given the
architect's rationales, SHALL be reported apart.

#### Scenario: The reviewer misses too many planted widenings
- **WHEN** the reviewer's catch rate on the pre-use corpus is below the registered threshold
- **THEN** the measured run does not start
- **AND** Before a measured run, the reviewer SHALL pass a pre-use test on a pinned corpus of
  hand-widened graphs, at a threshold fixed in the registration, or the run SHALL be refused.

#### Scenario: The reviewer's model, and its catch rates
- **WHEN** a reviewer is chosen for a measured run, and its catch rates are reported
- **THEN** Its model SHALL be chosen by a rule fixed in advance, and every catch rate SHALL be
  reported with how similar the reviewer's and the architect's models are.

#### Scenario: Same-family review
- **WHEN** the architect and the reviewer are from the same model family
- **THEN** the report calls the reviewer diverse, not independent, and states its results as a
  lower bound on independence

### Requirement: Authority changes only through the graph
A run SHALL NOT acquire authority while it executes. A missing grant SHALL fail the run and
return to the architect as a graph edit, which passes the formal review and the reviewer again.
The report SHALL give autonomy, the share of consequential actions taken with no human prompt,
beside utility and attack success.

#### Scenario: A node needs a capability it was not granted
- **WHEN** a node's operation is refused for lack of a grant
- **THEN** the run fails and records which grant was missing, and no prompt or approval grants
  it mid-run

### Requirement: The pretext experiment is registered before any trial
The pretexts, the two channels (the Product Owner's prompt, and a document the architect is
given), the cells, the models by full identifier, the task hashes, the primary outcome (a
widening that the least-authority check flags and that neither the link check nor the
reviewer catches), and one confirmatory test SHALL be
committed before any trial, and approved by the author.

#### Scenario: The registration is edited after trials began
- **WHEN** the registration file differs from its committed version
- **THEN** the harness refuses to run

#### Scenario: The registration, the tasks or the tree changed
- **WHEN** a run is started after any registered input has changed
- **THEN** The harness SHALL refuse a run whose registration, tasks or imported tree have changed
  since.

#### Scenario: Registered and exploratory results
- **WHEN** a report gives registered and exploratory results
- **THEN** Registered and exploratory results SHALL never be pooled.

### Requirement: Paid model calls are gated and recorded
A model backend that costs money beyond the subscription SHALL refuse to run unless a committed
approval records the author's go and a spend ceiling. It SHALL stop at the ceiling and record
what it spent. No test or build step SHALL call it.

#### Scenario: No approval
- **WHEN** the cross-family backend is invoked with no committed approval file
- **THEN** it refuses, and makes no network call

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

### Requirement: The human review records where authority is held
The human review page and its verdict file SHALL offer, for each grant, the verdict `misplaced`: needed by the task, but held by the wrong node. It sits beside `needed`, `wider` and `not-needed`. The registered reviewer's prompt and verdict scale MUST NOT change.

#### Scenario: Needed, but held by developer code
- **WHEN** a human reviewer judges that a payment grant is needed but should sit on a library writer, not on a `Custom` node
- **THEN** the verdict file records `misplaced` for that grant, with the reviewer's note

#### Scenario: The registered reviewer
- **WHEN** the registered reviewer's prompt and scale are hashed after this change
- **THEN** the hashes equal those registered

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
