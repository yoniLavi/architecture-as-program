# Change: Typed capability boundaries via the WASM Component Model

## Why
The sandbox tier (`add-wasi-node-sandbox`, archived) confines a node body as a core
`wasm32-wasip1` module under an empty WASI context, with capabilities wired in as ad-hoc host
functions over a hand-rolled flat ABI (framed bytes in linear memory). It works and it is tested,
but it leaves two honest limitations on the table, both recorded as follow-ups by that change:

1. **"No ambient authority" is enforced by the empty context, not the absence of imports.** A
   `wasm32-wasip1` module still *imports* WASI stubs (`environ_get`, `fd_write`, …); they are
   powerless because the context is empty, but they are present in the import table.
2. **The capability boundary is untyped at the WASM level.** Host functions exchange flat framed
   bytes, not typed values. The node's typed signature — the whole point of the signal graph — is
   reconstructed by convention on each side of the boundary rather than enforced at it.

The WASM Component Model with WIT-defined interfaces is the proposal's own stated direction
(@sec:sandboxing, @sec:beam): its typed inter-component interfaces are almost exactly the signal
graph's typed node boundaries. Adopting it turns the runtime boundary into a realisation of the
node's typed signature, and makes "no ambient authority" a property of the component's import set
rather than of a context configured behind powerless stubs.

## What Changes
- Define each capability kind (`LLMClient<inference>`, `LLMClient<[...]>`, `DBHandle<_, read>`,
  `ResponseChannel<_>`, `EventEmitter<_>`) as a **typed WIT interface**. A node's `with` clause
  maps to the set of interfaces its component imports.
- Compile node bodies to **WASM components** (not core modules) and link them through generated,
  typed bindings. Retire the flat `(ptr, len)` ABI and the manual FS/RS framing for the ported
  nodes.
- A capability the node did not declare is not in its imported world, so it cannot be named — and a
  value that does not match an interface's WIT type is a boundary error, not a marshalling accident.
- **A component node imports no ambient WASI functions at all** — the powerless stubs disappear, so
  the absence of authority is visible in the import set.
- Keep the host tier and the core-wasm story available during migration; the component tier is the
  strengthened enforcement path, and the two-tier composition story (@sec:phase2) is preserved.
- **BREAKING (internal):** the sandbox host's flat-ABI contract and the `cap_*` host-function names
  are replaced by WIT-typed interfaces for the ported nodes.

## Impact
- Affected specs: `signal-graph-runtime` (ADDED: typed WIT capability boundaries; a component node
  imports no ambient WASI functions).
- Affected code: `poc/sandbox/` (WIT world/interface definitions, bindings generation, a
  component-model host replacing/augmenting the core-wasm `host.py`); the Rust node crates recompiled
  as components; `Makefile` (`make wasm` targets components); `pyproject.toml` (component-model
  tooling in the `poc` group). The committed-artifact policy carries over.
- Proposal feedback: fold the typed-boundary result into @sec:sandboxing and @sec:phase1, and retire
  the "wasip1 still imports powerless stubs" nuance now noted in Technical Note A.
- Not in scope: CHERI/memory-level enforcement; the full component-model resource-and-handle story
  beyond what the five capability kinds need; multi-language node bodies.

## Notes on what is deliberately left open (design.md)
The exact WIT world layout, the choice of bindings toolchain, and whether the Python host uses
`wasmtime`'s component API directly or a generated binding layer are design decisions to settle at
implementation time, not commitments made here.
