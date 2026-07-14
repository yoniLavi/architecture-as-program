## 1. Write the attacks first
- [ ] 1.1 Define the hostile-node suite: read a file, open a socket, read an env var, call an
      unlinked host function, call `lookup` from an inference-only node
- [ ] 1.2 Implement the hostile nodes on the **host tier** and assert their escapes **succeed** —
      the known gap, recorded as a test rather than as prose
- [ ] 1.3 Mark the sandbox-tier equivalents as expected-to-fail until the tier exists (xfail),
      so the suite is red for the right reason before any sandbox code is written

## 2. Sandbox tier
- [ ] 2.1 Add `wasmtime` to the `poc` dependency group; keep `scripts/` stdlib-only and keep
      `make build` / pre-commit working without a Rust toolchain
- [ ] 2.2 Wasmtime host: instantiate a module with an **empty** WASI context — no preopens, no
      sockets, no env, no clock
- [ ] 2.3 Capability host functions: one import per handle operation (inference, tool call, DB read,
      channel send, event emit), linked in **only** when the node's signature declares it
- [ ] 2.4 Marshalling across the boundary for the vertical's value types (keep it dumb: JSON in
      linear memory is fine; note the serialisation cost for the benchmark)

## 3. Node bodies in Rust → wasm32-wasip1
- [ ] 3.1 `ParseMessage` — **regenerate** from the same signature + contract, in Rust. Commit the
      prompt alongside it. Same contract, new language, unchanged graph: "code as compiled artifact"
      demonstrated rather than asserted
- [ ] 3.2 `GenerateResponse` — the tool-capable node; its module links the `lookup` import and the
      read-only DB import, and nothing else
- [ ] 3.3 `make wasm` build step; decide and record the artifact policy (see design open question)

## 4. Tier composition
- [ ] 4.1 `Node` gains a tier (`host` | `sandbox`); tier is chosen at assembly, per node
- [ ] 4.2 Executor runs either tier transparently; `ExecutionResult` records the tier per node
- [ ] 4.3 Test: mixed-tier customer-support graph completes the vertical and reports per-node tiers

## 5. Close the loop on the attacks
- [ ] 5.1 Flip the sandbox-tier hostile-node tests from xfail to passing — every escape denied
- [ ] 5.2 Assert the inference-only node has **no tool import at all** (absence of capability, not
      merely absence of a method)
- [ ] 5.3 Update `poc/demo.py` to report the enforcement tier per node, and to keep disclosing the
      free-text residual (which the sandbox does **not** close)

## 6. Measure
- [ ] 6.1 Benchmark module instantiation and per-capability-crossing cost
- [ ] 6.2 Compare against the proposal's asserted envelope (per-crossing < ~1ms; <10% overhead at
      ~10ms of useful work per node) and report the result **whichever way it falls**

## 7. Wrap-up
- [ ] 7.1 Update `poc/README.md` and `AGENTS.md`: what each tier does and does not enforce
- [ ] 7.2 Fold findings into the proposal — real numbers into @sec:performance (currently an
      unmeasured envelope); any escape, gap, or surprise into Technical Note A
- [ ] 7.3 Full gate green: ruff, pytest, `make build`

## Notes for whoever picks this up
- The sandbox is not the deliverable; **the hostile-node suite is**. A sandbox that passes because
  nobody wrote the attacks is worth nothing. Task 1 comes first for that reason.
- Watch the capability-identity question from the last change (handles are currently shared per
  capability *type*). Each WASM instance needs its own import table, so per-node handle identity may
  fall out naturally — if it does, that resolves an open item in Technical Note A for free.
- Resist scope creep into the Component Model / WIT. It is the right long-term answer and the wrong
  thing to do first; see `design.md`.
