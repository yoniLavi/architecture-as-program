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
When a parent routes a capability wider than the child declares, the runtime SHALL deliver a facade limited to the child's declared type (allowlist, tool set, mode, payees, cap, orders, fields), holding the parent's handle as routed so a caretaker still revokes and rotates it. A handle routed at its declared type SHALL pass through unchanged.

#### Scenario: A child declares a narrower allowlist
- **WHEN** a parent routes `HTTPClient<['a.example', 'b.example']>` to a child declaring `HTTPClient<['a.example']>`
- **THEN** a request from inside the child to `b.example` is refused at the crossing, and so is a redirect to it from an allowlisted host

#### Scenario: A child declares a narrower tool set
- **WHEN** a parent routes `LLMClient<[lookup, refund]>` to a child declaring `LLMClient<[lookup]>`
- **THEN** the model inside the child is offered `lookup` alone, on both tiers, and a call to `refund` is refused

#### Scenario: A child declares a narrower mode
- **WHEN** a parent routes a `read-write` `DBHandle` or `StateHandle` to a child declaring `read`
- **THEN** the child's handle has no write operation and exposes no route to the store behind the parent's handle

#### Scenario: Revocation still reaches the facade
- **WHEN** the parent revokes the routed instance
- **THEN** the child's next crossing through the facade fails

#### Scenario: Narrowing composes
- **WHEN** a handle is narrowed at two nested boundaries
- **THEN** the innermost child is bound by the narrowest scope, and its crossings keep the instance label the outermost parent declared

## MODIFIED Requirements

### Requirement: Assembly validates a graph together with every graph it executes
The runtime SHALL, when assembling a graph, validate it together with every canonical graph it
reaches through sub-graph nodes, transitively, so that the cross-graph analyses (signature
matching, capability narrowing, and the boundary-output check) run before execution and not only
when graphs are validated as a batch at build. Capability narrowing is checked here, and enforced
when the handle is routed (a routed handle is attenuated to the child's declared scope).

#### Scenario: A composition the cross-graph checks reject does not assemble
- **WHEN** a parent graph routes a capability into a sub-graph parameter it cannot satisfy (for
  example, a billing store into the sub-graph's knowledge-base parameter), or declares a sub-graph
  node's output narrower than the child's terminals
- **THEN** assembly raises an assembly error naming the cross-graph reason, and nothing executes

#### Scenario: The canonical composition still assembles
- **WHEN** the canonical `support-platform.json` is assembled
- **THEN** it assembles and runs as before

#### Scenario: A name collision does not skip the checks
- **WHEN** a parent is named after its own sub-graph node, or a resolver returns a sub-graph under
  another name
- **THEN** the composition is rejected before the sub-graph runs

#### Scenario: Resolver-supplied sub-graphs and name collisions are checked
- **WHEN** a caller's resolver supplies a sub-graph, or a graph or batch reuses a name
- **THEN** It SHALL also validate a parent together with a sub-graph a caller's resolver supplied before
  running it, SHALL refuse a resolved sub-graph whose name differs from its node's, and SHALL reject a graph
  containing a node of its own name and a batch in which two graphs share a name, since graphs are resolved
  by name and each collision would skip the cross-graph checks.

#### Scenario: A sub-graph node's precondition is checked
- **WHEN** a sub-graph node declares a `requires` contract
- **THEN** A sub-graph node's `requires` contract SHALL be checked as a leaf's is.

#### Scenario: Validating a graph alone is not enough for a composition
- **WHEN** a graph that contains sub-graph nodes is validated alone
- **THEN** A graph validated alone leaves the cross-graph layer silent, and a runtime that executes a
  composition the validator rejects makes "rejected before anything runs" false for composed systems.
