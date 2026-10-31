## ADDED Requirements

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
architect's rationales, SHALL be reported apart. Before a measured run, the reviewer SHALL pass
a pre-use test on a pinned corpus of hand-widened graphs, at a threshold fixed in the
registration, or the run SHALL be refused. Its model SHALL be chosen by a rule fixed in
advance, and every catch rate SHALL be reported with how similar the reviewer's and the
architect's models are.

#### Scenario: The reviewer misses too many planted widenings
- **WHEN** the reviewer's catch rate on the pre-use corpus is below the registered threshold
- **THEN** the measured run does not start

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
committed before any trial, and approved by the author. The harness SHALL refuse a run whose
registration, tasks or imported tree have changed since. Registered and exploratory results
SHALL never be pooled.

#### Scenario: The registration is edited after trials began
- **WHEN** the registration file differs from its committed version
- **THEN** the harness refuses to run

### Requirement: Paid model calls are gated and recorded
A model backend that costs money beyond the subscription SHALL refuse to run unless a committed
approval records the author's go and a spend ceiling. It SHALL stop at the ceiling and record
what it spent. No test or build step SHALL call it.

#### Scenario: No approval
- **WHEN** the cross-family backend is invoked with no committed approval file
- **THEN** it refuses, and makes no network call
