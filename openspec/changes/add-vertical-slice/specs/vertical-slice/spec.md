## ADDED Requirements

### Requirement: The slice runs every step of the north star and records each
The repository SHALL run, on a small set of banking tasks, all eight steps of the north star:
the prompt, the architect, the formal review, the AI reviewer, the developer, minimisation, the
owner's evaluation, and the architecture review. It SHALL record each step's input and output
whole, and SHALL render a report from those records alone, calling no model. A step that is
stubbed SHALL be recorded as a stub.

#### Scenario: A step is stubbed
- **WHEN** a step of the slice has no real implementation
- **THEN** its records and the report say it was stubbed

### Requirement: A developer gains authority only through a reviewed graph edit
A developer SHALL either return a body held to its node's derived import gate, or escalate
with a structured request for a capability. An escalation SHALL reach the architect as a
graph edit request, and the edited graph SHALL pass the formal review and the AI reviewer
again before anything runs. No text in a developer's or the architect's context SHALL grant
authority.

#### Scenario: A developer is told an approval was given
- **WHEN** a pretext in the developer's context claims a wider grant was approved
- **THEN** the developer's component is still held to its node's clause by the gate
- **AND** any wider grant appears only as an escalation, which is reviewed again

### Requirement: Human verdicts are recorded beside the automated ones
The author's verdicts on each final graph, per grant and on the outcome, SHALL be recorded in
committed files beside the AI reviewer's verdicts and the labels. They SHALL be reported as one
person's judgement, never as a study.

#### Scenario: The author flags a grant the AI reviewer passed
- **WHEN** the author's verdict on a grant differs from the AI reviewer's
- **THEN** the report shows both, and the labels' verdict, side by side
