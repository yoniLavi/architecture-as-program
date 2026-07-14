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
uv run python -m poc.demo           # deterministic, offline, no network
uv run python -m poc.demo --live    # real Claude calls (needs: uv sync --group poc)
uv run pytest tests/test_poc_*.py   # the assertions behind the demo
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

## Enforcement fidelity — read before quoting this

Capability confinement here is **host-discipline enforcement**: a node receives only the handles
its signature declares, and each handle's surface is scoped to its declared authority. That
demonstrates the *shape* of the guarantee. It does **not** make it unforgeable — nothing here
stops a malicious node from `import os`. Memory-level unforgeability needs the WASM/WASI sandbox
tier, and ultimately CHERI. Both are named follow-ups, not claims this PoC makes.

## Layout

| File | Role |
|---|---|
| `graph.py` | Load graph JSON; gate assembly through the validator; provision handles |
| `handles.py` | Capability handles — the runtime form of the proposal's `with` clauses |
| `values.py` | Domain types flowing along the graph, incl. the `Untrusted[T]` trust marker |
| `nodes.py` | Node implementations, registered by graph node name |
| `generated/` | **AI-generated** node (`ParseMessage`) + the prompt used to generate it |
| `runtime.py` | The executor: propagate a signal, route sum-typed outputs by variant |
| `llm.py` | `StubLLM` (offline, deterministic) and `AnthropicBackend` (real Claude) |
| `variants.py` | Unsafe rewirings that exist to be rejected |
| `demo.py` | The demonstration |

`generated/parse_message.py` is the "code as compiled artifact" property made concrete: the node
was generated from its signature + contract alone (see `parse_message.prompt.md`), with no
visibility into adjacent nodes' implementations, and it is the copy that actually runs.
