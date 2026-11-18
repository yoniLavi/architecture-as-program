# S1 result: budgets as capability scopes

*Task 3.1–3.2 of `explore-specified-architecture`, 18 November 2026. Spike code in this
directory; nothing in `poc/`, `scripts/`, `graphs/` or any WIT file changed. Checks:
`uv run --group poc pytest spikes/specified-architecture/s1` (27 pass). Figures:
`results.json`, from `measure.py`.*

## What was built

- **`budget.py`** — budgets as trailing scope arguments the existing parser already
  accepts (`LLMClient<inference, Calls<'5'>>`, `HTTPClient<[...], Requests<'50'>>`,
  `StateHandle<'n', read-write, Bytes<'…'>>`); a narrowing rule layered on
  `type_parser.is_assignable`, unchanged; hierarchical `Meter`s; `MeteredBackend`;
  `BudgetExhausted`.
- **`metered_sandbox.py`** — `MeteredSandbox`, the runtime's `Sandbox` on its own engine
  with fuel and epoch interruption, plus a `StoreBudget` (fuel, memory, deadline) and the
  classification of each store bound; `metered_tier` runs the runtime's own confined
  adapters under a budget.
- **`rust/spin`** — a capability-free guest that burns CPU or memory on request
  (`wasm/spin.wasm`, built outside `make wasm`).

## What it shows

1. **Narrowing comes free, and is not enough.** A budget scope narrows exactly as a set
   scope does (8 narrowing cases pass, including a tool set and an allowlist narrowing
   together with their budgets). But a budget is spent: two children each declaring
   `Calls<'5'>` under a parent's `Calls<'5'>` both pass narrowing. **Metering** closes it:
   each routed handle gets a meter beneath its parent's (KeyKOS's shape), a charge is
   checked against the whole chain before it lands, and the test shows the second child
   refused at the *parent's* meter on the parent's sixth call, with nothing charged by
   the refusal. **Totals** (a static bound over the graph) remain a separate analysis
   that narrowing does not provide (design D5).
2. **The meter must sit on the backend, not the handle.** The confined adapters call
   `llm.backend.generate` directly; a meter on the handle's methods would be bypassed on
   the very tier that enforces. Tested through the runtime's `generate_response_sandbox`.
3. **`Calls` is exact; `Tokens` overrun by at most one call.** Tokens are known only after
   a call, and no backend here takes a per-call output cap, so the enforceable bound is
   "no call starts once the budget is spent" (shown: a 25-token budget ends at 30, the
   overrun recorded). A `Tokens` budget over a backend that reports no usage is refused at
   construction rather than silently unenforced. This is the same shape as
   `ClaudeCLIBackend.ceiling`, which checks before a call and learns usage after it.
4. **Exhaustion is its own event.** `BudgetExhausted` is not a `CapabilityError`; fuel
   too small even to instantiate is a budget, not an ungranted import; and an ungranted
   import on the metered engine is still classed as one. **But shipped code already
   conflates them:** value-bound grants' `uses` counter raises
   `CapabilityError("the bound grant is spent")` (`poc/attenuate.py`). A change that
   adopts budgets should move that to the budget class.
5. **Fuel is a good budget.** Deterministic (identical fuel for identical input, five runs;
   23 units per loop iteration of the spin guest, 4,574 per tool-round invocation of
   `GenerateResponse`, 16,386 to instantiate it). A runaway guest is stopped and classed
   `Fuel`. **The bound has slack:** wasmtime checks fuel at loop headers and function
   entries, so a run is stopped within one check interval past its budget, measured at 23
   units for the loop (a test bounds it at 64). The 86 units for `ParseMessage` (of
   43,588) was seen in a manual bisection and is in no record or test. Small,
   deterministic, and to be stated with any fuel figure.
6. **The deadline works, and is a backstop.** An epoch ticker (1 ms) stops a runaway guest
   (`Deadline`). It can only fire late, never early, but it counts time the guest was
   descheduled, so on a loaded machine it cuts work off earlier than fuel would. Use fuel
   as the budget and the deadline as a generous backstop.
7. **The memory limit holds, and its refusal is ambiguous.** `set_limits(memory_size=…)`
   bounds the guest (1 MiB under a 4 MiB limit succeeds, 16 MiB does not), but the refusal
   surfaces as `unreachable`: a Rust guest built with `panic = "abort"` traps the same way
   on a panic and on a failed allocation, and wasmtime-py 46.0.1 exposes neither
   `trap_on_grow_failure` nor a resource-limiter callback. The spike reports it as
   `GuestTrapped` (ambiguous), never as a budget or a capability. A Rust host, or a future
   binding, would make it exact.
8. **Cost: within noise.** Best-of CPU time, configurations interleaved (load average
   7–24 during the run):

   | engine | crossing (µs) | GenerateResponse call (µs) | burn(200k) vs plain |
   |---|---|---|---|
   | plain | 21.5 | 77.5 | 1.00 |
   | fuel | 25.9 | 77.8 | 1.04 |
   | epoch | 18.2 | 78.8 | 1.03 |
   | fuel+epoch | 23.6 | 78.4 | 0.99 |

   Every configuration's crossing sits inside the 5–100 µs band, and neither mechanism
   moves guest compute by more than this machine's noise (the fuel+epoch row is *faster*
   than plain). The claim supported is "no measurable cost at this resolution", not a
   figure for it.

## What it does not show

- **Totals.** No static bound over a graph was computed: sum along paths, maximum over
  exclusive branches, multiplication under `each`. `each` needs a bound on list length.
  The feed graph's `SelectItems` ensures `len(entries) <= 12`, which is exactly such a
  bound, so S2's contract reasoning could feed totals. That link is worth a follow-up.
- **The host tier.** CPU, memory and time are not bounded there against a hostile body;
  handle-reached budgets are host discipline, as every scope is.
- **Storage and network budgets** were parsed and narrowed but not metered: `Bytes` and
  `Requests` need the same backend-level meter in `StateHandle` and `HTTPClient`, and a
  redirect hop must count as a request.

## Recommendation: propose a change

Propose **`add-resource-budgets`**:

- **Grammar.** Trailing budget scopes on handle types, with narrowing in
  `type_parser.is_assignable` (the D5 rule above), and a `budget` annotation on a node for
  fuel and a deadline.
- **Run time.**
  - Meters live in the handle's backend and are shared down the routing chain.
  - Fuel and epoch interruption are enabled on the runtime engine.
  - A deadline is a backstop only.
- **Classification.**
  - `BudgetExhausted` as its own class, with the `uses` counter moved onto it.
  - Memory is left ambiguous and stated as such.
- **Totals** are a validator analysis in a second step, fed by contract bounds such as
  `len(entries) <= 12`.
- **Before turning fuel on in the shared engine,** re-run Paper 2's crossing measurement.
  It is a measurement key, not a pinned one, but the shared engine is the tier Paper 2
  measured, and the change should say so.
