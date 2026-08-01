## ADDED Requirements

### Requirement: A run binds a principal, and only declared nodes may rebind it
An assembled graph SHALL support binding a principal representing the authenticated party on whose
behalf the run executes. A node MAY declare that it binds a principal; such a node SHALL be the only kind licensed to
rebind the acting principal for the work downstream of it, mirroring the discipline by which only a
declared discharger may raise trust. A graph assembled without a principal SHALL behave exactly as it
did before this capability existed.

The validator SHALL reject a node that declares principal binding while holding no capabilities, since
a binder with no authority to scope is a declaration with no meaning.

#### Scenario: A run without a principal is unchanged
- **WHEN** a graph is assembled without binding a principal
- **THEN** every capability behaves exactly as it did before, and no crossing records a principal

#### Scenario: A non-binder cannot rebind the acting principal
- **WHEN** a node that does not declare principal binding attempts to act as a different principal
- **THEN** the attempt fails rather than silently widening authority

### Requirement: Capability crossings record the acting principal
Every recorded capability crossing SHALL carry, where a run binds a principal, the principal on whose
authority it was made, together with the chain of parties acting on that principal's behalf, so that
delegation is visible in the trace rather than inferred. Sub-graph runs SHALL record it at every
altitude.

This SHALL make the confused-deputy property checkable: no crossing anywhere in a run SHALL record a
principal outside the scope bound at entry unless it passed through a node declared to bind one.

#### Scenario: The confused-deputy property is checkable from the trace
- **WHEN** a run binds a principal and executes, including through a sub-graph
- **THEN** every crossing at every altitude records that principal or a narrowing of it
- **AND** a crossing recording a principal outside that scope, absent a declared binder, is detectable
