## ADDED Requirements

### Requirement: Revocation composes to the confined tier
The runtime SHALL enforce revocation of a capability instance for a node running on the confined (WASM
component) tier as well as the host tier: once an instance is revoked, a sandboxed node that binds it SHALL
fail on its next capability crossing rather than exercising the withdrawn authority. This enforcement SHALL
hold at the WIT capability boundary; it makes no claim at the memory level (CHERI remains a follow-up).

#### Scenario: A sandboxed node cannot exercise a revoked instance
- **WHEN** a node running on the confined tier binds a revocable capability instance and that instance is
  revoked
- **THEN** the node's next call across the capability boundary fails with a revoked-capability error
- **AND** before revocation the same call succeeds

#### Scenario: The revoked-instance escape is recorded in the hostile-node suite
- **WHEN** the hostile-node suite runs a sandboxed node's attempt to use a revoked instance
- **THEN** the attempt fails on the confined tier, asserted alongside the filesystem, network,
  environment, and ungranted-capability escapes, so the confinement result is a recorded fact
