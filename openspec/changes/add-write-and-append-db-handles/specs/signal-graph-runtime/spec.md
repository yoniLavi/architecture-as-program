## ADDED Requirements

### Requirement: The runtime provisions write-capable and append-only database handles
The runtime SHALL provision a `DBHandle` in `read-write` mode as a handle exposing both read and write
operations, and a `DBHandle` in `append` mode as a handle exposing an append operation and **no** read
operation, so that each handle's surface matches its declared mode and no handle grants authority its mode
does not name. Provisioning a `DBHandle` whose mode the runtime does not model SHALL raise a loud error
rather than silently substituting another mode. `read`-mode provisioning SHALL be unchanged.

#### Scenario: A read-write handle can read and write
- **WHEN** a `DBHandle<scope, read-write>` is provisioned
- **THEN** the handle exposes a read operation and a write operation, and a value written through it is
  visible to a subsequent read through the same handle

#### Scenario: An append-only handle can append but cannot read
- **WHEN** a `DBHandle<scope, append>` is provisioned
- **THEN** the handle exposes an append operation
- **AND** the handle exposes no read operation, mirroring the least-authority discipline of the other handles

#### Scenario: An unmodelled DBHandle mode is rejected
- **WHEN** a `DBHandle` is provisioned with a mode the runtime does not model
- **THEN** provisioning raises an error that names the modes the runtime does model

### Requirement: The SupportPlatform composition graph assembles and routes identity end-to-end
The runtime SHALL assemble the canonical `SupportPlatform` graph without error, since every capability it
declares is now provisionable, and SHALL route the distinct `ResponseChannel<user-session>` identities
declared in the graph source to the sub-graph nodes that declare them, so the shipped composition graph — not
only a synthetic stand-in — exercises capability-identity routing across a sub-graph boundary.

#### Scenario: The shipped composition graph assembles
- **WHEN** the canonical `SupportPlatform` graph is assembled
- **THEN** assembly succeeds and every declared capability is provisioned

#### Scenario: Graph-declared identities route to the correct sub-graphs
- **WHEN** the assembled `SupportPlatform` graph is inspected
- **THEN** the `CustomerSupport` and `BillingService` sub-graph nodes each receive a distinct
  `ResponseChannel<user-session>` instance matching the identity declared for it in the graph source
