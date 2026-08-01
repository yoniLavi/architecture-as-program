## ADDED Requirements

### Requirement: Provisioned authority is bounded by the assembly's scope
An assembled graph SHALL support use as a scope. On exit from that scope, every capability instance
the assembly provisioned as revocable SHALL be severed, so that authority granted for a run does not
outlive the run without the host taking a deliberate step to extend it. Severing on scope exit SHALL
be idempotent and SHALL leave the assembly usable for inspection.

Assemblies used without a scope SHALL behave exactly as before, so the guarantee is opt-in at the
call site and no existing caller changes behaviour.

The guarantee SHALL be documented as reaching only instances provisioned revocable: an instance
provisioned bare has no caretaker to sever and outlives the scope.

#### Scenario: Leaving the scope severs a revocable instance
- **WHEN** a graph is assembled within a scope with a revocable capability instance, and the scope exits
- **THEN** a node's handle for that instance raises on its next use

#### Scenario: A bare instance is not severed by scope exit
- **WHEN** a graph is assembled within a scope with an instance that was not declared revocable, and the scope exits
- **THEN** that instance remains usable, and the limit is documented rather than presented as confinement

#### Scenario: Assembling without a scope is unchanged
- **WHEN** a graph is assembled without using it as a scope
- **THEN** every capability instance behaves exactly as it did before this change
