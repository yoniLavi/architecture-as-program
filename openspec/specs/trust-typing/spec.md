# trust-typing Specification

## Purpose
TBD - created by archiving change add-trust-label-lattice. Update Purpose after archive.
## Requirements
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

### Requirement: Principal scope narrows monotonically
A principal-bound capability SHALL narrow monotonically wherever it is routed, including across a
sub-graph composition boundary: narrowing SHALL only reduce authority, never widen it, and SHALL be
expressed as intersection over a fixed set of dimensions rather than as an open predicate language.
This keeps the set of principals a node can ever act as enumerable from the graph without executing it,
which is the property the confused-deputy argument requires.

#### Scenario: Narrowing across a composition boundary cannot widen
- **WHEN** a parent routes a principal-bound capability into a sub-graph
- **THEN** the sub-graph's view of that capability is the same principal scope or a narrower one
- **AND** an attempt to widen it is rejected

### Requirement: An outbound-host allowlist narrows monotonically at composition
A parent routing an outbound HTTP capability into a sub-graph SHALL provide a handle whose permitted
host set is equal to or a superset of what the sub-graph declares, never a subset, so that composition
cannot silently grant a child reach the parent's own handle does not have. This extends the existing
capability-narrowing analysis to a scope that is a set rather than a mode or a name.

#### Scenario: A parent cannot route a narrower allowlist than the child declares
- **WHEN** a sub-graph declares an HTTP capability over a set of hosts and the parent routes one whose
  set omits any of them
- **THEN** validation rejects the composition
