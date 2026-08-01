# Change: Typed WIT interfaces for clock, outbound HTTP, and notification

## Why

The demonstrator's capability kinds are the four its one domain needed: an LLM client, a database
handle, a response channel, an event emitter. That is enough to state the central claim and not
enough to test it. Every result about deriving a component's import set from its `with` clause is
currently a result about *four hand-modelled interfaces in one graph*, and the obvious question — does
the derivation hold up as the capability vocabulary grows, or was it tuned to what was there? — has no
evidence behind it either way.

Three kinds carry that weight and are the ones the feed-triage toy (`docs/ROADMAP.md`) needs first:

- **`Clock`** is the sharp one, and the reason to do this now. Paper 2 §3.3.2 currently makes a point
  of the confined components importing *no* clock function at all — the absence is structural, not
  configured. Granting a clock deliberately turns that from a boast into a demonstration: a `with`
  clause visibly buying an authority the artifact otherwise does not have, and `wasi:clocks` granted
  as a capability like any other, which §6.7 argues for and nothing currently shows.
- **`HTTPClient<allowlist>`** is the first capability whose *scope* is a set rather than a mode or a
  name, so it exercises narrowing in a shape the existing kinds do not.
- **`Notifier<channel>`** is the outbound side the toy needs, and the simplest of the three.

## What Changes

- Three capability kinds in the type grammar, each with a WIT interface, a host-tier implementation,
  and a confined-tier binding: `Clock`, `HTTPClient<[host, ...]>`, `Notifier<'channel'>`.
- `poc/sandbox/interfaces.py` derives their expected imports from a `with` clause exactly as it does
  for the existing kinds, and the existing test comparing derived imports against a built component's
  actual imports covers them without modification — that it needs no modification is the point.
- An allowlist-narrowing rule for `HTTPClient`, folded into the existing capability-narrowing-at-
  composition analysis: a parent may route a handle whose allowlist is a superset of what the
  sub-graph declares, never a subset.
- The hostile-node suite gains cases for each: a node granted a clock cannot open a socket, a node
  granted an allowlisted HTTP client cannot reach a host outside its allowlist, and neither can reach
  the filesystem.

## Impact

- Affected specs: `signal-graph-runtime` (one ADDED requirement), `trust-typing` (one ADDED)
- Affected code: `scripts/type_parser.py`, `poc/handles.py`, `poc/sandbox/wit/caps.wit`,
  `poc/sandbox/interfaces.py`, Rust node bodies under `poc/sandbox/`, `scripts/graph_validator.py`
- Affected papers: Paper 2 §3.3.2 gains the clock demonstration; §4.4's import-set evidence widens
  from four kinds to seven
- **Requires `make wasm`**, so a Rust toolchain and `wasm-tools` are needed to regenerate the
  committed components — the first change in a while that does
- Not in scope: the feed-triage graph itself, node-local state, the scheduler driver, and fan-in.
  This is the capability vocabulary those need, proposed separately so the vocabulary can be reviewed
  on its own terms rather than inside a larger change.

## Open question for review

Whether `Clock` should be granted as `wasi:clocks/wall-clock` directly or as a bespoke interface.
Granting the WASI interface is the honest demonstration of the §6.7 argument that WASI interfaces are
one instance of capability-as-interface; a bespoke one keeps the tier's "no WASI adapter" property
textually simple. The first is more interesting and slightly weakens a sentence the paper currently
gets to write cleanly, so it is a decision for the author rather than an implementation detail.
