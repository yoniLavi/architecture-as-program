<!-- OPENSPEC:START -->
# OpenSpec Instructions

These instructions are for AI assistants working in this project.

Always open `@/openspec/AGENTS.md` when the request:
- Mentions planning or proposals (words like proposal, spec, change, plan)
- Introduces new capabilities, breaking changes, architecture shifts, or big performance/security work
- Sounds ambiguous and you need the authoritative spec before coding

Use `@/openspec/AGENTS.md` to learn:
- How to create and apply change proposals
- Spec format and conventions
- Project structure and guidelines

Keep this managed block so 'openspec update' can refresh the instructions.

<!-- OPENSPEC:END -->

# Architecture as Program — Notes for all Agents (This AGENTS.md is also symlinked for Claude Code to access as CLAUDE.md)

## What this repo is

A longitudinal research program arguing that AI coding agents + functional reactive programming + object-capability security converge on a new development paradigm: the **signal graph** as simultaneously architecture model, security policy, and source of truth.

It is structured as a **corpus of papers backed by a shared, evolving research artifact** (see `papers/README.md` and `METHODOLOGY.md`):

- **Paper 1 — the founding vision** (`papers/01-vision/`) is **frozen**: it reproduces the repository's state before the executable demonstrator `poc/` existed (dated *June 2026*). It was editorially tidied **once** for its arXiv preprint (July 2026 — typos, phrasing, and publication front matter, **no claim changed**; recorded in `ERRATA.md`) and then **re-frozen at the published-preprint commit**, which is where `scripts/check-freeze.py`'s `FREEZE_REF` now points. It is self-contained (carries its own pinned graph/diagram inputs) and errata-only again — do not edit it; the freeze guard fails the build if it drifts. A further one-time editorial-and-metadata revision for publication is permitted by the `paper-corpus` spec, but only that: no substantive claim may move.
- **Paper 2 — the demonstrator paper** (`papers/02-demonstrator/`) is the **living** document: it builds from the shared root artifact and folds in what the demonstrator has since substantiated. This is the paper you normally edit.

This is primarily a **writing project**: the papers are the outputs that matter. But they are backed by a real, tested toolchain (below), not vapourware.

## Key files

