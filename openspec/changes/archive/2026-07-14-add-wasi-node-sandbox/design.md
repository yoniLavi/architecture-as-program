## Context
The existing runtime enforces capability confinement by host discipline: a node is a Python function
that receives handle objects and is *trusted not to* reach for anything else. That is enough to show
the programming model, and useless as a security argument. The proposal's central claim — a node "has
no mechanism" to exceed its declared authority, "enforced by the absence of any mechanism rather than
a policy guard" (§5.3) — is exactly what a sandbox provides and host discipline does not.

The goal here is narrow and adversarial: make a node that *wants* to escape, and fail to escape it.

## Goals / Non-Goals
- **Goals:** WASM/WASI execution tier with zero ambient authority; a hostile-node suite that
  distinguishes the two tiers; host/sandbox tiers composing in one graph; first real overhead numbers.
- **Non-Goals:** CHERI (Phase 3); full WASM Component Model + WIT typed boundaries (see Decisions);
  snapshot/resume of in-flight nodes (WASI support is immature — the proposal already says so);
  multi-language node bodies; rewriting every node.

## Decisions

- **Decision: `wasmtime` + core `wasm32-wasip1`, not the Component Model — for now.**
  The Component Model is the better long-term fit (its typed inter-component interfaces are almost
  exactly the proposal's typed node boundaries, and §4.9 says so). But it is a much larger lift:
  WIT definitions, bindings generation, and a toolchain that is still moving. For the *security*
  question we need answered — can a hostile node escape? — plain core WASM under wasmtime with an
  empty WASI context is sufficient and far cheaper. Model the capability handles as **explicit host
  function imports**; grant no preopens, no sockets, no env, no clock.
  Component-model/WIT is the natural follow-up and should be scoped once this lands.

- **Decision: node bodies in Rust, compiled to `wasm32-wasip1`.**
  Rust has the least friction to a small, dependency-free WASM module. Python-in-WASM (componentize-py,
  or a WASM-compiled interpreter) is closer to the current node sources but drags in an interpreter,
  which muddies both the overhead numbers and the confinement argument. Note the honest cost: the
  AI-generated `ParseMessage` gets *regenerated* in Rust from the same signature + contract — which is
  itself a nice demonstration of "code as compiled artifact" (same contract, different implementation
  language, unchanged graph), and should be presented that way.

- **Decision: enforcement tier is per-node and explicit.**
  `Node` gains a tier (`host` | `sandbox`). The runtime reports the tier of every node it ran, and
  the demo prints it. Two reasons: (1) it makes it impossible for the demo to overclaim; (2) mixed
  tiers *are* the migration story — an opaque host node alongside a confined sandbox node is exactly
  the "wrap an existing service, then decompose it" path in @sec:phase2.

- **Decision: the hostile-node suite is the deliverable, not the sandbox.**
  Write the attacks first, assert they *succeed* on the host tier (documenting the gap as a test), then
  assert they *fail* on the sandbox tier. Attacks: read a file outside any grant; open a TCP socket;
  read an env var; call a host import the node was not linked with; attempt to call `lookup` from an
  inference-only node. A sandbox that passes because the attacks were never written is worth nothing.

- **Decision: measure, and publish whatever we find.**
  Report module instantiation cost and per-capability-crossing cost. @sec:performance currently asserts
  an unmeasured envelope (per-crossing < ~1ms keeps overhead under ~10% when a node does ~10ms of
  work). If the measured numbers violate that envelope, the proposal changes — that is the point of
  building the thing.

## Risks / Trade-offs
- **The sandbox becomes the demo, and the graph story gets lost.** → Mitigate by keeping the graph,
  the validator, and the vertical exactly as they are; the sandbox swaps out only how a node body runs.
- **Rust node bodies diverge from the Python ones.** → The contract is the interface; both must satisfy
  the same tests. Divergence that the contract does not catch is itself a finding for the
  "contract incompleteness" item in Technical Note A.
- **Toolchain weight** (Rust + wasm target + wasmtime) lands in a repo that has been proudly
  stdlib-only. → Confine it to the `poc` dependency group and a separate build step; `make build` and
  the pre-commit hooks must not require a Rust toolchain. Pre-built `.wasm` artifacts may be committed
  so the tests run without it.

## Migration Plan
Additive. The host tier remains the default; the sandbox tier is opt-in per node. Existing tests keep
passing unchanged. If the WASM build is unavailable, sandbox-tier tests skip with a clear reason
rather than failing.

## Open Questions
- Do we commit the built `.wasm` artifacts (tests run anywhere, but binaries in git), or require the
  Rust toolchain in CI (clean repo, heavier CI)? Leaning: commit them, with a `make wasm` to rebuild.
- Should capability *identity* (not just type) be threaded through now, given the aliasing finding
  from the last change? The sandbox forces the question — each module instance needs its own import
  table, so per-node handle instances may fall out naturally. Worth checking early.
- Does the inference-only guarantee survive the port? In Python it is enforced by the *absence of a
  method*; in WASM it must become the *absence of an import*. That is strictly stronger, and worth
  stating.
