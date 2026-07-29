## ADDED Requirements

### Requirement: The inspector renders the canonical graph sources

The inspector SHALL render its graph view from the canonical `graphs/*.json` files (directly or via an endpoint that serves them unmodified) and SHALL NOT maintain a parallel representation of any graph, so the rendered structure cannot drift from what the validator checks and the runtime executes — the same single-source-of-truth discipline as the generated SVG figures.

#### Scenario: The view reflects the canonical source

- **WHEN** a canonical graph JSON changes
- **THEN** the inspector's rendering of that graph reflects the change with no edit to UI code or data

#### Scenario: Node and edge detail comes from the source

- **WHEN** a user selects a node or edge
- **THEN** the displayed signature, capability `with` clause, instance names, and trust annotations are those parsed from the canonical JSON

### Requirement: Execution is triggered server-side through the existing runtime

The inspector SHALL trigger graph execution through a thin server-side API that calls the existing `poc` assemble/execute path — the same code path the tests and the evaluation harness exercise — and SHALL return the structured execution trace as its response. The UI SHALL NOT embed a second execution engine, and WASM components SHALL run under the server's `wasmtime`, not in the browser.

#### Scenario: A run returns the runtime's own trace

- **WHEN** a user triggers execution of a canonical graph with a chosen input and tier configuration
- **THEN** the server executes it via the `poc` runtime and responds with the schema-valid trace that run produced

#### Scenario: Unsafe wiring is refused, visibly

- **WHEN** execution is requested for a graph that fails validation
- **THEN** the API returns the validator's rejection with its reason class, and the inspector displays it — the assembly-time gate is part of what the inspector demonstrates

### Requirement: The trace overlay makes trust and capability flow visible

The inspector SHALL overlay a returned trace on the graph view, showing per-node enforcement tier, the trust label of each value flowing on each edge, capability crossings attributed to their instance names, and nested sub-graph runs. It SHALL include a guided prompt-injection walkthrough in which the propagating `Untrusted` taint, the sole discharge point, and the host-vs-confined contrast are each visible.

#### Scenario: Taint propagation is visible on the graph

- **WHEN** the prompt-injection scenario's trace is overlaid
- **THEN** the path carrying `Untrusted` data is visually distinguished up to the declared discharge node, and nowhere after it

#### Scenario: The tier contrast is visible

- **WHEN** the same scenario is run on the host tier and the confined tier
- **THEN** the overlay shows which tier ran each node and surfaces the recorded difference between the two runs

### Requirement: The corpus build does not depend on the UI toolchain

`make build` and the pre-commit hooks SHALL succeed on a machine with no Node toolchain installed, and no dependency from `ui/` SHALL enter `scripts/` or the `poc` dependency group. UI builds and checks are separate, opt-in targets.

#### Scenario: Paper build is unaffected

- **WHEN** `make build` runs on a machine without Node
- **THEN** the full corpus builds exactly as before this change

#### Scenario: The Python-side API surface is tested without the UI

- **WHEN** the pytest suite runs
- **THEN** the execution API's contract (graph serving, run triggering, trace and rejection responses) is covered by Python tests that do not require the UI to be built
