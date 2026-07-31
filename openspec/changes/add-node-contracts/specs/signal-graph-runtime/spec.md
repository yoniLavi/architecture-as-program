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

A malformed contract SHALL be rejected by the graph validator, and a contract referencing a field the
node's value type does not carry SHALL be rejected at assembly, so an unevaluatable contract fails
before execution rather than during it. The split reflects what each layer can know: the validator is
dependency-free and has no field schema for a declared type name, so it checks that a predicate parses;
assembly, which holds the value classes, checks that the paths resolve.

#### Scenario: A precondition violation blames upstream
- **WHEN** a node receives an input violating its declared precondition
- **THEN** the run fails with a contract violation attributing fault to the wiring that supplied it

#### Scenario: A postcondition violation blames the node body
- **WHEN** a node body emits an output violating its declared postcondition
- **THEN** the run fails with a contract violation attributing fault to that node's implementation

#### Scenario: A malformed contract is rejected by the validator
- **WHEN** a node declares a predicate outside the closed vocabulary
- **THEN** graph validation rejects it rather than deferring the error to execution

#### Scenario: An unresolvable field is rejected at assembly
- **WHEN** a contract references a field the node's value type does not carry
- **THEN** assembly fails rather than the run failing part-way through
