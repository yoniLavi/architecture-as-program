## ADDED Requirements

### Requirement: Clock, outbound HTTP, and notification are typed capability kinds
The runtime SHALL model access to the current time, to outbound HTTP, and to a notification channel as
declared capability kinds with typed interfaces, so that a node holding none of them cannot read a
clock, reach a network host, or notify anyone. Each SHALL be expressed as a WIT interface on the
confined tier, and a node's permitted import set SHALL be derived from its `with` clause for these
kinds by the same mechanism that derives it for existing kinds, with no special case.

An outbound HTTP capability SHALL carry the set of hosts it may reach, and a node holding it SHALL NOT
be able to reach a host outside that set.

#### Scenario: A node without a clock cannot read the time
- **WHEN** a confined node that does not declare a clock capability is built
- **THEN** its component imports no clock interface, and the derived and actual import sets agree

#### Scenario: A granted clock appears in the import set
- **WHEN** a node declares a clock capability
- **THEN** its component imports exactly that interface, and the import-set comparison passes

#### Scenario: An HTTP client cannot reach outside its allowlist
- **WHEN** a node holding an allowlisted HTTP capability attempts a request to a host not in the list
- **THEN** the attempt is refused
