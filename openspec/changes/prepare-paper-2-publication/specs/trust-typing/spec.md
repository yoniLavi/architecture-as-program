## RENAMED Requirements

- FROM: `### Requirement: Wiring checks are flow-sensitive with respect to trust`
- TO: `### Requirement: Wiring checks carry trust`

## MODIFIED Requirements

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

### Requirement: Trust laundering is rejected structurally
The type system SHALL reject trust laundering — reaching a clean requirement from an untrusted source
without transiting a declared discharger — as a violation of the lattice order, not by a rule checked
independently of edge typing. Widening a consumer's declared input to the untrusted type SHALL NOT
launder trust. A node's output SHALL be checked per variant, since each variant leaves on its own port,
and an input SHALL count as untrusted when `Untrusted<_>` appears anywhere inside it; a sub-graph's
boundary output SHALL keep trust in its comparison with the child's terminals.

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
A principal-bound capability SHALL never widen wherever it is routed, including across a sub-graph
composition boundary. The runtime achieves this structurally: a sub-graph is assembled with its
parent's principal and has no way to supply another, and only a node declared `binds_principal` may
extend the chain of parties acting on its behalf. *Narrowing* a principal — by intersection over a fixed
set of dimensions, so the principals a node can act as stay enumerable from the graph — is the recorded
design and SHALL NOT be described as implemented until it is: today a node cannot attenuate the principal
it was given, and the validator cannot say statically which principals a node could act as.

#### Scenario: Narrowing across a composition boundary cannot widen
- **WHEN** a parent routes a principal-bound capability into a sub-graph
- **THEN** the sub-graph acts for exactly the parent's principal, since it is assembled with it
- **AND** no path exists for the sub-graph to supply a wider one
