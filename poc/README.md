# Executable signal-graph runtime (PoC)

The runtime increment of the *Architecture as Program* proof of concept. It takes the
**same** canonical graph JSON that drives the proposal's figures (`graphs/customer-support.json`),
instantiates each node with **injected capability handles**, and runs signals through it.

Where the existing `scripts/` toolchain proves the *static* layer (edge typing, trust
propagation, capability narrowing), this proves the *executable* layer: that capabilities can
actually be injected, that a node cannot exceed the authority its signature declares, and that
the unsafe wirings the proposal calls "ill-typed" really are rejected before anything runs.

## Run it

```sh
uv run python -m poc.demo                 # deterministic, offline; sandbox tier if wasmtime present
uv run python -m poc.demo --no-sandbox    # force every node onto the host tier
uv run python -m poc.demo --live          # real Claude calls (needs: uv sync --group poc)
uv run --group poc pytest tests/test_poc_*.py   # the assertions behind the demo (incl. sandbox)
uv run --group poc python -m poc.sandbox.bench   # component-tier overhead vs the proposal's envelope
```

The offline path uses a deterministic stub model so the security tests are reproducible and
network-free in CI. The `--live` path runs the same graph against a real model, which is what
authentically stress-tests "LLM as trust discharger" — the security properties are structural
and do not depend on the model's quality either way.

## What it demonstrates

**1. Unsafe wiring is rejected at assembly time.** The runtime delegates to the project's
existing `graph_validator` — it does not re-implement type checking. Two unsafe rewirings
(`poc/variants.py`), each rejected for a *different* reason:

| Variant | Rejected by |
|---|---|
| `bypass_pipeline` — wire raw untrusted input straight into the tool-capable node | edge type-compatibility (`Untrusted<RawMessage>` ≠ `ConversationContext`) |
| `launder_trust` — "fix" that by widening the tool-capable node's input type | trust propagation (consumes `Untrusted<_>`, emits clean, never declares `discharges_trust`) |

The second is the one that matters. It type-checks on the edge; only the trust rule catches it.
Trust cannot be laundered by relabelling the consumer.

**2. Capability scoping is enforced by the handle's surface** (`poc/handles.py`). `InferenceLLM`
(`LLMClient<inference>`) has *no tool-calling method at all* — and never even tells the model
tools exist. `ToolLLM` (`LLMClient<[lookup]>`) refuses any tool outside its allowlist.
`ReadDBHandle` has no `write`. Channels and emitters are write-only sinks.

**3. Prompt injection is attenuated, not eliminated.** An adversarial message flows through the
graph; the inference-only nodes can be *influenced* but hold no authority to act, and the
tool-capable node receives a `ConversationContext` — the `Untrusted[RawMessage]` value is
consumed at the parse boundary and never reaches it.

