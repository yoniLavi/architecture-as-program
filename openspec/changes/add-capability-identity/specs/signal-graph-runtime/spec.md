## ADDED Requirements

### Requirement: Capability identity is expressible at the graph boundary
The runtime SHALL allow distinct instances of the same capability type to be named at the graph
boundary and routed to specific nodes, so that capability *identity* — not merely capability *type* —
can be expressed. When a graph does not declare any identity for a capability, the runtime SHALL
provision it by type as before, so identity is opt-in and simple graphs are unaffected.

#### Scenario: Two same-typed capabilities are provisioned as distinct instances
- **WHEN** a graph declares two capabilities of the same type with distinct identities and routes each
  to a different node
- **THEN** each node receives its own handle instance
- **AND** an operation on one instance (for a stateful handle) does not affect the other

#### Scenario: Type-only provisioning is preserved by default
- **WHEN** a graph declares a capability with no identity
- **THEN** the runtime provisions it by type exactly as before, and existing graphs behave unchanged

### Requirement: Stateful capabilities are not silently aliased by type
The runtime SHALL NOT, when an identity is specified, share a single handle instance across nodes that
declare the same capability type. This closes the aliasing gap that is harmless for read-only handles
but wrong for stateful, rate-limited, or revocable ones, and provides the nameable identity a later
revocation mechanism requires.

#### Scenario: Independent state across identically-typed handles
- **WHEN** two nodes each hold a stateful capability of the same type but distinct identity (e.g.
  independent rate-limit counters)
- **THEN** the state of one handle is independent of the other, rather than shared through a single
  aliased object

#### Scenario: A nameable identity exists for later revocation
- **WHEN** a capability instance is provisioned with a declared identity
- **THEN** that identity names the specific instance, so a future revocation or rotation mechanism can
  target it without affecting other instances of the same type
