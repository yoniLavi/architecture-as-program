## ADDED Requirements

### Requirement: Nodes may carry checkable pre- and postconditions
A node SHALL be able to declare preconditions over its inputs and postconditions over its outputs,
expressed as conjunctions of predicates over field paths of its already-declared types. The predicate
vocabulary SHALL be closed — comparisons, membership in a declared variant set, and field presence — with no
quantification, recursion, or embedded code, so that a contract remains checkable without a solver and
without a new dependency.

The runtime SHALL evaluate preconditions before invoking a node body and postconditions after, and a
violation SHALL carry **blame**: a failed precondition attributes fault to the upstream wiring, a
failed postcondition to the node body.

The validator SHALL reject a contract referencing a field absent from the node's declared types, so an
unevaluatable contract fails at assembly rather than at run time.

#### Scenario: A precondition violation blames upstream
- **WHEN** a node receives an input violating its declared precondition
- **THEN** the run fails with a contract violation attributing fault to the wiring that supplied it

#### Scenario: A postcondition violation blames the node body
- **WHEN** a node body emits an output violating its declared postcondition
- **THEN** the run fails with a contract violation attributing fault to that node's implementation

#### Scenario: An unevaluatable contract is rejected at assembly
- **WHEN** a contract references a field the node's declared types do not contain
- **THEN** validation rejects the graph rather than deferring the error to execution
