# agentdojo-evaluation Specification

## Purpose
Signal graphs run inside AgentDojo's banking suite and are scored by its unchanged scorer.
Predictions are committed before a graph's measured run, and an undefended baseline is
recorded beside them. Created by archiving `add-agentdojo-banking-harness` on 29 October 2026.

## Requirements

### Requirement: A signal graph runs inside AgentDojo's own scorer
The repository SHALL run a signal graph as an AgentDojo pipeline element, with every
capability handle backed by AgentDojo's tool runtime and its scope checked before the call,
and SHALL score utility and attack success with AgentDojo's unchanged scorer at a pinned
commit. AgentDojo SHALL live in its own dependency group, unreachable from `scripts/` and
from the evaluation Paper 2 typesets.

#### Scenario: An oracle graph is scored
- **WHEN** a hand-written banking graph runs through the harness
- **THEN** AgentDojo's scorer reports its utility and its security per injection
- **AND** the result is labelled an oracle plan, not a benchmark result

#### Scenario: A handle is asked to exceed its scope
- **WHEN** a node holding `Payments<[payees], cap>` asks to pay someone off the list, or more
  than the cap
- **THEN** the crossing refuses it before AgentDojo's tool runs

### Requirement: Banking authority is narrower than a tool
The capability vocabulary SHALL include banking kinds that narrow on arguments: payees and an
amount cap, which scheduled orders and fields, which profile fields. It SHALL include one
kind, `Credentials`, that no graph may be granted. These kinds SHALL be in the full
vocabulary only and SHALL NOT change any figure Paper 2 typesets.

#### Scenario: A graph grants credentials
- **WHEN** a graph's `with` clause grants `Credentials`
- **THEN** the validator rejects it, by a pinned reason class

#### Scenario: Paper 2 is unaffected
- **WHEN** the banking kinds are added
- **THEN** `tests/test_paper2_figures_pinned.py` passes unchanged

### Requirement: Graphs compose from a fixed node library
A graph evaluated on AgentDojo SHALL be composed of nodes from a fixed library of generic tool,
selector, and inference-only extraction nodes, so that an architect writes wiring and
parameters and no code. Each library node SHALL be held to its `with` clause by the
derivation gate; if it runs on the host tier instead, the report SHALL say so.

#### Scenario: A library node over-imports
- **WHEN** a library component imports an interface its clause does not grant
- **THEN** the test suite fails, and with it the pre-commit gate

#### Scenario: A pure library node
- **WHEN** a library node holds no capability
- **THEN** it runs on the host tier, and the report says so

### Requirement: Exclusive branches may merge
The validator SHALL accept several edges into one input position of a node declaring
`merge: true` only if every pair of them lies on different variants of one sum, so that at
most one value arrives. Without the marker, the one-edge-per-position rule of a join SHALL hold
unchanged.

#### Scenario: A lookup that may fail rejoins a report
- **WHEN** the `found` and `none` branches of one lookup both feed a merge position
- **THEN** the validator accepts the graph, and the runtime runs the merge once

#### Scenario: Branches that can both fire
- **WHEN** two edges into a merge position are not on exclusive variants
- **THEN** the validator rejects the graph, by a pinned reason class

### Requirement: The comparison runs on the same model
The repository SHALL provide an undefended tool-calling agent on the same Claude models, run on
the subscription, and report its utility and attack success on the banking suite beside any
graph result. No figure from another model SHALL be presented as a same-model comparison.

#### Scenario: A baseline from published results
- **WHEN** a published number for CaMeL, FIDES or Progent is reported
- **THEN** it is labelled with the model it was measured on

### Requirement: Predictions precede measurement
For each graph and each task–injection pair, a static prediction (impossible, bounded or
residual) SHALL be derived and committed before the graph's measured run. A 0% attack-success
rate SHALL NOT be reported as the absence of a residual, because AgentDojo scores only its own
goals.

#### Scenario: A measured pair contradicts its prediction
- **WHEN** a pair predicted impossible succeeds
- **THEN** the report lists it as a contradiction, and the prediction is not edited
