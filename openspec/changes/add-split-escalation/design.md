# Design

## Context

The motivation and the measurement are in `proposal.md`. These facts about the code shape
the options:

- **The architect may already redesign.** `develop_all` (`poc/slice/run.py`) is a
  worklist. An accepted edit may remove the requesting `Custom` node or add new ones, and
  each `Custom` node of the current graph gets one developer. D2's first run was answered by
  a redesign.
- **The escalation's architect sees the slice catalogue.** `escalate.edit` shows
  `mapping.system(SLICE_CATALOGUE)`, which carries `BIND_NOTE` beside `SendMoney`,
  `ScheduleTransaction` and `Custom`. It also sees the task, its abstract graph, its graph,
  and one reason line, `developer-request: node N asks for C bound {…}, because: '…'`.
- **The formal review is outside the architect's loop**, as in Paper 4. The rules' findings
  never reach the architect. A rejected edit leaves the graph before the request standing,
  and the developer gets no second request. Paper 4 kept the link check out of the loop so
  that a fabricated quote would not be repaired before review.
- **`no_wider` compares by text, per holder.** Every grant the edit adds or changes, on any
  node, must be assignable to the request. A bind's paths must equal the request's, and
  paths are relative to the holder's own inputs. So an extractor's inference grant counts as
  a widening, and a library writer's `in0.recipient` never equals a request's `in0.iban`.
- **`Compose` fields are expressions over `inN.path`** (`library.resolve`). A field that
  is exactly one path is a copy of that value, and so traceable. Anything else is computed.

## Goals / Non-Goals

**Goals:**
- Make D2's need expressible as a request, and checkable as an answer, so that the graph a
  bind needs can pass the review that guards it.
- Learn, in one small exploratory run, whether the developer asks for a split and whether
  the architect then makes one.

**Non-Goals:**
- Making the architect find the split unprompted (options C and D).
- Decomposition by the developer (option B).
- Choosing the extracted value safely. A split moves the choice of payee to the extractor,
  and contracts are still a later change.

## Decisions

### D1. Which lever: the options, and what each would measure

All four aim at the same graph: an extractor before the writer, with the writer bound to
the extractor's fields. They differ in who is asked to see that graph, and in what the
evidence would then show.

**A. The escalation may ask for a split (recommended).** This changes the **pipeline's
shape**: the request vocabulary grows a split form, and `no_wider` judges a redesign as an
answer. It also changes the **developer's** information position, through the slice prompt.
The **architect's** information position does not change. It receives only what the
developer sends, as before.
- *What it measures:* whether a developer who knows its input lacks the fields asks for
  them structurally, and whether an architect asked for that graph builds it. Then whether
  the gating rules accept it, the reviewer passes it, and the task gets done.
- *Why it is recommended:* D2's developer already diagnosed the problem, in prose ("input
  0 carries only a `text` field, so no `in0.<field>` path can bind the payee or amount").
  What it lacked was a form to say it in. The north star has escalation change the graph.
  A request for a graph change is that, said precisely. A also fixes the measured defect:
  today `no_wider` rejects every split answer, so no option yields an accepted split until
  the check can judge one. A needs that fix whichever option is chosen.

**B. The developer decomposes its node into a sub-graph** (north-star step 5). This
changes the **pipeline's shape** most. The developer authors a graph, and that graph needs
the validator, the formal review and the reviewer in turn. The sub-graph runtime and
routing-point attenuation already exist.
- *What it would measure:* whether developers restrict their own authority when they are
  free to.
- *Why not now:* decomposition can only narrow what the node holds, and D2's `PayBill`
  holds no payment grant. B cannot answer D2 without an escalation first. It is the back
  half's own question, and likely Paper 5's.

**C. The rules steer the architect with a structured reason.** This changes the
**pipeline's shape**: a loop from the formal review back to the architect, for
`custom_writers` and `no_wider` only, with the link check still outside. It also changes
the **architect's** information position: it learns the rules' verdicts, as fixed-table
reasons, never free text.
- *What it would measure:* whether the architect, told why its answer fails, finds the
  split itself.
