## ADDED Requirements

### Requirement: Node-local state is a typed capability
The runtime SHALL provide `StateHandle<'name', read>` and `StateHandle<'name', read-write>` as capability kinds, each a typed WIT interface backed by a host-side store, with no stateful combinator or feedback edge.

#### Scenario: A read-write handle narrows to read
- **WHEN** a graph routes `StateHandle<'seen', read-write>` where `StateHandle<'seen', read>` is declared
- **THEN** validation accepts it, and a handle for a different store name is rejected

#### Scenario: A read handle cannot write
- **WHEN** a node holding `StateHandle<'seen', read>` attempts a put, on either tier
- **THEN** the attempt is refused at the handle or has no interface to call

#### Scenario: State survives a restart
- **WHEN** a value is put and the driver process exits and restarts
- **THEN** the value is read back unchanged

### Requirement: Outbound HTTP performs bounded real fetches
The `HTTPClient` handle SHALL perform real GET requests only to allowlisted hosts over http or https, with a response size cap, a timeout, and redirects followed only to allowlisted hosts, and SHALL keep a canned-response mode as the default for tests.

#### Scenario: A redirect leaves the allowlist
- **WHEN** an allowlisted host redirects to a host outside the allowlist
- **THEN** the redirect is refused at the handle and never followed, and no request is made to the off-list host

#### Scenario: A refused redirect does not fail the run
- **WHEN** a node reads several URLs through the operation that returns failures as values, and one answers with a redirect off the allowlist
- **THEN** that URL is reported as a failed fetch and the others are still read, while a request the node itself makes to an off-list host still raises

#### Scenario: An oversized response
- **WHEN** a response exceeds the size cap
- **THEN** the fetch fails with a size error and no partial body is returned

### Requirement: A driver runs a graph on a schedule
The runtime SHALL provide a driver that executes one tick of a graph and exits, or ticks it on an interval, refusing to run while another driver holds the lock and recording each run's trace under `var/runs/`.

#### Scenario: Two drivers
- **WHEN** a second driver starts while one holds the lock
- **THEN** the second exits with an error and runs nothing

### Requirement: A sub-graph node may be applied to each element of a list
A sub-graph node declaring `"each": true` SHALL take `List<T>` and emit `List<U>`, where `T` and `U` are the referenced graph's boundary input and output, and the runtime SHALL run one isolated child run per element, in list order, collecting outputs in order.

#### Scenario: Elements are isolated
- **WHEN** a list of three items is triaged by a per-item sub-graph
- **THEN** three child runs execute, and no node in any child run receives more than one element

#### Scenario: A failing element
- **WHEN** one element's child run fails
- **THEN** the parent run fails naming the element's index, and no partial list is emitted

### Requirement: A node may join several inputs by position
A node SHALL be permitted several data inputs when each is fed by exactly one edge naming its position, and the runtime SHALL run it once, when every position holds a value, delivering values by position rather than by arrival order.

#### Scenario: Arrival order does not matter
- **WHEN** the same join receives its inputs in two different arrival orders
- **THEN** its output and trace are identical

#### Scenario: A join that can never fire
- **WHEN** a join's input positions are fed from mutually exclusive variants of one sum
- **THEN** validation rejects the graph, and a run ending with a join still waiting is refused

### Requirement: The LLM backend can be the local Claude CLI
The runtime SHALL provide an LLM backend that calls `claude -p` with no tools, no session persistence and none of the user's or repository's instructions, in an empty temporary directory, without passing an API key through, and SHALL keep the deterministic stub as the backend for every test and build step.

#### Scenario: No test calls a model
- **WHEN** the test suite and `make build` run
- **THEN** no `claude` process is started

#### Scenario: The subscription is nearly spent
- **WHEN** the CLI reports a usage window at or above the backend's ceiling
- **THEN** the next call is refused without starting a process, and the caller is told to stop and resume later

### Requirement: A host binding written short is not reported as an ungranted capability
The confined tier SHALL distinguish a component that imports an interface it was not granted from a component that calls a function of a granted interface which the host's binding omits, and SHALL report the second as a fault of the host adapter.

#### Scenario: A granted interface is bound without one of its functions
- **WHEN** a component calls `fetch` on an `http-client` the host bound with only `get`
- **THEN** instantiation fails naming the incomplete binding, not an ungranted capability

### Requirement: A routed handle is attenuated to the child's declared scope
When a parent routes a capability to a sub-graph, the runtime SHALL deliver a facade limited to the child's declared type (mode, tool set, allowlist, store name), keeping the caretaker so revocation still reaches it. This requirement is implemented only after Paper 2 publishes, together with Paper 2 version 1.1.

#### Scenario: A child declares a narrower allowlist
- **WHEN** a parent routes `HTTPClient<['a.example', 'b.example']>` to a child declaring `HTTPClient<['a.example']>`
- **THEN** a request from inside the child to `b.example` is refused at the crossing

#### Scenario: Revocation still reaches the facade
- **WHEN** the parent revokes the routed instance
- **THEN** the child's next crossing through the facade fails
