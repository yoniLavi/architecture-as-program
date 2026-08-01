- [x] 1.1 Grammar: `Clock`, `HTTPClient<[host, ...]>`, `Notifier<'channel'>` in `scripts/type_parser.py`;
      regenerate `dist/grammar.md` and confirm it is emitted, not hand-edited
- [x] 1.2 Resolve the open question in `proposal.md` — `wasi:clocks` versus a bespoke clock interface —
      before writing the WIT, since it changes what §3.3.2 can say
      → **Resolved: `wasi:clocks/wall-clock@0.2.0` directly** (author approved). The WIT is vendored
      (wall-clock slice only) under `poc/sandbox/wit/deps/clocks/`; §6.7's argument is now demonstrated
      rather than asserted, and §3.3.2's "no ambient authority" sentence is qualified rather than
      weakened — "ambient" is defined as an import the `with` clause did not grant.
- [x] 2.1 WIT interfaces in `poc/sandbox/wit/caps.wit`; host-tier handles in `poc/handles.py`
- [x] 2.2 Confined-tier bindings and a Rust node body exercising each; `make wasm` to regenerate the
      committed components → `node_heartbeat` (all three kinds in one confined body) and
      `hostile_clocked` (clock-only)
- [x] 2.3 Confirm `poc/sandbox/interfaces.py` derives the new kinds with **no special case** — if it
      needs one, that is a finding about the derivation and belongs in the paper
      → No special case: each kind is one mapping entry; `interfaces_for_node`/`expected_imports`
      unchanged, and `wasi_imports()` needed no code change either — its granted-set logic already
      expressed "ambient = not granted", only its docstring needed the nuance spelled out. Pinned by
      `test_new_kinds_derive_from_a_with_clause_with_no_special_case`.
- [x] 3.1 Allowlist narrowing in the capability-narrowing analysis; reject a subset route
- [x] 3.2 Hostile-node cases: clock-holder cannot open a socket, HTTP-holder cannot leave its
      allowlist, neither reaches the filesystem
- [x] 4.1 Paper 2 §3.3.2: the clock demonstration, replacing the boast with a worked grant
- [x] 4.2 Paper 2 §4.4: import-set evidence across seven kinds rather than four
- [x] 4.3 `make build` green; full suite green with the `poc` group (307 tests + 21 subtests)
