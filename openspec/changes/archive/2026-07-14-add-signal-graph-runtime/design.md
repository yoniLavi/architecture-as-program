## Context
The repo already has a stdlib-only type parser and graph validator that operate on `graphs/*.json`.
This change adds the first *executable* layer. The guiding constraints: reuse the existing static
tooling rather than duplicate it; keep the proposal toolchain stdlib-only and its build untouched;
and be scrupulously honest about enforcement fidelity, since the whole point is to demonstrate
(not overclaim) the proposal's security properties.

## Goals / Non-Goals
- **Goals:** Run the customer-support security vertical end-to-end; demonstrate capability injection,
  capability scoping, assembly-time rejection of unsafe wiring, and prompt-injection attenuation;
  produce a repeatable demo + tests.
- **Non-Goals (this change):** Unforgeable sandbox enforcement (WASM/WASI — next change); CHERI;
  replay/time-travel; the full 9-node graph as a deployable service; hierarchical composition
  (SupportPlatform); a visual editor; agent-authored node generation as an automated loop.

## Decisions

- **Decision: Python host, reuse `scripts/`.** The runtime imports `type_parser` and
  `graph_validator` directly. The "reject unsafe wiring at assembly time" guarantee is delegated to
  the validator, not reimplemented. Alternative (TypeScript host) was rejected for this first slice
  because it would duplicate the parser/validator and split the toolchain; revisit if/when the WASI
  work or a browser editor makes TS compelling.

- **Decision: capabilities as Python objects with a deliberately narrow surface.** A node function
  receives its handles as explicit arguments; there is no registry or global accessor. Scope is
  enforced by the object's methods: `InferenceLLM` has `.complete(...)` but no tool API;
  `ToolLLM([...])` exposes only the named tools; `ReadDBHandle` has `.read(...)` but no `.write(...)`.
  This is **host-discipline enforcement**: it shows the *shape* of capability confinement. It does
  not prevent a malicious node from `import os` — that is what the WASI tier (next change) adds. The
  PoC states this limitation in its output.

- **Decision: node implementations live in a registry keyed by node name.** At least one node
  implementation is **AI-generated** from its signature + contract (demonstrating "code as compiled
  artifact"); the generation prompt and the resulting code are committed as artifacts. The runtime
  treats node code as opaque — it only wires inputs/handles to outputs.

- **Decision: hybrid LLM execution behind a single flag.** `--live` uses real Anthropic calls for
  the LLM-backed nodes; default uses recorded fixtures captured from a prior live run. The exact
  model id, SDK, and call shape are taken from the `claude-api` reference at implementation time
  (not guessed here). Fixtures make the security tests deterministic in CI; the live path is what
  authentically stress-tests LLM-as-trust-discharger.

- **Decision: the prompt-injection demo is the primary deliverable.** Two unsafe-wiring variants of
  the graph are constructed in-memory and shown to fail assembly via the validator; one adversarial
  message is run through the real pipeline (live) to show the inference-only nodes cannot act and the
  tool-capable node never sees raw user text.

## Risks / Trade-offs
- **Host-discipline ≠ real sandbox.** Risk: demo overclaims enforcement. → Mitigation: the runtime
  prints, and the spec requires, an explicit fidelity disclaimer; unforgeability is deferred to the
  named follow-up change.
- **LLM trust discharge may be weaker than the proposal implies.** This is a *desired* risk to
  surface: if an adversarial message routes itself maliciously within the typed pipeline, that
  finding updates Technical Note A rather than being hidden.
- **Anthropic dependency / cost / nondeterminism.** → Mitigation: optional dependency group; fixtures
  by default; live path gated behind a flag and used sparingly.

## Migration Plan
Additive only. New `poc/` package and an optional `[dependency-groups] poc` in `pyproject.toml`.
Existing `make build`, validator, and pytest defaults are unchanged; runtime tests are opt-in or
fixture-backed so they do not require network access in CI.

## Open Questions
- ~~Which node to AI-generate first?~~ **Resolved: `ParseMessage`** — the trust-discharging node.
  It is the security crux, so AI-generating it best demonstrates "code as compiled artifact" on the
  load-bearing node. Nondeterminism is handled via recorded fixtures.
- Do we record fixtures as raw API responses or as node-output values? (Leaning node-output for
  stability against SDK changes.)
- How is node-local state represented if a vertical node needs it? (Deferred; flagged for Technical
  Note A if it bites.)
