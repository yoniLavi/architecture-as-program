# Resource budgets as capability scopes

> **Status: proposed, not approved.** It was written on 18 November 2026, after the author
> accepted spike S1's recommendation (`explore-specified-architecture`, archived).
> Nothing is implemented before task 0.1.

## Why

A capability today bounds *what* a node may do: its kind and its scope. It does not bound
*how much*.
- A granted `LLMClient` can be called without limit.
- A confined body can spin forever.
- The only counter that exists, `uses`, raises `CapabilityError("…spent")`, which reads
  as a security fault rather than a spent budget.

S1 (`spikes/specified-architecture/s1/`, 27 tests, `RESULT.md`) showed the pieces work on
this runtime:
- **Calls and tokens** can be metered at the model backend, beneath the parent's meter,
  as hierarchical KeyKOS-style meters.
- **Fuel** stops a runaway guest deterministically. It overshoots by one check interval,
  and its crossing cost (18–26 µs on all four engines) sits inside the crossing band.
- **An epoch deadline** is a backstop.
- **A store memory limit** holds, but wasmtime-py cannot tell its refusal from a guest
  panic.

S1 also found that budgets are *spent*, not narrowed like sets (design D5 of the spike).
A child's budget must draw on its parent's meter, not copy it.

## What Changes

- **Budget scopes on handle kinds** (grammar as S1 settled):
  - `LLMClient<inference, Calls<'5'>>`, and `Tokens<'N'>`;
  - `HTTPClient<[...], Requests<'N'>>`;
  - `StateHandle<'name', read-write, Bytes<'N'>>`.

  These are trailing scope arguments, which `type_parser` already parses. Assignability:
  a smaller budget is assignable to a larger one.
- **Meters shared down the routing chain.** A child's meter draws on its parent's.
  - The meter sits on the backend, because confined adapters call `backend.generate`
    directly.
  - Exhaustion raises `BudgetExhausted`, which is **not** a `CapabilityError`.
  - The shipped `uses` counter is reclassified the same way.
- **Store budgets on confined nodes.** A node-level `budget` annotation sets fuel, memory
  and a deadline, on the runtime's engine (`engine_config()` gains fuel and epoch
  interruption). A fuel figure is always stated with its one-interval overshoot.
- **Failure classes stay apart.** A budget refusal, a resource failure, an incomplete
  host binding and an ungranted import are four different errors. Where wasmtime cannot
  separate a memory-limit refusal from a guest panic, the error says it is ambiguous.
- **Not in scope:** totals across a graph (a later validator analysis). A token bound
  proved from a call count waits on a per-call output cap (S4's finding), which is named
  here and not built.

## Impact

- **Code:** `scripts/type_parser.py` (assignability for budget arguments),
  `poc/handles.py`, `poc/llm.py`, `poc/sandbox/host.py` (`engine_config`), `poc/attenuate.py`.
- **Paper 2's figures must not move.** `engine_config()` changes the engine the crossing
  benchmark builds, so the crossing band is re-measured. A move outside the band is a
  finding for the author, not a re-seed.
- **New capability:** `resource-budgets`.
- **End condition:** the tasks are done, `make build` is green, two verifying subagents
  have reported, and the change is archived.
