## 1. WIT interfaces for the capability kinds
- [x] 1.1 Author WIT interfaces for the five capability kinds the vertical uses (inference LLM,
      tool-scoped LLM, read-only DB, response channel, event emitter); decide the world layout
- [x] 1.2 Generate the capability→interface mapping from the graph JSON so the boundary cannot drift
      from the node signatures

## 2. Component-model host
- [x] 2.1 Add the component-model tooling to the `poc` group; keep `scripts/` stdlib-only and keep
      `make build` / pre-commit working without a Rust or component toolchain
- [x] 2.2 Implement a component host that instantiates a node component and links the typed capability
      interfaces its world imports — and only those
- [x] 2.3 Assert a component node's import set contains no ambient WASI functions (the strengthened
      "no ambient authority")

## 3. Node bodies as components
- [x] 3.1 Recompile `ParseMessage` as a component importing the typed inference interface
- [x] 3.2 Recompile `GenerateResponse` as a component importing the typed LLM (lookup-only) and
      read-only DB interfaces, running the tool loop over typed WIT calls
- [x] 3.3 `make wasm` builds components; carry over the committed-artifact policy

## 4. Preserve the guarantees the last change established
- [x] 4.1 Port the hostile-node suite to the component tier; every escape still denied
- [x] 4.2 Mixed-tier composition still runs end-to-end with host/component parity on the outcome
- [x] 4.3 Re-measure overhead on the component tier and compare against the envelope (@sec:performance)

## 5. Wrap-up
- [x] 5.1 Update `poc/README.md` and `AGENTS.md`: the component tier, what it enforces, how it differs
      from the core-wasm tier
- [x] 5.2 Fold findings into the proposal: typed boundaries into @sec:sandboxing/@sec:phase1; retire
      the "wasip1 still imports powerless stubs" nuance in Technical Note A
- [x] 5.3 Full gate green: ruff, pytest, `make build`

## Notes for whoever picks this up
- The confinement result is already established by the core-wasm tier; the value here is the *typed*
  boundary and dropping the WASI stubs, not more confinement. Do not let the port regress the
  hostile-node suite.
- Resist a general resource/handle framework. Model only the five capability kinds the vertical needs.
- Toolchain choices (bindings generator, host API) are open — see `design.md`. Pick the least-friction
  combination that builds reproducibly and can commit artifacts.

## Outcomes (filled in on completion)

**Toolchain settled** (the open questions in `design.md`):
- **World layout**: one `world` per node, sharing per-capability `interface`s plus a function-free
  `types` interface for the domain vocabulary. `poc/sandbox/wit/caps.wit`.
- **Bindings**: guest = `wit-bindgen` (the `generate!` macro, no `cargo component` needed); host =
  `wasmtime`'s Python component API directly (`wasmtime.component`, present since wasmtime-py 46) —
  no generated shim was required.
- **Target**: `wasm32-unknown-unknown` + `wasm-tools component new` with **no WASI adapter**. This
  turned out to be load-bearing rather than incidental: a `wasip1` *or* `wasip2` build would link
  std against WASI and put ambient imports back in the import set. This is what makes
  `wasi_imports() == []` true.
- **Value marshalling**: domain types are WIT records with an `intent` **enum** and an `ok`/`error`
  **variant** matching the graph's sum-type role labels. Nothing was left as an opaque string.

**Open question answered.** "Is there a clean way to enumerate a component's imports and assert the
WASI set is empty?" — yes: `Component.type.imports(engine)`. `poc/sandbox/host.py` exposes it as
`component_imports` / `capability_imports` / `wasi_imports`, and the suite asserts the last is `[]`
for every artifact.

**Open question answered.** "Does the typed boundary let us drop the node-side tool loop?" — we kept
it, and the loop got *simpler* rather than merely relocating: the model's reply is now a WIT variant
(`text` | `call`), so the tagged-string parse and its `malformed model reply` arm are gone.

**Correction to 5.2 as written.** There was no "wasip1 still imports powerless stubs" nuance in
Technical Note A to retire — the archived `add-wasi-node-sandbox` change listed it as a follow-up but
never landed it in the proposal. What existed instead was an *overstatement* in @sec:phase1 ("a
module's only imports are the host functions implementing its declared capability handles"), which
was not quite true for wasip1 and is now literally true. @sec:phase1 and @sec:sandboxing were
rewritten to state the wasip1-vs-component distinction explicitly rather than to delete it.

**Benchmark defect found and fixed (not in the original scope).** `bench.py` timed a single cold
pass, so JIT/interpreter warm-up was charged to whichever measurement ran first — and because the
per-crossing cost is a *difference* of two timings, that inflated the reported crossing by roughly an
order of magnitude (a first run of the ported tier reported ~500µs/crossing, which would have read as
"typing the boundary cost 10×"). With warm-up and best-of-rounds, the crossing is ~25µs. Two
consequences recorded in the proposal and both READMEs: the absolute figures are **not** comparable
to those previously published for the flat-ABI tier, and the only claim the data supports is that
typing the boundary did not move the crossing out of its order of magnitude. The crossing measurement
also now differences *one* component driven down a 1-crossing and a 3-crossing path, rather than two
different node bodies, so guest-side work cancels.

**Follow-on proposal edit prompted by review (beyond 5.2).** The finding that a `wasip2` build drags
in ambient WASI imports raised a fair question: is WASI the right thing to build on, given it might be
deprecated? Answered by distinguishing the two layers the word "WASI" conflates. The durable
substrate is the **WASM Component Model / WIT** (the typed-interface layer); **WASI** is a standard
*library* of interfaces built on it. The PoC already bets on the substrate — it defines its own WIT
capability interfaces rather than importing WASI's — so it is untouched by WASI's interface churn.
Grounded in the current roadmap: WASI 0.1 is legacy; 0.2 rebased WASI onto the Component Model; **0.3
(ratified June 2026) removed the `wasi:io` package entirely**, folding it into the Component Model's
canonical ABI; WASI 1.0 is expected late 2026/early 2027. That `wasi:io` removal is a concrete
instance of the point — the interfaces move, the substrate they rebase onto is stable. @sec:sandboxing
was rewritten to state the layering and reframe WASI's own interfaces as a *worked example* of
capability-as-interface (structurally the same as our `DBHandle`/`LLMClient`, for host resources); the
agenda's "WASM/WASI" shorthand was tightened to name the Component Model where the typed boundary is
load-bearing. New citations: `wasi_030_2026`, `wasi_roadmap_2026`.
