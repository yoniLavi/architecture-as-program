## Context

The inspector is paper-reported evidence on the tooling predictions, not demo polish. That decision drives everything: claims must be tested, framing must be inspector-not-editor, and the corpus build must stay independent of a second toolchain. The repo's invariant — every rendered artifact generated from a checked source — must survive contact with a UI, which is historically where such invariants die.

## Goals / Non-Goals

- Goals: render canonical graphs; trigger real both-tier execution server-side; visualise traces (tiers, taint, crossings, nesting); guided injection walkthrough; evidence strong enough to report.
- Non-Goals: graph *authoring* (the editor prediction stays open in §7); in-browser WASM execution (jco) — no paper-relevant claim, large lift; deployment/hosting infrastructure beyond local run (a hosted demo is a later, outward-facing decision); any UI dependency in the corpus build.

## Decisions

- **The UI is a pure consumer.** It renders `graphs/*.json` served unmodified and traces returned by the runtime. No graph model in TypeScript beyond parsing for display; layout is computed client-side from the JSON. If the UI needs a fact not in the JSON or the trace, the fix is upstream (schema or trace), never a UI-side annotation.
- **Execution server-side via the existing runtime.** A thin HTTP layer in `poc/` (stdlib `http.server` or the smallest viable dependency in the `poc` group — decide at implementation; nothing new in `scripts/`). Same assemble/execute path as the tests; the API adds transport, not semantics. `wasmtime` runs where it already runs.
- **Next.js in `ui/` with its own lockfile**, no workspace coupling to the repo root. `make ui*` targets are opt-in; CI for the UI (if any) is a separate job that cannot fail the paper build.
- **Paper figures regenerate.** Screenshots for §3 come from the e2e run, committed the way other generated figures are handled, so the paper's images cannot drift from the artifact.
- **Testing bar follows report-ability**: each behavior the paper asserts maps to a scenario in the `graph-inspector` spec, covered by a Python contract test (API) or an e2e check (UI). What isn't tested doesn't get claimed.

## Risks / Trade-offs

- Two toolchains in one repo → strict isolation (own lockfile, opt-in targets, build-independence scenario pinned in the spec).
- An HTTP layer over the runtime could acquire semantics (auth, state, mutation) → the API is read-and-run only; anything more is a new proposal.
- The walkthrough could dramatise beyond the evidence (e.g. implying the host tier "blocks" anything) → walkthrough copy review against §4's language is part of task 4.1's checklist.
- Live Claude calls from a UI invite accidental key exposure → `--live` stays CLI-only unless separately proposed; the UI runs the stub model path.

## Open Questions

- Layout engine (React Flow's built-in vs ELK) — decide on rendered quality of the nine-node graph with sub-graph nesting.
- Whether trace payloads are ever shown (upstream open question in `add-execution-trace`; lean remains types + labels only).
