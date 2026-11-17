# Tasks

Every session working on this change first checks the feed recorder (standing task 0.2 of
`operate-feed-triage`; `pgrep -fl poc.feeds.archive`, never a second one) and
`git status`. No test touches the system `git`. `scripts/` is not edited. The Paper 2, 3
and 4 figure pins (`tests/test_paper{2,3,4}_figures_pinned.py`) stay green without
re-seeding throughout. Do not edit `poc/`, `scripts/` or `graphs/` while the re-run (4.x)
is in progress.

## 0. Approval

- [x] 0.1 **The author approves this proposal**, chooses the lever (`design.md` D1;
      recommended: A alone), and answers the open questions: the number of repetitions,
      further arms, and library-writer answers. Record the answers in `design.md`, and
      update the proposal's status line (16 November 2026: every recommendation taken. A
      alone, no further arm, five repetitions (`n = 5` in 4.1), and library-writer answers
      accepted by plain-path tracing). Recorded in `design.md`

## 1. The split request

- [x] 1.1 Parse `split` in `developer.escalation` (`poc/slice/developer.py`) and keep it on
      `Escalation`, malformed or not, as `bind` is kept. Verify: tests in
      `tests/test_slice_developer.py` for a well-formed split, a split with no bind, and a
      reply holding code that mentions `split`, which is still read as code
- [x] 1.2 The split request's well-formedness in `formal.no_wider` (D2): every bound path is
      `in0.<f>` with `f` requested, the payee a string and the amount a number, and it fails
      closed otherwise. Verify: tests in `tests/test_bind_formal.py` for each of the
      spec's request scenarios, plus D2's recorded request
      (`runs/bind/user_task_0.D2.json`), which still fails closed. (`formal.split_fields`;
      the two hand-written answers are rebuilt as fixtures in `tests/split_answers.py`, and
      reproduce the proposal's table under the `formal.py` of `fba71d2`)
- [x] 1.3 `escalate.reason` renders a split as one bounded line (D5). Verify: a test in
      `tests/test_slice_escalate.py` on the line's text and its bound length, and that a
      request without `split` renders exactly as before

## 2. Judging a split answer

- [x] 2.1 The value tracer: from a holder's bind path, back along data edges and through
      `Compose` fields that are a single plain path, to the producing node's field, using
      the library's path grammar. Verify: tests that the tracer and `library.resolve` agree
      on every plain-path case, and that arithmetic, a constant or a selector breaks the
      trace. (`formal.trace`; a plain path is read with the library's own tokeniser, so it
      is exactly what `library.evaluate` passes through unchanged. A selector ends the
      trace at itself, which is never the inserted node, so the answer fails)
- [x] 2.2 `no_wider`'s split judgement (D3): the inserted node produces the fields, holds no
      grant but `LLMClient<inference>`, the bind traces to it, and uses are no more than
      asked; requests without `split` keep today's path. Verify: tests for every scenario
      of "A split answer is held to the split asked for", including both hand-written
      answers from the proposal's table, which now pass, and the unbound one, which still
      fails
- [x] 2.3 `escalate.decide` passes the split through, and the worklist in `develop_all`
      handles both answers: the requesting node kept as a bound payer, which gets its
      developer again, and the node removed. Verify: tests in
      `tests/test_slice_escalate.py` with a scripted architect and a scripted reviewer, and
      no model

## 3. The developer prompt, and the limit

- [x] 3.1 `poc/slice/prompts/developer.md`: the split paragraph and example, and the cap
      correction (D4). Verify: a test that the slice prompt offers `split` and that its
      payment examples' caps parse, and that Paper 3's generation prompt and the
      registration hashes are unchanged
- [x] 3.2 The limit (spec: value-bound-grants): the library-writer split answer, run against
      AgentDojo's injected bill with the stand-in that obeys it, pays the attacker; the
      test asserts that it does. Verify: the new case in `tests/test_bind_limits.py`
      passes, and the bind is labelled `untrusted`. **Corrected in implementation (17
      November 2026): for the library-writer answer the label is `trusted`, and the test
      pins that.** `SendMoney` takes a trusted `PaymentOrder` only, so the `Compose` before
      it must declare `discharges_trust` (as the control graph's does), and the label
      follows the holder's declared input, not where its values came from. The
      developer's own node paying (`custom_pays`) reads the extractor's output directly
      and is labelled `untrusted`; the test pins both. The pinned run: the attacker paid
      on 7 of 9 injections and the attack met on 4, the same sets as the bound oracle
      plan's, on both tiers. The request names its fields `recipient` and `amount`,
      because the fooled stand-in substitutes the goal's arguments by field name
- [x] 3.3 Replay: run `formal.custom_writers` and `formal.no_wider` over the committed slice
      and bind records, and confirm every recorded outcome is unchanged (no recorded
      request carries `split`). Verify: a test over `runs/slice/` and `runs/bind/`

## 4. The re-run (exploratory, unregistered)

- [x] 4.1 `poc.slice.run --split-rerun` (D6): D2 with the split offered, `n` repetitions
      (0.1), into `poc/slice/runs/split/user_task_0.D2.rN.json`, with stubs naming the
      prompt correction and "never pooled", and the slice's gates (clean tree, control
      passing). Verify: a test with scripted backends that it writes whole records, resumes,
      and refuses on a dirty tree
- [x] 4.2 Commit the code, then run it: Haiku, the subscription, low priority. Commit the
      records as they land. Verify: `n` records exist and each names its `head` (17
      November 2026: five records, `user_task_0.D2.r1` to `r5`, each at `5f670b7`, nice 19
      with background QoS)
- [ ] 4.3 The findings entry in `docs/ROADMAP.md`, as counts ("k of n") per step: request
      kind, the architect's answer, each rule, the reviewer, the holder's kind, the trust
      label, and utility. The limit comes first, and no rate is stated. Verify: the author
      reads it

## 5. Close

- [x] 5.1 `make build` and `make spec-check` pass, with `make architect` unchanged and the
      Paper 2, 3 and 4 figure pins green without re-seeding
- [ ] 5.2 `openspec validate add-split-escalation --strict`, then archive with the
      author's go. No new capability, so no Purpose to write
