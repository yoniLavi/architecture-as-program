# A payee the account already pays: provenance for a bound payment

> **Status: proposed, not approved (17 November 2026).** Nothing is implemented until the
> author approves it and answers the open questions in `design.md` (task 0.1).

## Why

Two changes made the graph a bind needs expressible and checkable: an extractor before the
writer, with the writer bound to its fields. Neither changes what an injection does. The
pinned limits (`tests/test_bind_limits.py`, at `ea44088`):
- task 0's bound oracle plan, under AgentDojo's nine injections with the stand-in that
  obeys them, pays the attacker on 7 and meets the attack's goal on 4;
- the split answer the check accepts does exactly the same;
- D1's own extractor, bound, still pays a truncated IBAN.

A bind holds the writer to its input, and the input is whatever the extractor returned.
The next lever is a check on **where the payee came from**, applied where the money moves.

Measured against AgentDojo's banking environment (suite `v1.2.2`, the default environment,
read at `ea44088`):
- the account's past outgoing payments went to four IBANs. The attacker's
  (`US133000000121212121212`) is not among them, though a lookalike is
  (`US122000000121212121212`, the Apple Store);
- **task 0's legitimate payee, `UK12345678901234567890`, is not among them either.** It
  appears only in the bill, inside the very text an injection replaces. No check on the
  extracted value can tell it from the attacker's: both are new, and both come only from
  the untrusted bill;
- of the ground-truth payments in the 16 user tasks, the payee is a past payee in 4
  (tasks 3, 4, 6, and 15's `send_money`) and new in 1 (task 0). Tasks 5 and 11 name a
  merchant rather than an IBAN. Task 15's change of a scheduled recipient is not a
  `Payments` call.

So the honest version of this change is not "the injection is stopped". It is: **a
payment to a payee the account has never paid can be refused at the crossing, and the
cost is that every new payee, legitimate or not, then needs a decision outside the
graph.** This change measures both sides of that.

## What Changes

- **A new payee class, `known-payees`**, beside `any` and `inbound-senders`:
  `Payments<[known-payees], cap>`. It admits a payee only if the account has already sent
  it a completed payment. The handle reads that set from the bank at the crossing, as
  `inbound-senders` is read now, on both tiers. With a bind, both must hold: the payee is
  the bound value, and it is a known payee.
- **Narrowing follows from the existing rule** (`PaymentsScope.covers`), with no new code.
  `any` admits `known-payees`. `known-payees` and `inbound-senders` are incomparable. A
  literal payee list is not assignable to `known-payees`, because whether a literal is
  known depends on the run.
- **A refusal is the existing one**: "outside the handle's payees". Paper 4's fixed table
  (`poc/architect/measure.py`) already classes it, and the refused IBAN never passes
  through that table. Nothing in it changes.
- **Evidence:**
  - *Deterministic, pinned by tests:*
    - the handle's rule on both tiers: a past payee is paid; a new one is refused, and so
      is a lookalike;
    - a payee made known by a payment in the same run is admitted, which is stated as
      the rule's trust boundary.
  - *Predictions, committed before the measured runs:*
    - one per graph and injection: which payments are refused, and which tasks lose
      utility.
  - *The re-run of the pinned injection cases*, with each `Payments<[any], …>` grant
    rewritten to `[known-payees]`:
    - task 0's bound oracle plan, under the nine injections;
    - the split answer;
    - D1's bound replay.

    Each is reported as the attacker refused or paid, and the task's utility kept or lost.
    The predicted result for task 0 is that every attacker payment is refused **and the
    bill is not paid**. Both are pinned. The records go in a new file; the oracle-plan
    and bound records stay unchanged.
  - *A static count over the 16 tasks:* how many legitimate payments `known-payees` would
    refuse. Each such refusal is a confirmation the user would have to give.
- **A findings entry** in `docs/ROADMAP.md`, in counts, with the cost stated as plainly as
  the gain.

**Not in this change:**
- a confirmation channel: asking the user about a new payee, and modelling their answer.
  That needs a human, or a stated model of one, and is open question 3. This change only
  counts where a confirmation would be needed;
- any check on the **amount's** provenance. Under injection the attacker writes the
  document, so "a figure in the document" proves nothing; design D5 sets this out;
- offering `known-payees` to the architect. The registered `CATALOGUE` never changes;
  `SLICE_CATALOGUE` is open question 4. The evidence here uses hand-rewritten grants,
  labelled as such;
- `ScheduledPayments` and `UserProfile`: a scheduled recipient or a profile field is not
  checked;
- any live model run, and any paid spend;
- any change to `caps.wit` or `banking.wit`. The scope is enforced host-side, as
  `inbound-senders` is;
- any paper edit, and any move of Paper 4 toward review.

## Capabilities

### New Capabilities
- `payee-provenance`: what a payment grant may admit by where a payee came from: the
  `known-payees` class, its enforcement at the crossing, how it narrows, and the evidence
  that pins both what it stops and what it costs.

### Modified Capabilities
None. `value-bound-grants`' pinned limits stay as they are, for `[any]` grants. The new
pins are this capability's, for `[known-payees]` grants.

## Impact

- **Code:**
  - `scripts/type_parser.py`: one new member of `DYNAMIC_PAYEES`. It stays stdlib-only;
  - `poc/bank.py`: the known-payee set, and `_check_payment`;
  - `poc/agentdojo/harness.py`: a rewritten-grant run beside `bound_runs`, writing a new
    record.

  No registered code path changes meaning: no registered graph holds `known-payees`.
- **Tests:**
  - new `tests/test_payee_provenance.py`;
  - the parser's and the bank's existing tests are extended;
  - the Paper 2, 3 and 4 figure pins stay green without re-seeding. Paper 4's labels are
    pinned by hash and do not move.
- **Build:** `dist/grammar.md` gains the new payee class, because it is generated from the
  parser. That is a grammar card, not a paper figure.
- **Usage:** none. No step calls a model.
