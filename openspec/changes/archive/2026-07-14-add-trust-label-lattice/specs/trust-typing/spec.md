## ADDED Requirements

### Requirement: Trust levels form a lattice with no upward coercion
The type system SHALL model trust levels as elements of a lattice with a partial order, such that a
more-trusted requirement cannot be satisfied by a less-trusted value. In particular `Untrusted<T>`
SHALL NOT be a subtype of `T`: there is no coercion that raises trust. The only way to lower trust is
an explicit, declared discharge (below).

#### Scenario: Untrusted does not inhabit the clean type
- **WHEN** a value of type `Untrusted<T>` is offered where `T` is required
- **THEN** the type system rejects the substitution, because trust cannot be raised by coercion

#### Scenario: A wider trust may satisfy a narrower requirement, never the reverse
- **WHEN** the lattice orders two trust levels
- **THEN** a value at the more-trusted level may be supplied where the less-trusted level is required,
  and never the other way around

### Requirement: Wiring checks are flow-sensitive with respect to trust
The wiring checker SHALL treat an edge as well-typed only if, in addition to data-type compatibility,
the source's trust label flows to the target's under the lattice order. Trust compatibility SHALL be
a property of the edge check itself, not a separate rule applied beside it.

#### Scenario: An edge that raises required trust without discharge is ill-typed
- **WHEN** an edge connects a source carrying `Untrusted<_>` to a target that requires a clean input,
  with no discharger between them
- **THEN** the edge is ill-typed on trust grounds, independently of whether the data types match

### Requirement: Trust discharge is a declared, typed transformation
The type system SHALL permit lowering trust only at a node explicitly declared as a discharger, and
SHALL treat discharge as producing a distinct output type rather than as silently dropping a label. A
node not declared as a discharger SHALL NOT emit a lower-trust output than its input.

#### Scenario: Only a declared discharger may lower trust
- **WHEN** a node consumes an `Untrusted<_>` input and emits a non-`Untrusted` output
- **THEN** the graph is well-typed only if that node is declared as a discharger
- **AND** the discharge yields a distinct refined type, so downstream nodes see the discharged type,
  not a relabelled original

### Requirement: Trust laundering is rejected structurally
The type system SHALL reject trust laundering — reaching a clean requirement from an untrusted source
without transiting a declared discharger — as a violation of the lattice order, not by a rule checked
independently of edge typing. Widening a consumer's declared input to the untrusted type SHALL NOT
launder trust.

#### Scenario: Widening the consumer's input does not launder trust
- **WHEN** a graph is "repaired" by widening a tool-capable node's input to `Untrusted<_>` so every
  edge type-checks
- **THEN** the graph is still rejected, because the node emits a non-`Untrusted` output from an
  `Untrusted<_>` input without being a declared discharger — a lattice violation, not a separate
  side-condition
