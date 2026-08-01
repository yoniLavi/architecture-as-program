- [ ] 1.1 Grammar: `Clock`, `HTTPClient<[host, ...]>`, `Notifier<'channel'>` in `scripts/type_parser.py`;
      regenerate `dist/grammar.md` and confirm it is emitted, not hand-edited
- [ ] 1.2 Resolve the open question in `proposal.md` — `wasi:clocks` versus a bespoke clock interface —
      before writing the WIT, since it changes what §3.3.2 can say
- [ ] 2.1 WIT interfaces in `poc/sandbox/wit/caps.wit`; host-tier handles in `poc/handles.py`
- [ ] 2.2 Confined-tier bindings and a Rust node body exercising each; `make wasm` to regenerate the
      committed components
- [ ] 2.3 Confirm `poc/sandbox/interfaces.py` derives the new kinds with **no special case** — if it
      needs one, that is a finding about the derivation and belongs in the paper
- [ ] 3.1 Allowlist narrowing in the capability-narrowing analysis; reject a subset route
- [ ] 3.2 Hostile-node cases: clock-holder cannot open a socket, HTTP-holder cannot leave its
      allowlist, neither reaches the filesystem
- [ ] 4.1 Paper 2 §3.3.2: the clock demonstration, replacing the boast with a worked grant
- [ ] 4.2 Paper 2 §4.4: import-set evidence across seven kinds rather than four
- [ ] 4.3 `make build` green; full suite green with the `poc` group
