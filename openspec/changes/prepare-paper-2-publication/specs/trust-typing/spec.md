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
