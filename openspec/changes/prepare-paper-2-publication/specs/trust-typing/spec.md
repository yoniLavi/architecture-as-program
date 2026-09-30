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
