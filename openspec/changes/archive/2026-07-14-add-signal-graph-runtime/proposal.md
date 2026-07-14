# Change: Executable signal-graph runtime (security vertical)

## Why
The proposal's static toolchain (parser + validator) proves the *graph-level* layer of Phase 1,
but every claim that depends on **execution** is unproven: that capabilities are genuinely
injected (no ambient authority), that capability scoping confines a node's effects, and — the
headline, most-contestable claim — that prompt injection is structurally attenuated because no
well-typed wiring connects untrusted input to a tool-capable LLM. Building a runnable slice both
demonstrates these claims and stress-tests them, feeding any roadblocks back into the proposal
(Technical Note A).

## What Changes
- Add a Python **signal-graph runtime** (`poc/`) that loads a canonical graph JSON, instantiates
  each node with **injected capability handles**, and propagates signals along the active path.
- Add **capability handle** objects whose surface enforces scope: `LLMClient<inference>` exposes
  no tool-calling; `LLMClient<[lookup]>` exposes only `lookup`; `DBHandle<scope, read>` is
  read-only; `ResponseChannel` / `EventEmitter` are write-only sinks.
- Enforce **no ambient authority at the host tier**: a node receives only its declared handles and
  has no other mechanism to reach external authority (host-discipline enforcement; the WASM/WASI
  sandbox tier that makes this *unforgeable* is a later change, explicitly out of scope here).
- Reuse the existing validator to **reject unsafe graph variants at assembly time**: a graph that
  wires raw/`Untrusted<_>` user input directly into the tool-capable LLM node fails to assemble.
- Run the **customer-support security vertical** end-to-end (ReceiveMessage → ParseMessage →
  ModerateContent → FetchContext → GenerateResponse → SendReply), with **hybrid** LLM execution:
  real Anthropic calls for the adversarial demonstration, recorded fixtures elsewhere.
- Add a **prompt-injection demonstration** as an executable artifact + test: an adversarial message
  cannot trigger tool actions through the inference-only nodes, and the tool-capable node never
  receives raw user text.
- Isolate runtime dependencies (Anthropic SDK) in an **optional dependency group**; the proposal
  toolchain stays stdlib-only and its build is unaffected.

## Impact
- Affected specs: `signal-graph-runtime` (new capability).
- Affected code: new `poc/` package; `pyproject.toml` (new optional dependency group + test paths).
  No changes to `proposal.typ`, `graphs/*.json`, or the existing `scripts/` validator/parser.
- Proposal feedback: findings from the build are recorded against Technical Note A items
  (node-local state, capability routing, replay fidelity, strength of LLM trust discharge) in a
  follow-up proposal-edit change.
