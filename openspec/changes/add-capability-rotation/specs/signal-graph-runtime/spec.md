## ADDED Requirements

### Requirement: A named capability instance can be rotated at runtime
The runtime SHALL allow a capability instance provisioned with a declared identity to be rotated after
assembly: re-pointed at a freshly provisioned backing handle of the same capability kind, such that a
node's subsequent use of that instance exercises the new authority through the same forwarding caretaker.
The authority to rotate a capability SHALL be distinct from the authority to use it and SHALL be held only
by the host that assembled the graph — never given to a node. Rotation SHALL be targeted: rotating one
instance SHALL NOT affect other identities of the same type, nor any shared-by-type sibling.

#### Scenario: Rotation re-points authority
- **WHEN** a node holds a rotatable capability instance and that instance is rotated to a new backing
  handle
- **THEN** the node's next use of the instance is served by the new handle
- **AND** before rotation the same use was served by the original handle

#### Scenario: Rotation is targeted to one instance
- **WHEN** two nodes hold distinct-identity instances of the same capability type and one instance is
  rotated
- **THEN** the rotated instance's node observes the new authority
- **AND** the other instance — and any shared-by-type sibling — is unchanged

#### Scenario: Nodes cannot rotate
- **WHEN** a rotatable capability is provisioned
- **THEN** the rotate authority is held only by the host that assembled the graph, and no node receives a
  means to rotate any capability

#### Scenario: Rotation preserves the capability kind
- **WHEN** the host attempts to rotate an instance to a replacement of a different capability kind
- **THEN** the runtime rejects the rotation, so the surface the node holds cannot change kind underneath it

## MODIFIED Requirements

### Requirement: Revocation is opt-in and leaves un-revoked provisioning unchanged
The runtime SHALL wrap in a forwarding caretaker only capability instances explicitly provisioned as
revocable or rotatable; type-only and plain-identity instances SHALL be provisioned exactly as before, so
graphs that use neither revocation nor rotation are unaffected. An instance MAY be declared revocable,
rotatable, or both; the runtime SHALL expose the revoke operation only for revocable instances and the
rotate operation only for rotatable instances, so the two authorities are granted independently.

#### Scenario: Non-managed capabilities are unchanged
- **WHEN** a graph declares no revocable and no rotatable capability
- **THEN** provisioning behaves exactly as without these changes, and existing graphs and their tests pass
  unchanged

#### Scenario: Revocation and rotation are granted independently
- **WHEN** an instance is declared rotatable but not revocable
- **THEN** the host can rotate it but the runtime exposes no revoke authority for it, and vice versa
