# Change: Strengthen the evidence behind Paper 2's partial and unattempted claims

## Why

Paper 2's §5 (predictions and outcomes) currently records three verdicts that modest engineering can move: cross-language interchangeability rests on a single regenerated node ("an existence proof, not a claim about the general case"), confined-tier enforcement covers only two of the nine `CustomerSupport` nodes, and two bounds are recorded as open gaps — cross-tier sub-graph composition ("not attempted") and the unchecked `ServiceOutcome` union alias (the cross-graph validator never examines the output side, pinned by a test as a real gap). Each item below is tied to the specific §5 verdict or recorded gap it moves; none touches the §5.3 conditionals (soundness, contracts, CHERI, replay), which stay honestly conditional.

## What Changes

- Regenerate at least one *capability-holding* node (e.g. `FetchContext` with its database read handle, or `SendReply` with its identity-routed send handle) in Rust from the same graph signature, moving interchangeability beyond the pure-transformation case.
- Extend confined-tier coverage so a majority of the `CustomerSupport` execution path runs as WASM components, with the runtime continuing to report which tier ran each node.
- Execute a sub-graph across enforcement tiers: a host-tier `SupportPlatform` parent running `CustomerSupport` with confined-tier nodes inside it, with confinement and identity routing holding across the boundary.
- Close the `ServiceOutcome` alias gap: the cross-graph validator checks a sub-graph node's declared output type against the union of the child graph's terminal types, with a mutation-corpus case pinning the new rejection and its reason class.
- Update Paper 2 accordingly: §3 (implementation) facts, §5 verdict upgrades with their restrictions stated, and removal of the closed gaps from §7/§8 (a stated limitation is only cut when the artifact has actually closed it).

## Impact

- Affected specs: `signal-graph-runtime` (four ADDED requirements)
- Affected code: `poc/sandbox/` (new Rust node crates, committed `.wasm` artifacts), `poc/runtime` sub-graph execution, `scripts/graph_validator.py` (cross-graph output check), `poc/evaluate.py` (new pinned corpus cases), `tests/`
- Affected papers: `papers/02-demonstrator/proposal.typ` §3, §5, §7, §8 (Paper 1 untouched — frozen)
- Independent of the other two active changes; can land first.
