## 1. Write the attacks first
- [x] 1.1 Define the hostile-node suite: read a file, open a socket, read an env var, call an
      unlinked host function, call `lookup` from an inference-only node
- [x] 1.2 Implement the hostile nodes on the **host tier** and assert their escapes **succeed** —
      the known gap, recorded as a test rather than as prose
- [x] 1.3 Suite is red for the right reason before green: the ambient escapes and the ungranted
      capability distinguish the tiers, and sandbox-tier tests skip cleanly when the tier is absent
      (the intended xfail-then-pass sequencing, achieved via the tier distinction)

## 2. Sandbox tier
- [x] 2.1 Add `wasmtime` to the `poc` dependency group; keep `scripts/` stdlib-only and keep
      `make build` / pre-commit working without a Rust toolchain (committed `.wasm` artifacts)
- [x] 2.2 Wasmtime host: instantiate a module with an **empty** WASI context — no preopens, no
      sockets, no env, no clock (`poc/sandbox/host.py`)
- [x] 2.3 Capability host functions: one import per handle operation (inference, generate, DB read),
      linked in **only** when the node's signature declares it
- [x] 2.4 Marshalling across the boundary: flat, framed bytes in linear memory (FS/RS separators),
      addressed by a packed `(ptr, len)` i64; serialisation cost noted in the benchmark

## 3. Node bodies in Rust → wasm32-wasip1
- [x] 3.1 `ParseMessage` — **regenerated** from the same signature + contract, in Rust. Prompt
      committed at `poc/generated/parse_message.wasm.prompt.md`. Same contract, new language,
      unchanged graph: "code as compiled artifact" demonstrated rather than asserted
- [x] 3.2 `GenerateResponse` — the tool-capable node; its module links the `cap_generate` and
      read-only `cap_kb_lookup` imports and nothing else (a tool outside `{lookup}` has no import)
- [x] 3.3 `make wasm` build step; artifact policy recorded: `.wasm` committed under
      `poc/sandbox/wasm/`, `poc/sandbox/rust/target/` gitignored (tests run without Rust)

## 4. Tier composition
- [x] 4.1 `Node` gains a tier (`host` | `sandbox`); tier is chosen at assembly, per node
      (`assemble(..., sandbox={...})`)
- [x] 4.2 Executor runs either tier transparently; `ExecutionResult.tiers` records the tier per node
- [x] 4.3 Test: mixed-tier customer-support graph completes the vertical and reports per-node tiers,
      with host/sandbox parity on the terminal outcome

## 5. Close the loop on the attacks
- [x] 5.1 Sandbox-tier hostile-node tests pass — every ambient escape denied, ungranted capability
      cannot instantiate
- [x] 5.2 Assert the inference-only node has **no tool import at all** (absence of capability in the
      import table, not merely absence of a method)
- [x] 5.3 `poc/demo.py` reports the enforcement tier per node and keeps disclosing the free-text
      residual (which the sandbox does **not** close); `--no-sandbox` forces the host tier

## 6. Measure
- [x] 6.1 Benchmark module compilation, per-node instantiation, and per-capability-crossing cost
      (`poc/sandbox/bench.py`)
- [x] 6.2 Compare against the proposal's envelope (per-crossing < ~1ms) and report the result:
      crossing ≈ tens of µs (well within envelope); instantiation ≈ a few hundred µs; compilation a
      one-time ≈ tens of ms

## 7. Wrap-up
- [x] 7.1 Update `poc/README.md` and `AGENTS.md`: what each tier does and does not enforce
- [x] 7.2 Fold findings into the proposal — real numbers into @sec:performance; the sandbox tier and
      hostile-node suite into @sec:phase1; the per-instance import-table result into Technical Note A
      (hierarchical capability routing)
- [x] 7.3 Full gate green: ruff, pytest (102 tests + 11 subtests), `make build`

## Notes for whoever picks this up
- The sandbox is not the deliverable; **the hostile-node suite is**. A sandbox that passes because
  nobody wrote the attacks is worth nothing. Task 1 comes first for that reason.
- Watch the capability-identity question from the last change (handles are currently shared per
  capability *type*). Each WASM instance has its own import table, so per-node handle *binding* is
  already per-instance even when the underlying handle object is shared — this narrows the Technical
  Note A item rather than closing it (provisioning still collapses identity by type).
- Resist scope creep into the Component Model / WIT. It is the right long-term answer and the wrong
  thing to do first; see `design.md`.

## Follow-ups surfaced by this change (not in scope here)
- **Honest nuance on "no ambient authority":** a `wasm32-wasip1` module still *imports* WASI stubs
  (`environ_get`, `fd_write`, …); they are powerless under the empty context, but confinement is
  enforced by that empty context, not by the absence of the imports. A `wasm32-unknown-unknown` or
  Component Model target would remove even the stubs. Worth a follow-up.
- **Instance pooling:** instantiation (~a few hundred µs) dominates the per-node sandbox cost;
  pooling warm instances would amortise it. Not needed for the PoC.
- **CHERI / memory-level unforgeability** remains Phase 3, as does the Component Model + WIT typed
  boundary.