| File | Role |
|---|---|
| `papers/02-demonstrator/proposal.typ` | The living paper's source (Typst). **This is the document you normally edit.** |
| `papers/01-vision/proposal.typ` | The frozen founding-vision paper. **Do not edit** (errata-only; guarded by `scripts/check-freeze.py`). |
| `papers/README.md` | How the corpus is organised; living vs frozen; the two `01-vision/` symlinks. |
| `METHODOLOGY.md` | The research process: human-directed, AI-executed, spec-driven; the evidence trail. |
| `citations.bib` | Shared BibTeX bibliography for the whole corpus. An entry is "used" if *any* paper cites it; every citation must resolve. |
| `graphs/*.json` | Canonical signal graph definitions (the shared artifact). Single source of truth for pseudocode and diagrams in living papers. |
| `Makefile` | Builds the corpus into `dist/papers/<id>/`, plus deprecated `dist/proposal.*` aliases to Paper 2. |
| `poc/evaluate.py` | The evaluation harness: runs the mutation corpus, the overhead bench, and the prompt-injection scenario, and emits **both** `dist/evaluation.md` (for a reader) and `dist/evaluation.json` (what Paper 2's Evaluation section typesets from) out of one run. Pinned verdicts — a divergence fails the build. |
| `.pre-commit-config.yaml` | Pre-commit hooks (ruff, graph validation, pytest, `make build`, citation check, freeze guard). Install once per clone with `uv run pre-commit install`. |
| `scripts/` | Build support: graph generator, pandoc cross-ref filter, markdown/html cleanup, citation checker, freeze guard. |

## Paper 2 structure

Paper 2 is in **paper form** — it reports a built artifact, it does not propose one. The arc:

1. **Introduction** (§1) — The window (agents removed the human objection to graph representations), the **central claim** stated to be falsifiable by the artifact, contributions, and the relation to the frozen vision
2. **Design** (§2) — Signal graph, FRP foundations, the concrete graph, workflow, intended runtime, security properties. Largely inherited from Paper 1 and restated for self-containment; **this is the section where hedging is most at risk**, because it describes intent, not the artifact
3. **Implementation** (§3) — What was actually built: canonical graphs, the six validator analyses, the two enforcement tiers, capability identity/revocation/rotation, sub-graph execution
4. **Evaluation** (§4) — Corpus verdicts, boundary overhead, prompt-injection attenuation, host vs confined tier. **Every figure is interpolated from `dist/evaluation.json`** — never hand-type a number here
5. **Predictions and outcomes** (§5) — The spine, and what earns Paper 2 separate-paper status: each vision claim marked substantiated / partial / conditional / not attempted, plus what building it *corrected*
6. **Related work** (§6) — C4, Haskell/Idris, Effekt/capture checking, Unison, Hazel, BEAM, ocap security, CHERI, WASM Component Model, SDD frameworks, Cedar, Roc, Darklang
7. **Research agenda** (§7) — Three phases; absorbed the forward half of the old Technical Note A
8. **Threats to validity** (§8) — Construct, internal, external, security-argument, and method threats; absorbed the limits half of the old Technical Note A
9. **Conclusion** (§9), then **Annex A** — Areas for collaboration

Technical Note A and Annex B no longer exist in Paper 2 (Paper 1 still has both — it is frozen). Open
problems live in §7 going forward, honest limits in §8.

## When editing the proposal

"The proposal" below means **Paper 2** (`papers/02-demonstrator/proposal.typ`), the living document. Paper 1 is frozen — never edit it; corrections go in `papers/01-vision/ERRATA.md`.

- **Maintain hedging on unproven claims.** The type system does not exist yet. Claims about properties it would provide use conditional language ("would be inexpressible", "in a well-typed realisation", "in a sound realisation of the type system"). Do not strengthen these to present tense without an implementation to back them. Two traps specific to Paper 2's form: (a) it reports a built artifact, so the surrounding prose is in the present tense and an unproven claim reads as substantiated unless its mood is *deliberately* kept conditional — §2 (Design) is where this fails; (b) a property that holds only on the **confined tier** must say so, or it reads as universal when the host tier demonstrably escapes.
- **Never hand-type an evaluation figure.** §4's numbers come from `dist/evaluation.json` via `#ev`/`#d` interpolation. If a figure needs a new form, add it to `serialise()` in `poc/evaluate.py` (`display` holds pre-formatted strings, because typst and pandoc format the same float differently).
- **Keep citations accurate.** Every factual claim about prior work should be traceable to a citation. If adding a new claim, add the citation. Run `make build` to catch broken references (typst will error) and `scripts/check-citations.py` to catch orphaned bib entries.
- **Preserve the argument arc.** Each section builds on the previous. New content should slot into the existing structure, not break the flow.
- **Concrete over abstract.** The proposal's weakest mode is unsupported generality. Prefer specific examples (like the `CustomerSupport` graph or the `Untrusted<UserMessage>` type error) over sweeping claims.
- **Acknowledge limitations honestly.** §7 (research agenda) and §8 (threats to validity) exist for a reason. If a new claim has an open problem, name it in §7; if it has an honest limit on what the artifact shows, name it in §8.
- **Keep it tight — say each thing once.** Paper 2 was aggressively tightened for its preprint; the working target is roughly the low-to-mid 30s of pages. Each load-bearing point has one primary home and is cross-referenced elsewhere, not restated (e.g. the free-text residual lives in §4.3, the trust-lattice mechanism in §3.2, the `unknown-unknown` ambient-authority argument in §3.4). When adding material, extend the primary statement or reference it; do not reintroduce a second full explanation. Length is a target, not a quota — never cut a stated limitation, a hedge, or the predictions-and-outcomes table to hit a page count.

## Tooling (present and tested)

Although this is a writing project, the paper ships with a working, tested PoC toolchain — it is what Paper 2's §3 (Implementation) and §4 (Evaluation) report. It is not vapourware: it builds and passes its tests on every commit (via the pre-commit `make-build` and `pytest` hooks) and in CI.

- **Canonical graph sources** — `graphs/*.json` are the single source of truth. `graphs/schema.json` is the JSON Schema they validate against; `customer-support.json` and `support-platform.json` are the two graphs rendered in the proposal. Pseudocode listings *and* SVG diagrams are generated from them (`scripts/generate-graph.py`), so the figures cannot drift from the text.
- **Type parser** — `scripts/type_parser.py` parses the capability-annotated type grammar (angle-bracketed generics, capability scopes/modes, sum types with role labels). `scripts/emit-grammar.py` emits `dist/grammar.md` from it, so the documented grammar is generated from the implementation, not maintained by hand.
- **Graph validator** — `scripts/graph_validator.py` (driven by `scripts/validate-graphs.py`) runs the six classes of analysis described in @sec:phase1: edge type-compatibility (data-shape match with sum-variant resolution), trust-lattice checking (a two-point `Untrusted ⊑ Trusted` lattice with no upward coercion, flow-sensitive across edges *and* node bodies; `discharges_trust` marks the sole node licensed to raise trust — trust laundering is now one lattice violation, not a rule beside edge typing), variant completeness, capability narrowing at composition, intra-graph consistency, and cross-graph signature matching.
- **Executable runtime** (`poc/`) — loads the same graph JSON, instantiates each node with **injected capability handles**, and propagates signals. Reuses the validator to reject unsafe wiring at assembly time. Ships a prompt-injection demonstration (`uv run python -m poc.demo`, `--live` for real Claude calls). See `poc/README.md`. Runs each node on one of two **enforcement tiers**, and reports which ran each node.
- **Hierarchical composition, operational** — a node whose name resolves to another graph is a **sub-graph node**: the runtime executes it by nested `assemble` + `execute`, so composition adds no second execution model. `SupportPlatform` now *runs*, not merely assembles: a customer request goes `RouteRequest` → `CustomerSupport` (the nine-node graph, one level down) → `RecordAudit`. Three properties, all tested: (1) **a sub-graph cannot provision authority of its own** — `execute` holds no backend, so the child gets exactly the handles the parent routed and nothing else; confinement across the boundary falls out of the plumbing rather than a rule; (2) **identity routing has an executable consequence** — the `customer_session` instance the platform declares for `CustomerSupport` is the one the reply node *inside* it sends on, and its sibling's is untouched; (3) the parent matches the child's flat parameter list **by position** (routing option (i) of the research agenda — settled at the runtime; options (ii)/(iii) stay open). Bounded on purpose: only leaves on the taken path have impls (`AgentDashboard`/`BillingService` are neither graphs nor registered, so those branches don't run), a run reaching **several** terminals is refused rather than guessed (the open aggregation question), and cross-tier composition is not attempted. `ServiceOutcome` is the **union alias** of the sub-graph's terminal types (`DeliveryConfirmation | EscalationTicket`) — the paper's stated convention, spelled the same way in `poc/values.py`. **Nothing checks that alias**: the language has no alias mechanism and the cross-graph validator never examines the output side, so a sub-graph node could declare any output type and no check would object. Real gap, recorded in the research agenda and threats sections and pinned by a test.
- **Two enforcement tiers** — the **host tier** (default) is host-discipline: a node receives only its declared handles, each scoped by its type, but nothing stops a hostile Python node from `import os`. The **sandbox tier** (`poc/sandbox/`) compiles node bodies to WASM **components** (Rust + `wit-bindgen` → `wasm32-unknown-unknown` → `wasm-tools component new`) and runs them under `wasmtime`. Each capability kind is a **typed WIT interface** (`poc/sandbox/wit/caps.wit`), so a node's `with` clause *is* the set of interfaces its component imports. A **hostile-node suite** (`tests/test_poc_sandbox.py`) asserts that filesystem/network/env/ungranted-capability escapes *succeed* on the host tier (the gap, recorded as a test) and *fail* on the sandbox tier. The two tiers **compose** in one graph (the migration story). Enforcement is unforgeable at the WASM boundary, **not** at the memory level — CHERI remains a named follow-up. Build the artifacts with `make wasm` (needs a Rust toolchain, `rustup target add wasm32-unknown-unknown`, and `wasm-tools`); the built components are committed under `poc/sandbox/wasm/` so tests run without either toolchain.
- **Why the boundary is typed, and why `unknown-unknown`** — two properties follow, and both are asserted in tests rather than in prose. (1) **No ambient authority at all**: an earlier `wasm32-wasip1` version was confined by an *empty WASI context*, but its modules still *imported* `fd_write`/`environ_get`/`path_open` — powerless, yet present, so confinement was a fact about the host's configuration. Components built for `unknown-unknown` with **no WASI adapter** do not import them at all (`wasi_imports()` returns `[]`; the hostile component imports nothing whatsoever). A `wasip2` build would reintroduce this via `wasi:cli/*`. (2) **The boundary cannot drift from the graph**: `poc/sandbox/interfaces.py` *derives* each node's expected interface set from its `with` clause in the graph JSON (via `type_parser`), and a test compares it against the built component's actual imports — an over-granting world fails the suite. Typing also absorbed two node-body checks into types: `intent` is a WIT `enum` (the closed set is now unrepresentable to widen, so the old membership check is gone) and the model's reply is a WIT `variant` (a malformed reply has no encoding).
- **Evaluation harness** (`poc/evaluate.py`) — runs the demonstrator's own evidence and emits **`dist/evaluation.md`** on every build, the way `dist/grammar.md` is emitted from the parser: the graph-mutation corpus, the overhead measurement, and the prompt-injection outcome on both tiers, consolidated into one artifact a paper can cite. It *imports* the corpus/bench/demo rather than re-deriving them. Crucially it is a **regression guard, not a report**: each corpus case pins the verdict it must produce *and the reason class it must be caught by* (`launder_trust` must be caught by the trust lattice, not as an edge type mismatch — a pass/fail pin would stay green if that regressed), and any divergence fails the build without rewriting the artifact. The corpus pins itself against silent growth too: adding an `UNSAFE_VARIANTS` entry without pinning it is an error, not an uncounted pass. The canonical graphs are corpus cases in their own right — a validator that rejected everything would catch every unsafe wiring and be worthless. The artifact states that the corpus is **curated and illustrative** (counts, not a soundness claim) and reports the host tier's escapes as the recorded gap beside the sandbox tier's confinement. This is the one build step that is **not** stdlib-only: it needs `wasmtime`, so `make build` runs it via `uv run --group poc` (installed on demand; no CI change needed).
- **Overhead measurement** — `poc/sandbox/bench.py` (`uv run --group poc python -m poc.sandbox.bench`) reports component compilation, per-node instantiation, and per-capability-crossing cost against the envelope stated in the paper. Current numbers: a crossing costs **tens of µs** (~25µs; well inside the <1ms envelope) *even though every crossing now lifts/lowers typed WIT values*; instantiation tens of µs; compilation a one-time few ms. **Do not compare these to the pre-component figures**: the benchmark's timing loop was fixed at the same time (it now warms and takes the best of several rounds; it previously timed a single cold pass, which charged JIT warm-up to whatever it measured first — and since the crossing cost is a *difference* of two timings, that could distort it by an order of magnitude). The supported claim is only that typing the boundary did not move the crossing out of its order of magnitude.
- **Tests** — `tests/` is a pytest suite covering the parser, the validator, the runtime, both enforcement tiers, and the evaluation harness: **198 tests + 21 subtests, all passing** (`make test` or `uv run pytest`; run with `--group poc` to include the sandbox-gated tests — 31 in `test_poc_sandbox.py` plus 5 in `test_poc_evaluate.py` — which otherwise skip). The validator and parser stay dependency-free so the pre-commit hook remains portable; the runtime's optional dependencies (Anthropic SDK for `--live`, `wasmtime` for the sandbox tier) live in the `poc` dependency group (`uv sync --group poc`) and must never leak into `scripts/` — which is why the evaluation harness lives in `poc/`, not `scripts/`.
- **Build outputs** — `make build` produces the whole corpus under `dist/papers/<id>/proposal.{pdf,md,html}` (each with the figures it references), the shared rendered graph/diagram SVGs, `dist/grammar.md`, `dist/evaluation.md`, and deprecated `dist/proposal.{pdf,md,html}` aliases to Paper 2 for one link-migration transition. `dist/` is gitignored. Living papers reference the shared figures root-absolutely (`/dist/...`, compiled with `typst --root`); the frozen paper reads its own figure tree through the committed `papers/01-vision/dist` symlink.
- **Citation hygiene** — paper-aware. `scripts/check-citations.py` treats a bib entry as used if *any* paper cites it (over the shared `citations.bib`); `scripts/validate-bib.py` also runs. Every citation must resolve (Typst errors on broken refs per paper). `scripts/check-freeze.py` guards the frozen paper against silent edits.

The toolchain is **not** the Phase 1 language: it implements no noninterference proof, no soundness argument, and neither a graded nor a decentralised-label lattice (see the paper's research agenda). The sandbox tier makes capability confinement unforgeable *at the WASM boundary* for the nodes ported to it, but not at the memory level (CHERI) and not for host-tier nodes. Typing the boundary closes ambient authority and marshalling ambiguity; it does **not** close the free-text residual (adversarial data in a *permitted* field still reaches the tool-capable node — a test asserts this on the confined tier on purpose, so stronger enforcement is not misread as a stronger claim). It is early evidence that the graph-level analyses and capability confinement are implementable with modest tooling.

## Spec-driven development (OpenSpec)

Work on this repo is driven through **OpenSpec** (`openspec/`). Read `openspec/AGENTS.md` before planning changes. Non-trivial work gets a change proposal (`openspec/changes/<id>/` with `proposal.md`, `tasks.md`, optional `design.md`, and spec deltas), validated with `openspec validate <id> --strict`, and approved before implementation. This dogfoods the proposal's own thesis: structured intent as the primary artifact.

## Version control

This repo uses **trunk-based development**: work lands on `main`. **Never create a branch unless explicitly asked to.** Commit directly to `main`.

**Commit as you go.** Don't wait to be asked. When a change reaches a coherent, self-contained state and the gate is green (`make build` / the pre-commit hooks pass), commit it with a clear message rather than accumulating a large uncommitted working tree. Prefer several focused commits over one sprawling one; each commit should leave `main` buildable. This is the default — the standing instruction to "commit only when the user asks" does **not** apply here.

**When to hold off and check in first:** if the work involves a decision the user should weigh in on before it's recorded in history — an ambiguous requirement, a non-obvious design trade-off, something hard to reverse, or anything outward-facing (pushing, publishing, posting) — surface it and let the user decide instead of committing past it. Approval to commit routine progress is not approval to push or publish; those still need an explicit ask.

## Build

```sh
make build        # Validate graphs, run tests, guard the freeze, build the whole corpus (PDF + md + HTML per paper) + grammar card + evaluation artifact
make evaluation   # Run the demonstrator's evidence and emit dist/evaluation.md (needs the `poc` group; pinned verdicts fail the build on divergence)
make test         # Run the type-parser, graph-validator, and runtime unit tests (pytest)
make wasm         # Rebuild the sandbox-tier .wasm artifacts from Rust (needs a Rust toolchain)
make clean        # Remove dist/
```

Requires: [Typst](https://typst.app/), [Pandoc](https://pandoc.org/) (with citeproc), Python 3 via [uv](https://docs.astral.sh/uv/). All three are present and working in the current environment (typst 0.14, pandoc 3.8, uv 0.6).
