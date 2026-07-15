## Context
On the sandbox tier a node runs as a WASM component whose imports are typed WIT capability interfaces. The
host (`poc/sandbox/nodes.py`) satisfies those imports with closures that call the *same* Python handle
objects the host tier uses (`InferenceLLM`, `ReadDBHandle`, `ToolLLM`). `add-capability-revocation` makes a
revocable instance a `Caretaker` over that handle. So if the closures bridge to the caretaker (not to the
bare handle captured before wrapping), a revoked caretaker's method raises inside the closure, and the
guest's capability crossing fails. The whole change hinges on *which object the closure closes over*.

## Goals / Non-Goals
- **Goals:** a sandboxed node binding a revoked instance fails on its next capability crossing; this is a
  recorded test in the hostile-node suite; no over-claim (the failure is at the WIT boundary, not memory).
- **Non-Goals:** rotation on the sandbox tier; ambient-authority revocation (none exists); CHERI; changing
  the host tier's semantics.

## Decisions
- **Decision: prefer composition over a second mechanism.** First verify that routing the caretaker
  through the existing WIT host functions already yields a raised error on a revoked crossing. If it does,
  the change is a test plus whatever wiring ensures the closures capture the caretaker (via
  `handle_for`/`handles_for`) rather than a pre-wrap handle. A second sever point at the boundary is added
  *only* if composition does not hold — avoiding a redundant enforcement path that could drift from the
  host tier's.
- **Decision: assert in the hostile-node suite, not just a unit test.** The suite's discipline is that
  escapes *succeed* on the host tier (recorded gap) and *fail* on the sandbox tier. A revoked-instance
  crossing is the same shape: it must fail on the confined tier, asserted alongside the filesystem /
  network / env / ungranted-capability escapes.

## Risks / Trade-offs
- **Silent host/guest divergence.** If the sandbox path captured the bare handle at build time, revocation
  would pass on the host tier and *silently* not compose to the sandbox tier — the exact failure this
  change exists to catch. → The test makes divergence loud.
- **Boundary-sever duplication.** Adding a second sever point risks two code paths for one property. →
  Only add it if composition fails; prefer the single caretaker.

## Migration Plan
Additive. Nodes not ported to the sandbox tier are unaffected. If composition already holds, this is
mostly a test; if not, the boundary sever is gated on the same revoked flag, so un-revoked crossings are
unchanged.

## Open Questions
- Does the current `poc/sandbox/nodes.py` bridge close over the instance resolved through `handle_for`
  (which would be the caretaker) or a handle captured earlier? The first `/verify` step answers this and
  decides whether any wiring change is needed at all.
