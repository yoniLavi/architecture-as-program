## ADDED Requirements

### Requirement: A named capability instance can be revoked at runtime
The runtime SHALL allow a capability instance provisioned with a declared identity to be revoked after
assembly, such that a node's subsequent use of that instance fails rather than exercising authority.
Revocation SHALL be modelled as severable indirection: the node holds a forwarding caretaker, and a
separate revoke authority — never given to a node — severs it. The authority to revoke a capability
SHALL be distinct from the authority to use it.

#### Scenario: Revocation severs authority
- **WHEN** a node holds a revocable capability instance and that instance is revoked
- **THEN** the node's next use of the instance fails with a revoked-capability error
- **AND** before revocation the same use succeeds

#### Scenario: Revocation is targeted to one instance
- **WHEN** two nodes hold distinct-identity instances of the same capability type and one instance is
  revoked
- **THEN** the revoked instance's node fails on use
- **AND** the other instance — and any shared-by-type sibling — remains fully usable

#### Scenario: Nodes cannot revoke
- **WHEN** a revocable capability is provisioned
- **THEN** the revoke authority is held only by the host that assembled the graph, and no node receives
  a means to revoke any capability

### Requirement: Revocation is opt-in and leaves un-revoked provisioning unchanged
The runtime SHALL wrap only capability instances explicitly provisioned as revocable; type-only and
plain-identity instances SHALL be provisioned exactly as before, so graphs that do not use revocation
are unaffected.

#### Scenario: Non-revocable capabilities are unchanged
- **WHEN** a graph declares no revocable capability
- **THEN** provisioning behaves exactly as without this change, and existing graphs and their tests
  pass unchanged