- *Why not as the lever:* it would not have rescued D2 as run. The request did not parse,
  so `no_wider` fails every answer to it. It can also be satisfied the wrong way.
  `custom_writers` passes a literal payee and a cap, and the architect never sees the
  bill, so any literal it writes is invented. It would also turn the rules from a check
  into a constraint the architect is fitted to, the very reason Paper 4 kept the review out
  of the loop. It is a candidate second arm if A's run fails at the architect.

**D. The catalogue states the pattern** (`SLICE_CATALOGUE` only; the registered
`CATALOGUE` never). This changes only the **architect's** information position: its
stage-two text says that to pay values found in a document, one puts an `Extract` with the
fields first, then a writer bound to them.
- *What it would measure:* whether the architect follows a pattern it is given. That is a
  prompt's effectiveness, not the pipeline's.
- *Why not:* the roadmap called the gap "a design question, not a wording fix". D gives
  the answer instead of letting the pipeline reach it. It also changes the text every
  slice unit's stage two sees, so later units could not be compared with the slice's six.
  It is cheap, and a fair ablation after A.

### D2. The split request's form

    {"escalate": {"capability": "Payments<[any], uncapped>",
                  "split": {"fields": {"iban": "string", "total": "number"}},
                  "bind": {"payee": "in0.iban", "amount": "in0.total", "uses": 1},
                  "because": "…"}}

- `split.fields` is the record the developer asks to receive as its first data input,
  `in0`. The node's other inputs shift up by one.
- A split request must carry a `bind`. Every bound path is `in0.<f>`, with `f` in
  `split.fields`. A payee field must be a `string`, and an amount field a `number`.
- Anything else fails closed (`UNPARSEABLE_REQUEST`), as a malformed bind does now.
- *Rejected:* letting the request name the extractor (`Extract` or a `Custom` parser). How
  to produce the fields is the architect's choice, and the request states only the need.

### D3. Judging a split answer (`no_wider`)

For a split request, an edit passes when there is a node `E`, absent before the edit,
that meets four conditions:
1. **`E` produces the fields.** Its output record has every requested field with its type.
   The library check already knows `Extract` and `Custom` `fields`.
2. **`E` holds nothing with an effect.** Its only possible grant is `LLMClient<inference>`.
   This grant is exempt from "not within the request", and is the only grant the exemption
   covers.
3. **The bind traces to `E`.** The requested grant (assignable to the request) is held by
   some node `W`. `W`'s bind traces each requested field to `E`'s same field: either
   directly (`W`'s `in0` is `E`'s output), or through a chain of `Compose` nodes whose
   field is a single plain path (`=inK.f`). Tracing follows data edges. Arithmetic, a
   constant, or a selector in the chain breaks the trace, and the edit fails (`BIND_WIDER`).
4. **Uses are no more than asked.**

Every other grant the edit adds or widens is judged as before. `W` may be the requesting
node, still `Custom`, or a library writer. `custom_writers` still applies to `W` if it is
`Custom`, and a bound grant passes it.

*Rejected:* accepting only the "requesting node pays" shape, which keeps the text
comparison. The library-writer form keeps payment authority out of developer code. The
human page's new `misplaced` verdict exists to prefer that form, so the check must not
reject it.

*Rejected:* tracing through arbitrary expressions. Proving `=in0.total * 1` equal to its
source is a solver's job, and the check stays dependency-free and conservative.

### D4. The developer prompt: the split form, and one correction

`poc/slice/prompts/developer.md` gains one paragraph on the split form, with one example.
It says when to use it: when no field of the node's inputs names a value the bind needs.
Its payment example's cap changes from `'<cap>'` to "a number, or `uncapped` where the
amount is bound". D2's request (`'bill-total'`) failed to parse on that placeholder.

This is a harness correction, and the re-run's record says so. The re-run therefore
differs from the bind re-run in two respects, both on the developer's side. Paper 3's
generation prompt and registration are a different file and do not move.

