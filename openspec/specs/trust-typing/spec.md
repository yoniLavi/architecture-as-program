# trust-typing Specification

## Purpose
TBD - created by archiving change add-trust-label-lattice. Update Purpose after archive.

## Requirements

### Requirement: Trust levels form a lattice with no upward coercion
The type system SHALL model trust levels as elements of a lattice with a partial order, such that a
more-trusted requirement cannot be satisfied by a less-trusted value. In particular `Untrusted<T>`
SHALL NOT be a subtype of `T`: there is no coercion that raises trust. The only way to raise trust is
an explicit, declared discharge (below).

#### Scenario: Untrusted does not inhabit the clean type
- **WHEN** a value of type `Untrusted<T>` is offered where `T` is required
- **THEN** the type system rejects the substitution, because trust cannot be raised by coercion

#### Scenario: A wider trust may satisfy a narrower requirement, never the reverse
- **WHEN** the lattice orders two trust levels
- **THEN** a value at the more-trusted level may be supplied where the less-trusted level is required,
  and never the other way around

### Requirement: Trust discharge is a declared, typed transformation
The type system SHALL permit raising trust only at a node explicitly declared as a discharger, and
SHALL treat discharge as producing a distinct output type rather than as silently dropping a label. A
node not declared as a discharger SHALL NOT emit a higher-trust output than its input. A node holding a
tool-scoped `LLMClient<[...]>` SHALL NOT be declared a discharger, and SHALL NOT consume `Untrusted<_>`
input: untrusted data reaches a tool-capable node only after an upstream discharger. Because narrowing is
checked but not enforced, a parent SHALL NOT route a tool-scoped client into a sub-graph's inference-only
slot, where the node holding it would escape this rule.

#### Scenario: Only a declared discharger may lower trust
- **WHEN** a node consumes an `Untrusted<_>` input and emits a non-`Untrusted` output (raising the
  data's trust; the scenario's title predates the lattice's orientation)
- **THEN** the graph is well-typed only if that node is declared as a discharger
- **AND** the discharge yields a distinct refined type, so downstream nodes see the discharged type,
  not a relabelled original

#### Scenario: A tool-capable node is not a discharger and takes no untrusted input
- **WHEN** a node holding a tool-scoped client consumes `Untrusted<_>`, whether or not its outputs stay
  untrusted and whether or not it is declared a discharger
- **THEN** the graph is rejected

### Requirement: Trust laundering is rejected structurally
The type system SHALL reject trust laundering — reaching a clean requirement from an untrusted source
without transiting a declared discharger — as a violation of the lattice order, not by a rule checked
independently of edge typing. Widening a consumer's declared input to the untrusted type SHALL NOT
launder trust. A node's output SHALL be checked per variant, since each variant leaves on its own port, and a
role SHALL name exactly one variant (a repeated role would let a second variant leave on a port the
edge check resolved to the first),
and an input SHALL count as untrusted when `Untrusted<_>` appears anywhere inside it; a sub-graph's
boundary output SHALL keep trust in its comparison with the child's terminals. Laundering through an
undeclared node is a lattice violation; laundering by declaring a tool-capable consumer a discharger is
caught by the sink rule beside the lattice (see "Trust discharge is a declared, typed transformation").

#### Scenario: Widening the consumer's input does not launder trust
- **WHEN** a graph is "repaired" by widening a tool-capable node's input to `Untrusted<_>` so every
  edge type-checks
- **THEN** the graph is still rejected, because the node emits a non-`Untrusted` output from an
  `Untrusted<_>` input without being a declared discharger — a lattice violation, not a separate
  side-condition

#### Scenario: One untrusted variant does not license a clean sibling
- **WHEN** that repaired node's output is a sum with one variant marked `Untrusted<_>` and another clean
- **THEN** the graph is rejected on the clean variant, as the same lattice violation

### Requirement: Principal scope narrows monotonically
A run's principal SHALL never widen wherever the run is routed, including across a sub-graph
composition boundary. The runtime achieves this structurally: a sub-graph is assembled with its
parent's principal and has no way to supply another, and only a node declared `binds_principal` may
extend the chain of parties acting on its behalf. No capability instance is bound to the principal — it
is recorded and propagated only — and binding one SHALL NOT be described as implemented until it is. *Narrowing* a principal — by intersection over a fixed
set of dimensions, so the principals a node can act as stay enumerable from the graph — is the recorded
design and SHALL NOT be described as implemented until it is: today a node cannot attenuate the principal
it was given, and the validator cannot say statically which principals a node could act as.

#### Scenario: Narrowing across a composition boundary cannot widen
- **WHEN** a parent runs a sub-graph under a principal
- **THEN** the sub-graph acts for exactly the parent's principal, since it is assembled with it
- **AND** no path exists for the sub-graph to supply a wider one

### Requirement: An outbound-host allowlist narrows monotonically at composition
A parent routing an outbound HTTP capability into a sub-graph SHALL provide a handle whose permitted
host set is equal to or a superset of what the sub-graph declares, never a subset, so that composition
cannot silently grant a child reach the parent's own handle does not have. This extends the existing
capability-narrowing analysis to a scope that is a set rather than a mode or a name.

#### Scenario: A parent cannot route a narrower allowlist than the child declares
- **WHEN** a sub-graph declares an HTTP capability over a set of hosts and the parent routes one whose
  set omits any of them
- **THEN** validation rejects the composition

### Requirement: Wiring checks carry trust
The wiring checker SHALL treat an edge as well-typed only if, in addition to data-type compatibility,
the source's trust level is at or above the level the target requires, in the lattice ordered by
trustworthiness (`Untrusted ⊑ Trusted`, the reverse of the flows-to order of integrity labels). Trust
compatibility SHALL be a property of the edge check itself, not a separate rule applied beside it. Labels
are fixed by declared types, so the check is not flow-sensitive in the information-flow sense.

#### Scenario: An edge that raises required trust without discharge is ill-typed
- **WHEN** an edge connects a source carrying `Untrusted<_>` to a target that requires a clean input,
  with no discharger between them
- **THEN** the edge is ill-typed on trust grounds, independently of whether the data types match
