## ADDED Requirements

### Requirement: Capability boundaries are typed WIT interfaces
The runtime SHALL provide a component execution tier in which each capability kind is expressed as a
typed WebAssembly Interface Types (WIT) interface, and a node body runs as a WASM component that
imports exactly the interfaces named by its `with` clause. The host and node SHALL exchange typed
values across these interfaces rather than a flat byte ABI, so that a value which does not match an
interface's declared type is a boundary error rather than a marshalling accident.

#### Scenario: A node imports exactly the capability interfaces its signature declares
- **WHEN** a node declaring `with LLMClient<[lookup]>, DBHandle<'knowledge-base', read>` is
  instantiated on the component tier
- **THEN** its component imports the typed LLM interface (offering only `lookup`) and the typed
  read-only knowledge-base interface, and no other capability interface
- **AND** a capability the node did not declare is not present in its imported world and cannot be
  named from within the component

#### Scenario: A type-mismatched value at the boundary is rejected
- **WHEN** a value that does not conform to a capability interface's WIT type is passed across the
  boundary
- **THEN** the mismatch is caught at the typed boundary rather than being reinterpreted as raw bytes

### Requirement: A component node imports no ambient WASI functions
The runtime SHALL, on the component tier, produce node components whose import set contains only their
typed capability interfaces and no ambient WASI functions. This strengthens "no ambient authority"
from a property of an empty runtime context (behind powerless WASI stubs, as on the core-wasm tier)
to the absence of the imports themselves.

#### Scenario: The component's import set contains no WASI functions
- **WHEN** a node component is inspected for its imports
- **THEN** the import set contains only the node's declared capability interfaces
- **AND** no filesystem, socket, environment, or clock function appears among the imports at all

#### Scenario: The hostile-node suite still denies every escape on the component tier
- **WHEN** the hostile-node attacks (filesystem, network, environment, ungranted capability) are run
  against a node on the component tier
- **THEN** each attempt fails, as it does on the core-wasm tier, so the confinement result is
  preserved rather than weakened by the port
