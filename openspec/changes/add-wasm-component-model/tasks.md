## 1. WIT interfaces for the capability kinds
- [ ] 1.1 Author WIT interfaces for the five capability kinds the vertical uses (inference LLM,
      tool-scoped LLM, read-only DB, response channel, event emitter); decide the world layout
- [ ] 1.2 Generate the capability→interface mapping from the graph JSON so the boundary cannot drift
      from the node signatures

## 2. Component-model host
- [ ] 2.1 Add the component-model tooling to the `poc` group; keep `scripts/` stdlib-only and keep
      `make build` / pre-commit working without a Rust or component toolchain
- [ ] 2.2 Implement a component host that instantiates a node component and links the typed capability
      interfaces its world imports — and only those
- [ ] 2.3 Assert a component node's import set contains no ambient WASI functions (the strengthened
      "no ambient authority")

## 3. Node bodies as components
- [ ] 3.1 Recompile `ParseMessage` as a component importing the typed inference interface
- [ ] 3.2 Recompile `GenerateResponse` as a component importing the typed LLM (lookup-only) and
      read-only DB interfaces, running the tool loop over typed WIT calls
- [ ] 3.3 `make wasm` builds components; carry over the committed-artifact policy

## 4. Preserve the guarantees the last change established
- [ ] 4.1 Port the hostile-node suite to the component tier; every escape still denied
- [ ] 4.2 Mixed-tier composition still runs end-to-end with host/component parity on the outcome
- [ ] 4.3 Re-measure overhead on the component tier and compare against the envelope (@sec:performance)

## 5. Wrap-up
- [ ] 5.1 Update `poc/README.md` and `AGENTS.md`: the component tier, what it enforces, how it differs
      from the core-wasm tier
- [ ] 5.2 Fold findings into the proposal: typed boundaries into @sec:sandboxing/@sec:phase1; retire
      the "wasip1 still imports powerless stubs" nuance in Technical Note A
- [ ] 5.3 Full gate green: ruff, pytest, `make build`

## Notes for whoever picks this up
- The confinement result is already established by the core-wasm tier; the value here is the *typed*
  boundary and dropping the WASI stubs, not more confinement. Do not let the port regress the
  hostile-node suite.
- Resist a general resource/handle framework. Model only the five capability kinds the vertical needs.
- Toolchain choices (bindings generator, host API) are open — see `design.md`. Pick the least-friction
  combination that builds reproducibly and can commit artifacts.
