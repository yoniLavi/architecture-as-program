# Signal graph runtime

## ADDED Requirements

### Requirement: The confined tier instantiates reliably on a loaded machine
The confined tier SHALL size its engine for many short-lived stores rather than for a few long-lived
guests, so that instantiating a node does not reserve address space out of proportion to what a node
body uses. The runtime creates a fresh store per node invocation, so a per-store reservation sized for
a server is paid on every crossing into the tier and fails when the host is under memory pressure.

The reservation SHALL NOT become a correctness limit: a guest that outgrows it SHALL have its memory
reallocated rather than trapping. The benchmark SHALL build its engine from the same configuration as
the runtime, so the tier is measured as it is run.

#### Scenario: A node instantiates on a loaded machine
- **WHEN** the host is under enough memory pressure that a multi-gigabyte reservation would be refused
- **THEN** a confined node still instantiates and runs

#### Scenario: The reservation does not bound what a guest may allocate
- **WHEN** a guest's linear memory grows beyond the configured reservation
- **THEN** its memory is reallocated and execution continues

#### Scenario: The benchmark measures the configured tier
- **WHEN** the overhead benchmark runs
- **THEN** its engine carries the same configuration the runtime uses

### Requirement: A host resource failure is reported distinctly from an ungranted capability
The confined tier SHALL distinguish an instantiation that failed because the host could not allocate
resources from one that failed because the component imports a capability it was not granted. Both
failures arrive at the same place, and reporting the first as the second sends a reader hunting for a
security fault that is not there — an ungranted capability is a finding about the graph, and an
exhausted host is a finding about the machine.

#### Scenario: Resource exhaustion is named as such
- **WHEN** instantiation fails because the host cannot allocate memory for the guest
- **THEN** the error says so, and does not attribute the failure to an ungranted capability

#### Scenario: An ungranted capability is still reported as one
- **WHEN** a component imports an interface its `with` clause does not grant
- **THEN** instantiation fails naming the ungranted capability, before any guest code runs
