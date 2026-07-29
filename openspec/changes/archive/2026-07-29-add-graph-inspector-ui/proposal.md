# Change: Add a graph inspector UI (React/Next.js) reported in Paper 2

## Why

Paper 2's §5 currently records the tooling predictions as "not attempted at all... no evidence in either direction". A web interface that renders the canonical graphs, triggers real (server-side, both-tier) execution, and visualises the resulting traces — trust taint propagating node by node, the confined tier refusing what the host tier permits — is the first artifact built against those predictions, and the decision is to *report* it in the paper, which raises its bar: what the paper claims about it must be tested, and what it is must be framed precisely. It is a visual **inspector**, not the predicted visual **editor** — it views and runs graphs; it does not author them. The verdict can move to partial, never to substantiated.

## What Changes

- New `ui/` directory: a Next.js app rendering `graphs/*.json` directly (no parallel graph representation — the same single-source-of-truth discipline as the generated SVGs).
- A thin server-side execution API wrapping the existing `poc` assemble/execute, returning the structured trace from `add-execution-trace`; the UI is a pure consumer of graphs + traces.
- Trace overlay visualising per-node tier, trust labels, capability crossings with instance names, and sub-graph nesting; a guided prompt-injection scenario showing the `Untrusted` taint path and the host-vs-confined contrast.
- Dependency isolation: the UI's toolchain (Node) is not required by `make build`; nothing from `ui/` leaks into `scripts/` or the `poc` dependency group.
- Paper 2: §3 reports the inspector; §5 moves the visual-editor prediction to partial with the inspector-not-editor restriction stated; §7 records authoring (editing the graph from the UI, with the validator in the loop) as the open next step.

## Impact

- Affected specs: `graph-inspector` (new capability, four ADDED requirements), `paper-corpus` (one ADDED requirement)
- Affected code: new `ui/` (Next.js app), a small execution-API entry point in `poc/`, `Makefile` (optional `ui` targets only), `tests/` (API contract tests on the Python side)
- Affected papers: `papers/02-demonstrator/proposal.typ` §3, §5, §7
- Ordering: depends on `add-execution-trace` (the trace is what the UI renders); independent of `strengthen-claim-evidence`.
