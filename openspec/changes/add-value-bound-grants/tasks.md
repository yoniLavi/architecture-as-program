# Tasks

Every session working on this change first checks the feed recorder (standing task 0.3 of
`strengthen-generation-evidence`; `pgrep -fl poc.feeds.archive`, never a second one) and
`git status`. No test touches the system `git`. Paper 2, 3 and 4 figure pins
(`tests/test_paper{2,3,4}_figures_pinned.py`) stay green without re-seeding throughout.

## 0. Approval

- [x] 0.1 **The author approves this proposal** and answers the three open questions in
      `design.md` (16 November 2026: every recommendation taken. The escalation re-run 5.3
      goes ahead, the bound amount is a cap, and the `Custom` rule fails `Payments` only
      and reports the other writer kinds). Recorded in `design.md`

## 1. Declaring and checking a bind

- [x] 1.1 The bindable-kind table (`Payments` → `payee`, `amount`, `uses`) and the
      validator's structural bind checks in `scripts/graph_validator.py`, stdlib-only: a held
      grant, a bindable kind, data-input paths in range, a positive `uses`. Verify: new
      `tests/test_bind_validation.py` covers each rejection in the spec, and every canonical
      graph and corpus case still validates as pinned (`make evaluation` unchanged)
- [x] 1.2 Trust labels for binds, per variant, and enforcement of a claimed `trusted`.
      Verify: tests for an untrusted payee (accepted, labelled), a false `trusted` claim
      (rejected), and a sum input with one untrusted variant (labelled `untrusted`)
- [x] 1.3 The library's field-type check for binds against record schemas (`Extract`
      `fields`, `Custom` `fields`, `RECORDS`), and `bind` offered in `SLICE_CATALOGUE`'s
      text only. Verify: a test that a payee bound to a number fails, and the existing test
      that the registered `CATALOGUE` text is unchanged still passes

## 2. Enforcing a bind

- [x] 2.1 `BoundPaymentsFacade` in `poc/attenuate.py`: the bound scope passed down as
      `within`, and a use counter that only successful calls spend. Verify: unit tests in
      `tests/test_poc_attenuation.py` for another payee, an amount over the bound, a second
      call, a refused call that spends nothing, and a bind beneath a routing-point facade
- [ ] 2.2 Binding at node activation in `poc/runtime.py`: resolve the paths per activation,
      one facade per item under `each`, and fail the run on a path that does not resolve or
      has the wrong type. Verify: runtime tests for each case, including that no payment is
      made on a failed resolution
- [ ] 2.3 Both tiers. A hand-written hostile body holding a bound grant pays another payee,
      and then pays twice, on the host tier and as a confined component (crate under
      `poc/sandbox/rust/`, built with `make wasm`, committing only the new component). Verify:
      the crossing refuses both on both tiers, and the component's imports equal its derived
      interface set

## 3. Rendering

- [ ] 3.1 A bound grant renders with its bind and trust label in the reviewers' canonical
      graph (for slice runs), in `poc/slice/behaviour.py`, and on `poc/slice/page.py`. Verify:
      rendering tests, and a check that the registered reviewer's canonicalisation of a graph
      with no bind is byte-identical to before

## 4. The formal rules and the placement verdict

- [ ] 4.1 The `Custom`-writer rule in `poc/architect/formal.py`, as a separate function run by
      the slice path only. It fails an open `Payments` grant on a `Custom` node, and reports
      (does not fail) an unnarrowed `ScheduledPayments` or `UserProfile`, as 0.1 decided. Verify: tests for the spec's scenarios, plus a replay over the slice's
      records in which D2's final graph fails and no other unit does. `make architect` and its
      pins are unchanged
- [ ] 4.2 The escalation request gains an optional `bind`, and the no-wider check is applied
      in `poc/slice/escalate.py`. An unparseable request fails closed. Verify: tests for a
      wider answer (fails), an exact answer (passes), a bind with more uses (fails), and D2's
      recorded decision replayed (fails)
- [ ] 4.3 `misplaced` on the human page and in the verdict file schema. Verdict files already
      written are untouched. Verify: `tests/test_slice_page.py` covers the new verdict, and a
      test confirms the registered reviewer's prompt and scale hashes are unchanged

## 5. The limits, pinned

- [ ] 5.1 D1 replayed as a limit: the committed wrong-account body's graph, with `SendMoney`
      bound to `ParseBill`'s output. Pinned as **succeeding** (the truncated IBAN is paid).
      Verify: the test asserts the payment is made
- [ ] 5.2 The injection residual: an oracle graph for banking task 0 with an `Extract` →
      bound writer, run on stand-in models against AgentDojo's injections into the bill.
      Pinned as **succeeding** where the extractor returns the attacker's payee. Verify: the
      test asserts it, and the oracle-plans record is written apart from
      `poc/agentdojo/records/oracle-plans.json`, which is unchanged
- [ ] 5.3 Approved in 0.1: re-run D2's escalation once on the subscription (Haiku,
      low priority), with `bind` offered to developer and architect, recorded under
      `poc/slice/runs/bind/`. Exploratory and unregistered. Do not edit `poc/` while it runs.
      Verify: the record is committed, and the report states what the architect granted
- [ ] 5.4 A findings entry in `docs/ROADMAP.md`, giving what a bind buys and the two limits
      in 5.1 and 5.2, with no figure from a registered run. Verify: the entry names the tests
      that pin each claim

## 6. Close

- [ ] 6.1 `make build` and `make spec-check` pass, with the poc and agentdojo groups, and the
      Paper 2, 3 and 4 figure pins are unchanged. Verify: the commands' output, and a
      `git diff --stat` over `tests/*pin*.json` that shows no change
- [ ] 6.2 Archive the change. Write the `value-bound-grants` spec's Purpose in the archive
      commit. Verify: `openspec validate --archived` passes