**The residual, stated plainly:** the bounded `question` field survives parsing, so adversarial
text *does* reach the tool-capable node as data. The proposal says exactly this ("a schema that
retains a free-text field … still treats that field as adversarial"). What bounds the damage is
the capability scope, not the absence of the text: blast radius drops from *arbitrary tool
execution* to *a bad lookup query*. `test_free_text_residual_is_real_and_acknowledged` asserts
this limitation on purpose.

## Two enforcement tiers

Every node runs on one of two tiers; the runtime reports which ran each node, so the demo can never
overstate the guarantee in force.

**Host tier (default).** A node is a Python function that receives its capability handles as
arguments. This is *host-discipline* enforcement: it demonstrates the *shape* of confinement, but
nothing stops a malicious Python node from `import os`. The handle surfaces are scoped (§2 above),
but confinement is a convention, not a barrier.

**Sandbox tier (`poc/sandbox/`) — a WASM *component* with a typed capability boundary.** A node body
is compiled to a WebAssembly **component** (Rust → `wasm32-unknown-unknown` → `wasm-tools component
new`) and run under `wasmtime`. Each capability kind is a **typed WIT interface** (`sandbox/wit/caps.wit`):
`LLMClient<inference>` is an interface offering one inference function, `DBHandle<_, read>` an
interface offering `lookup` and no writer, and so on. **A node's `with` clause is exactly the set of
interfaces its component imports.** Here confinement is enforced, not modelled:

- an inference-only node has no tool-calling **import** — the capability is absent, not merely
  unexposed (strictly stronger than the host tier's missing method);
- a component that declares a capability it was not granted **cannot instantiate at all**, and the
  refusal *names the interface* it was denied;
- **there is no ambient authority to reach for at all.** The components import *no* WASI functions —
  not filesystem, socket, environment, or clock. See below; this is the strongest claim here.
- a value that does not match an interface's WIT type is a **boundary error**, not a byte
  reinterpreted as something else.

#### Why `wasm32-unknown-unknown` and not `wasip1`/`wasip2`

This is the load-bearing build choice. An earlier version of this tier compiled nodes to
`wasm32-wasip1` and confined them with an **empty WASI context** (no preopens, no sockets, no env, no
clock). That worked — but the modules still *imported* `fd_write`, `environ_get`, `path_open` and
friends. Those imports were **powerless**, because the host handed them an empty context; they were
nonetheless **present**, so "no ambient authority" was a fact about the *host's configuration*, and a
misconfigured host would have granted them for real.

Building for `wasm32-unknown-unknown` and converting to a component with **no WASI adapter** removes
them. `wasi_imports()` returns `[]`, and the hostile-ambient component imports *nothing whatsoever*.
Confinement became a property of **the artifact** rather than of how it happens to be run. (A
`wasm32-wasip2` build would reintroduce the problem in new clothes: std would link `wasi:cli/*` and
`wasi:io/*` into the import set.)

#### The boundary cannot drift from the graph

`sandbox/interfaces.py` **derives** each node's expected interface set from its `with` clause in
`graphs/customer-support.json`, parsing the capability types with the project's own `type_parser`.
The test suite compares that against what the built component actually imports. A world that grants a
node an interface its signature never asked for is a **test failure**, not a quiet over-grant.

The typed boundary also absorbed two checks the flat-ABI node bodies had to perform by hand. `intent`
is a WIT `enum`, so a node **cannot** return an intent outside the closed set — the old body needed a
membership check to promise that; now the widening is not representable. And the model's reply is a
WIT `variant` (`text` | `call`), so a malformed reply has no encoding.

The two tiers **compose in one graph**: the security-critical nodes (`ParseMessage`,
`GenerateResponse`) run as confined components while the rest run on the host tier — the proposal's
incremental-migration path (opaque host node → confined node). `ParseMessage` is *regenerated in
Rust* from the same signature and contract as the Python version (`sandbox/rust/node_parse_message/`,
prompt in `generated/parse_message.wasm.prompt.md`): same contract, new language, unchanged graph.

### The hostile-node suite is the deliverable

`tests/test_poc_sandbox.py` writes the attacks first. Each escape attempt is asserted **twice**: it
*succeeds* on the host tier (the gap, recorded as a test rather than as prose) and *fails* on the
component tier. A sandbox that passed because nobody wrote the attacks would be worth nothing. The
rule for the port to the component model was that it must not regress: every escape denied by the
old flat-ABI tier is still denied.

### Building the artifacts

The compiled `.wasm` components are committed under `poc/sandbox/wasm/`, so the tests run without a
Rust or component toolchain. To rebuild them: `rustup target add wasm32-unknown-unknown`, install
`wasm-tools` (`brew install wasm-tools` or `cargo install wasm-tools`), then `make wasm`. Without
`wasmtime` installed (`uv sync --group poc`), the sandbox tests skip and the demo falls back to the
host tier, both with a clear message.

## Enforcement fidelity — read before quoting this

The component tier makes capability confinement **unforgeable at the WASM boundary** for the nodes
ported to it: an escape needs a `wasmtime` defect, not just a misbehaving node. It does **not**
provide memory-level unforgeability (a sandbox escape via a runtime bug is out of scope; that is
CHERI's job, a Phase 3 follow-up), and host-tier nodes remain host-discipline only.

Typing the boundary also does **not** close the free-text residual above. It stops ambient-authority
escapes and marshalling ambiguity; it does nothing about adversarial data in a *permitted* field. The
bounded `question` still reaches the tool-capable node, and what limits the blast radius is the
capability scope, not the type of the boundary. `test_free_text_residual_survives_into_the_confined_tool_node`
asserts this on purpose, on the confined tier, so the stronger enforcement cannot be quietly read as
a stronger claim than it is.

One more caveat, on the numbers. `bench.py`'s figures were re-measured for this tier, and its timing
loop was fixed at the same time (it now warms and takes the best of several rounds; it used to time a
single cold pass, which charged JIT warm-up to whichever measurement ran first and — since the
per-crossing cost is a *difference* of two timings — could distort it by an order of magnitude). So
the absolute numbers are **not** directly comparable to those previously reported for the flat-ABI
tier. The claim they support is narrower and is the one that matters: typing the boundary did not
move the per-crossing cost out of its order of magnitude (still tens of µs, well inside the
proposal's <1ms envelope) even though every crossing now lifts and lowers typed values.

## Layout

| File | Role |
|---|---|
| `graph.py` | Load graph JSON; gate assembly through the validator; provision handles; pick per-node tier |
| `handles.py` | Capability handles — the runtime form of the proposal's `with` clauses |
| `values.py` | Domain types flowing along the graph, incl. the `Untrusted[T]` trust marker |
| `nodes.py` | Host-tier node implementations, registered by graph node name |
| `generated/` | **AI-generated** `ParseMessage` (Python + Rust/WASM) and the prompts used to generate them |
| `runtime.py` | The executor: propagate a signal, route sum-typed outputs by variant, record tiers |
| `llm.py` | `StubLLM` (offline, deterministic) and `AnthropicBackend` (real Claude) |
| `variants.py` | Unsafe rewirings that exist to be rejected |
| `sandbox/` | The WASM component tier: `wit/caps.wit` (**the typed capability boundary**), `interfaces.py` (capability→interface mapping, derived from the graph), `host.py` (wasmtime component host), `nodes.py` (adapters), `bench.py` (overhead), `rust/` (node + hostile component sources), `wasm/` (committed artifacts) |
| `demo.py` | The demonstration |

`generated/parse_message.py` is the "code as compiled artifact" property made concrete: the node
was generated from its signature + contract alone (see `parse_message.prompt.md`), with no
visibility into adjacent nodes' implementations. Its Rust/WASM twin
(`sandbox/rust/node_parse_message/`) is the same property across a language boundary.
