## Context

Four items, each tied to a §5 verdict or a recorded gap. The engineering is modest but touches the runtime's two most delicate seams: the sub-graph executor (which deliberately holds no backend) and the cross-graph validator (which deliberately stays stdlib-only).

## Goals / Non-Goals

- Goals: move the three §5 verdicts named in the proposal; close the two recorded gaps (cross-tier composition, output-side alias check).
- Non-Goals: anything in §5.3 (soundness, contracts, CHERI, replay, user-level authorisation); multi-terminal aggregation (stays open and refused loudly); a real alias *mechanism* in the type grammar — the check is structural comparison, and the paper must say so.

## Decisions

- **Alias check is structural, not nominal.** The language still has no alias mechanism; the validator compares the sub-graph node's declared output against the union of the child's terminal types structurally. The paper reports "the output side is now checked", not "aliases exist". The grammar is untouched.
- **Cross-tier composition reuses per-node tier resolution.** The child graph's nodes resolve to tiers exactly as in a top-level run; the sub-graph executor stays backend-free. No new mechanism — which, if it works, is itself the paper-relevant observation (same shape as the §5.1 "no mechanism by which it could fail" result).
- **Regeneration targets a capability-holding node.** `FetchContext` (database read) is the primary target; `SendReply` is stretch because identity routing across the WIT boundary is the interesting hard case. One is required, two is better.
- **Host-tier fallbacks stay registered** so the host-vs-confined comparison in the evaluation artifact remains runnable — the two-tier contrast is load-bearing in §4.

## Risks / Trade-offs

- More committed `.wasm` artifacts grow the repo and the `make wasm` maintenance surface → accepted; committed artifacts are what keep tests toolchain-free.
- The output-side check could reject a wiring the runtime currently accepts → run the full corpus before pinning; any newly-rejected canonical case is a finding to report, not to paper over.
- Verdict upgrades in §5 are the hedging danger zone → 5.2's task text requires restrictions to be stated in the same sentence as each upgrade.

## Open Questions

- Whether `GenerateResponse`'s confined variant counts toward "majority" in the live-model configuration (the `--live` path may stay host-tier); if so, the majority claim is stated for the default configuration and says so.
