# Change: Unforgeable node confinement via a WASM/WASI sandbox

## Why
The runtime PoC demonstrates the *shape* of capability confinement but not its *enforcement*. A node
currently receives only its declared handles by **host-level discipline** — nothing stops a node
implementation from simply reaching around the object model (`import os`, open a socket, read the
filesystem). Every security claim in the proposal ultimately rests on "no ambient authority" being a
property of the runtime rather than a convention, and that is precisely the property we have not yet
shown.

This change closes the gap the previous one deliberately left open. It is the single most load-bearing
piece of unfinished evidence in the PoC: until a **hostile** node — one actively trying to escape —
provably cannot exceed its injected capabilities, the proposal's "security by construction" claim is
asserted rather than demonstrated.

## What Changes
- Add a **capability-restricted execution tier**: node bodies compiled to WebAssembly and executed
  under `wasmtime` with **no WASI preopens, no filesystem, no network, no clock, no environment** —
  the module's *only* imports are the host functions that implement its declared capability handles.
- Add a **hostile-node test suite**: node implementations that deliberately attempt filesystem
  access, network egress, ambient environment reads, and calling a capability they were not granted.
  Under the host tier these attempts **succeed** (the gap, asserted as such); under the sandbox tier
  they **must fail**. This is the falsifiable core of the change.
- Make the enforcement tier an explicit, inspectable property of a run (`host` vs `sandbox`), so the
  demo and the tests can never overstate which guarantee is in force.
- Port at least the two security-critical nodes (`ParseMessage`, `GenerateResponse`) to the sandbox
  tier, keeping the rest on the host tier — demonstrating that the two tiers **compose** within one
  graph, which is also the proposal's incremental-migration story (opaque node → confined node).
- Measure and report per-node overhead (instantiation + capability-boundary crossing), giving the
  first real numbers against the performance envelope asserted in @sec:performance.
- **BREAKING (spec-level):** the "fidelity is disclosed" scenario changes — the runtime no longer
  reports host-discipline as the *only* available enforcement.

## Impact
- Affected specs: `signal-graph-runtime` (MODIFIED: prompt-injection fidelity; ADDED: sandbox
  enforcement, hostile-node resistance, tier composition, overhead measurement).
- Affected code: new `poc/sandbox/` (wasmtime host, capability import shims, WIT/host-function
  definitions); `poc/graph.py` (tier selection at assembly); `poc/demo.py` (report the active tier);
  new node sources compiled to `wasm32-wasip1`; `pyproject.toml` (`wasmtime` in the `poc` group);
  build wiring for the WASM artifacts.
- Proposal feedback: real overhead numbers land in @sec:performance (currently an unmeasured
  "working envelope"); any escape or gap found lands in Technical Note A. If the sandbox tier turns
  out to cost more than the envelope allows, that is a finding worth publishing, not hiding.
- Not in scope: CHERI, the component model's full typed-interface story, snapshot/replay of
  in-flight nodes, and multi-language node bodies. Each is noted as a follow-up.
