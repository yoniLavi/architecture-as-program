# The architecture graph as specification: contracts, proofs and budgets

> **Status: approved, 18 November 2026** (task 0.1 records the answers; the Paper 4 gate
> was waived and S1 now leads). Proposed 17 November 2026. This is a future-directions
> change: it records a direction and the spikes that test it.

## Why

So far the graph has been argued as a security policy: the `with` clause sets the import
surface, the trust lattice sets where untrusted data may go, and scopes set what a handle
admits. The author's direction (17 November 2026) is to make the graph also the
**specification**. Each node would carry:
- what it must do (invariants, pre- and postconditions), possibly backed by a proof the
  checker verifies;
- what it may consume (budgets for model cost, CPU, wall-clock time, memory, storage and
  network), enforced at run time and bounded by proof where a bound can be proved.

This could feed more than one paper. The machinery it would build on already exists, as
measured at `9b710ff`:
- **Contracts.** `poc/contracts.py` gives a node `requires`/`ensures` with blame, in a
  closed vocabulary (comparison, set membership, presence, `len`). A contract is checked
  at run time and can be turned into a property-based-test strategy (`strategy`). Its
  docstring calls the ceiling the design: anything richer "would need a solver".
  - Composition along edges (whether A's `ensures` implies B's `requires`) is not checked
    anywhere.
- **Scopes that narrow.** Every capability kind has a scope that narrows at composition:
  - checked at validation, and enforced at the routing point since 16 November 2026
    (`poc/attenuate.py`);
  - a budget written as a scope would inherit both.
- **Usage ceilings.** `ClaudeCLIBackend` (`poc/llm.py`) already refuses calls past a usage
  ceiling (default 0.90 of a window). That is a budget, held in the backend and not in
  the graph.
- **The confined tier.** It runs each node in a fresh wasmtime store with a capped memory
  reservation (`poc/sandbox/host.py`). wasmtime also offers fuel (an instruction count)
  and epoch interruption (a wall-clock deadline), and neither is used yet.
- **Paper 3's gate.** An agent writes a node, and a checker that does not trust the agent
  decides whether to admit it. Proof-carrying code (Necula and Lee, 1996) is the same shape
  with a stronger certificate.

## What Changes

This change records the direction, the decisions it would need, and the spikes. It changes
no code until a spike is approved, and each spike that leads to a capability gets its own
change.

- **A direction note**, `docs/SPECIFIED-ARCHITECTURE.md`, covering the four strands in
  `design.md`:
  - S1, budgets as capability scopes;
  - S2, contracts that compose along edges;
  - S3, proofs of node bodies;
  - S4, proofs of resource bounds.
- **Four spikes, one per strand.** Each is small, time-boxed and calls no model unless the
  author approves it (the generation pilot in S3 is the only candidate). Each ends in a
  written result and a recommendation: propose a change, or stop.
- **A prior-art survey before S3 and S4**, recorded in `docs/PRIOR-ART.md`. It covers:
  - proof-carrying code;
  - Rust verification (Verus, Aeneas into Lean, Kani, Creusot, Prusti);
  - resource-aware type systems (RAML and amortised analysis);
  - KeyKOS/EROS meters and space banks;
  - the current state of agent-written proofs.

  This follows the repo's practice of engaging working systems before choosing a
  direction.

**Not in this change:**
- any edit to a paper: Paper 1 is frozen, Paper 2 v1.1 is set aside, and Paper 4 is not
  pushed toward review;
- any change to the contract vocabulary, the validator, `caps.wit`/`banking.wit`, the
  registered architect, or Paper 3's generation prompt or registration. A spike that
  needs one of these stops and asks;
- any paid spend, or any proof toolchain added to the build. A prover installed for a
  spike lives in its own dependency group and runs in no build step;
- choosing a paper. The author decides after the spikes which results feed which paper.

## Capabilities

### New Capabilities
None yet. Each spike that succeeds proposes its own capability in its own change. This
change declares `skip_specs`.

### Modified Capabilities
None.

## Impact

- **Docs:** `docs/SPECIFIED-ARCHITECTURE.md` (new), `docs/PRIOR-ART.md` (a survey section),
  and `docs/ROADMAP.md` (a pointer).
- **Code:** none in this change. Spike code lives under `spikes/specified-architecture/`,
  outside `poc/` and `scripts/`, and is imported by no build step.
- **Open changes:** this makes three open changes (`add-payee-provenance`, open when this
  was proposed, was archived on 18 November 2026):
  - `add-paper-4`;
  - `operate-feed-triage`;
  - this one.

  The author asked for it. It has an end condition (task 6.1): archive once every spike
  has a written result and the author has decided on each recommendation.