### D5. The reason the architect receives

`escalate.reason` renders a split as one bounded line:

    node PayBill asks to be split: a node before it producing {iban: string, total: number}
    from its inputs, then Payments<[any], uncapped> bound payee=in0.iban, amount=in0.total,
    once, because: '…'

The `EDIT` text and the system text are unchanged.

### D6. The re-run

`python -m poc.slice.run --split-rerun` runs the hand-built D2 with the split offered. The
gates are the slice's: a clean tree, and the control passing. Records go to
`poc/slice/runs/split/user_task_0.D2.rN.json`, one file per repetition. A repetition is
written whole or not at all, and a rerun resumes.
- It uses Haiku on the subscription, at low priority (`poc/polite.py`). It is exploratory
  and unregistered, and never pooled with `runs/slice/` or `runs/bind/`.
- What each repetition reports, as counts: whether the developer asked for a split (or a
  plain bind, or nothing); whether the architect split, granted wide, or declined; each
  rule's finding; the reviewer's verdict on the changed grants; whether `W` is the `Custom`
  node or a library writer; the bind's trust label; and the task's utility on the clean
  environment.
- No rate is stated: the result is "k of n", with n the author's (open question 1).

## Risks / Trade-offs

- [The split is read as a defence] → The split graph under injection is pinned as paying
  the attacker (spec, value-bound-grants). The roadmap entry says so first. *Corrected
  in implementation, 17 November 2026:* this line said the bind is labelled `untrusted`
  wherever the extractor read untrusted text. That holds only where the developer's node
  pays. A library writer takes a trusted record, so some node upstream of it declares the
  discharge (the `Compose` in the fixture, the `Extract` in the re-run's answers), and its
  bind is labelled `trusted` (task 3.2 pins both). The label follows
  the declaration, so it cannot carry this risk; only the pinned limit does.
- [Two developer-side changes confound the re-run's comparison with the bind re-run] → Both
  are stated in the record's stubs. The cap correction alone would only have made D2's
  request parse, and D2 would still have had no field to bind, which is the gap this change
  closes.
- [The inference exemption is a hole] → It covers one grant, `LLMClient<inference>`, on the
  one node the split inserted, and only for a split request. An inference grant moves no
  money. It does give an `Extract` the untrusted bill, and that is the residual the limit
  pins.
- [Tracing through `Compose` is a second resolver that could drift from `library.resolve`]
  → It reuses the library's path grammar (`_PATH`). A test holds the tracer and the
  resolver to the same plain-path cases.
- [Touching `formal.py` moves a Paper 4 pin] → `no_wider` is slice-only, and no registered
  path calls it. `make architect` and `tests/test_paper4_figures_pinned.py` run in the
  close phase.
- [Haiku again in every role, the architect and the reviewer the identical model] → As in
  the slice. Stated as diversity at most, never independence.

## Migration Plan

Additive. A request without `split` is judged exactly as before. Nothing is pushed or
published.

## Open Questions

**Answered by the author, 16 November 2026 (task 0.1): every recommendation taken.** The
lever is A alone, with no further arm (C and D stay candidates for a later change). The D2
re-run has five repetitions. Library-writer answers are accepted by tracing plain-path
`Compose` fields.

The questions as put:

1. **How many repetitions of the D2 re-run?** *Recommended: five.* One run is an anecdote.
   Five give "k of 5" for each step, with no rate claimed, and the author has said the
   usage window is not a concern. One keeps the precedent of the bind re-run.
2. **The lever (D1).** *Recommended: A alone.* A one-variable change keeps the re-run
   readable. Should C (one structured retry from the rules) or D (the pattern in
   `SLICE_CATALOGUE`) be added as a further arm? If so, each needs its own records
   directory and its own repetitions.
3. **Library-writer answers (D3).** *Recommended: accept them, by tracing plain-path
   `Compose` fields.* The alternative accepts only "the requesting node pays", which is
   simpler, but rejects the form that keeps payment out of developer code.
