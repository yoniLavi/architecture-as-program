# A split as an escalation: an extractor before the writer, the writer bound to it

> **Status: proposed, not approved (16 November 2026).** Nothing in it is implemented. The
> author chooses among the four options in `design.md` (D1), and answers its open questions,
> in task 0.1.

## Why

`add-value-bound-grants` (archived 16 November 2026, `fba71d2`) made a payment grant
bindable to a payee and an amount read from a node's own inputs. Its one live re-run of the
slice's D2 (`poc/slice/runs/bind/user_task_0.D2.json`) showed what remains:
- the developer of `PayBill`, a `Custom` node that reads the bill and pays, could not bind.
  Its only input is the bill's text, so no field names a payee or an amount. It said so in
  prose, and asked for `Payments<[any], 'bill-total'>`, which does not parse;
- the architect granted `Payments<[any], uncapped>` again, unbound, and the AI reviewer
  called it needed;
- `formal.custom_writers` and `formal.no_wider` rejected the edit, and the task was not done.

The rules stop the wide grant. Nothing leads anyone to the graph a bind needs: an extractor
before the writer, with the writer bound to the extractor's fields. **Worse, the rules
reject that graph too.** Measured at `fba71d2` by replaying today's checks over two
hand-written answers to a well-formed bound request (`Payments<[any], uncapped>` with
`payee=in0.iban, amount=in0.total, uses 1`). The script was read-only, in the session
scratchpad.

| The edit | `custom_writers` | `no_wider` |
|---|---|---|
| `Extract {iban, total}` → `PayBill` (`Custom`), bound to `in0.iban`, `in0.total` | passes | **fails**: the `Extract`'s `LLMClient<inference>` is "not within the request" |
| the same, with the writer unbound | fails | fails (the same, and `unbound-answer`) |
| `Extract` → `Compose` → `SendMoney`, bound to `in0.recipient`, `in0.amount` | passes | **fails**: the inference grant, and `bind-wider`, because paths are compared as text relative to each holder's own inputs |

So under today's rules, every split answer to D2 fails. The check counts the extractor's
inference grant as a widening, and it cannot follow a value through a `Compose`. D2's
request also could not have been met. The developer prompt's example cap, `'<cap>'`,
invited a non-number, and an unparseable request fails closed by design.

## What Changes

The recommendation, option A of `design.md` (D1): **a developer may ask for a split.** The
other three options are set out there, with what each would measure, and the author
chooses.

- **The developer's request may ask for a split.** It names the fields and types it needs
  as its first input, such as `{"iban": "string", "total": "number"}`, together with the
  bound grant over those fields. This is the slice's request format only, and the
  developer's prompt is the slice's (`poc/slice/prompts/developer.md`).
- **The architect receives the split as a structured reason**, beside the capability and
  the bind. Its catalogue, `SLICE_CATALOGUE`, does not change. The architect still decides,
  and may decline.
- **`formal.no_wider` learns to judge a split answer.** A node new in the edit must produce
  the requested fields with their types. That node may hold `LLMClient<inference>` and
  nothing else. The grant's holder must bind each requested field to that node's field,
  either directly or through `Compose` fields that are plain paths (`=inK.field`). An
  expression with arithmetic does not trace, and fails closed.
- **One harness correction to the slice's developer prompt.** The example cap becomes a
  number, or `uncapped` where the amount is bound. It is stated as a correction, because it
  changes what a re-run is compared with.
- **Evidence:**
  - *Deterministic, pinned by tests:* both split answers above pass. Each way of breaking a
    split fails: no bind, another field, an arithmetic `Compose`, an effect grant on the
    extractor, or more uses. D2's recorded request still fails closed.
  - *The limit, pinned as succeeding:* a split answer run against an injected bill pays
    the attacker. The split moves the choice of value to the extractor, and does not make
    the choice right.
  - *Exploratory, unregistered:* D2 re-run with the split offered, into
    `poc/slice/runs/split/`, never pooled with `runs/slice/` or `runs/bind/`. It uses Haiku
    on the subscription, at low priority. The number of repetitions is open question 1.

**Not in this change:**
- option B, a developer decomposing its node into a sub-graph. This is north-star step 5's
  other half, and likely Paper 5's;
- options C and D (a structured reason from the rules, and the pattern in the catalogue),
  unless the author picks either at 0.1;
- any change to the registered `CATALOGUE`, the architect's prompts, the reviewer's prompt
  or scale, the labels, or Paper 3's generation prompt and registration;
- any change to `caps.wit`, `banking.wit`, the type grammar or `is_assignable`;
- contracts for `Custom` nodes (the roadmap's "contracts are not optional"), which need
  their own change;
- bindable kinds other than `Payments`;
- re-running the slice's six architect units or D1;
- any paper edit, including Paper 2 v1.1 (task 9.2 of
  `build-feed-triage-and-generation-experiment`), and any move of Paper 4 toward review;
- a registered experiment, and any paid spend.

## Capabilities

### New Capabilities
None.

### Modified Capabilities
- `architect-pipeline`: the developer's escalation request may ask for a split, and the
  no-wider check judges a split answer by where the bound values come from.
- `value-bound-grants`: the pinned limits gain a split answer under injection.

## Impact

- **Code:** all of it is on the slice path.
  - `poc/slice/developer.py`: parsing the split request;
  - `poc/slice/prompts/developer.md`: the split form, and the cap correction;
  - `poc/slice/escalate.py`: the reason text;
  - `poc/architect/formal.py`: `no_wider`'s split judgement and the value tracing;
  - `poc/slice/run.py`: a `--split-rerun` mode writing to `runs/split/`;
  - `docs/ROADMAP.md`: the findings entry. The bind re-run was reported the same way, and
    `make slice` is not touched.

  No registered code path calls any of them. `scripts/` is untouched.
- **Tests:** `tests/test_slice_escalate.py`, `tests/test_bind_formal.py`,
  `tests/test_slice_developer.py`, and `tests/test_bind_limits.py` for the limit. The
  Paper 2, 3 and 4 figure pins stay green without re-seeding. The test that the registered
  `CATALOGUE` text is unchanged stays green.
- **Usage:** the re-run only, on the subscription.
