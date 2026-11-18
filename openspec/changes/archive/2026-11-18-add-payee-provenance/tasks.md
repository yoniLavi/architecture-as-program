# Tasks

## 0. Approval

- [x] 0.1 The author approves the proposal and answers `design.md`'s open questions 3
  (counting only, with no modelled user) and 4 (no `SLICE_CATALOGUE` entry). Record the
  date and the answers here. Nothing below starts before this box is checked.
  *Approved 17 November 2026, with every recommendation taken ("let's please go with your
  recommendations"):*
  - Q3: count where a confirmation would be needed; model no user's answer;
  - Q4: no `SLICE_CATALOGUE` entry;
  - Q1 and Q2 stay deferred.

## 1. The class

- [x] 1.1 Add `known-payees` to `DYNAMIC_PAYEES` in `scripts/type_parser.py`. Verify:
  - a case in `tests/test_type_parser.py` parses it as dynamic;
  - narrowing cases pass: `any` covers it, and it is incomparable with `inbound-senders`
    and with a literal list;
  - the parser stays stdlib-only;
  - `dist/grammar.md` regenerates with the class.

  *Done. The last check's premise was wrong: the grammar card
  (`scripts/emit-grammar.py`) documents no banking kind, and so names neither
  `any` nor `inbound-senders`. It regenerates, and is unchanged. Adding a
  `Payments` section would be an unplanned `scripts/` edit, so it is left to
  the author. The slice's behaviour page (`poc/slice/behaviour.py`) gained
  words for the class ("anyone the user has already paid"), so a
  `known-payees` grant never renders as "no payee"; no slice graph holds one.*
- [x] 1.2 Add `known_payees(bank)` (D2) to `poc/bank.py`: outgoing, completed payments only.
  `_check_payment` admits a payee in it. Verify, with `tests/test_banking_kinds.py` cases on
  AgentDojo's default environment:
  - the four past payees are admitted;
  - the attacker's IBAN, the lookalike, the bill's IBAN and an inbound-only sender are
    refused with "outside the handle's payees";
  - a payment made earlier in the run makes its payee known (D3).

  *Done. The default environment has no inbound-only sender (its one sender, GB29, was
  also paid), so that case adds one inbound row to a copy. The copy is held to
  AgentDojo's history where the `agentdojo` group is installed. The proposal's
  "lookalike" (the Apple Store's IBAN) differs from the attacker's in two digits, not
  one; a one-character lookalike, a case change and a trailing space are refused too.
  Also pinned: a scheduled order does not make its recipient known, and the cap still
  holds.*
- [x] 1.3 Check the confined tier. Verify, with a test in `tests/test_payee_provenance.py`:
  a known payee is paid and a new one refused through the confined banking adapter, with
  `banking.wit` byte-identical.
  *Done, bound and unbound, on task 0's graph with `PayBill` confined; `banking.wit` and
  `caps.wit` are held by hash.*
- [x] 1.4 Check the bind and the refusal. Verify, in `tests/test_payee_provenance.py`:
  - a bound `[known-payees]` grant refuses a bound new payee;
  - `measure.refusal` of that failure is the fixed payee line, and contains no IBAN.

  *Done. A spy shows the bind in force on each run. The failure message names the IBAN;
  the reason built from it does not.*

## 2. Predictions, then the re-run

- [x] 2.1 Rewrite grants with a harness function. It replaces `Payments<[any], uncapped>`
  with `Payments<[known-payees], uncapped>` and touches nothing else (D6). Verify: a test
  diffs each rewritten graph against its source, and the validator accepts all three.
  *Done: `harness.rewrite_known_payees` (exact strings and keys only; a bind is keyed by
  its grant). The split answer and D1 are test fixtures, which `poc` does not import, so
  the three cases are built in `tests/known_payee_cases.py`, which also writes the record.*
- [x] 2.2 Write predictions to `poc/agentdojo/predictions/known-payees.json`. Cover:
  - task 0's plan under the clean run and the nine injections;
  - the split answer under the same;
  - D1's bound replay.

  Each prediction says whether the attacker is paid and whether utility holds. Verify: a
  test holds the file's hash. **Commit before 2.3.**
  *Done: 41 predictions (two cases × clean + nine injections × two stand-ins + one
  confined injection, and D1's replay), derived from the committed `[any]` records and
  the rule, before any rewritten case ran. Every run is predicted refused, the attacker
  unpaid, the bill unpaid, and no injection goal met. Compared fields: `refused`,
  `attacker_paid`, `utility`, `attack_success`.*
- [x] 2.3 Run the rewritten graphs. Use `OracleModel`/`FooledModel`, the host tier for all,
  and the confined tier for injection 0. Write the results to
  `poc/agentdojo/records/known-payee-plans.json`. Verify:
  - a test regenerates the record and compares it;
  - every outcome is compared with its prediction, and any mismatch is listed as a
    contradiction;
  - the existing tests still hold `oracle-plans.json` and `bound-oracle-plans.json`
    unchanged.

  *Done: 41 runs, no contradictions. No run made a payment: 16 tried the attacker
  (host and confined) and 24 tried the bill, and all were refused. D1's replay runs
  confined throughout, because its body has no host form.*
- [x] 2.4 Pin the cost and one limit, in `tests/test_payee_provenance.py`:
  - task 0's bill is unpaid on the clean run;
  - an injected value equal to a known payee is paid (design, Risks).

  *Done. The limit is injection 0 with its payee swapped for the Apple Store's IBAN
  (paid before; two digits from the attacker's). The fooled stand-in obeys it, and the
  bound writer pays it on both tiers.*
- [x] 2.5 Write the static count over the 16 tasks' ground-truth payments: payees that are
  known, new, or a merchant name, by task. Verify: a test pins it, and it currently reads
  4 known, 1 new, 2 merchant names.
  *Done (`harness.payee_count`): 4 known, 1 new, 2 merchant names. As first written,
  this note said the rule refuses "3 of the 7, not 1". Verification corrected it: the
  rule refuses **1 of the 7 unavoidably** (task 0), and 3 of 7 only if the merchant
  names are paid as AgentDojo's ground truth spells them. Each name resolves to one
  known IBAN, and `payee_count` now computes and reports both readings.*

## 3. Findings

- [x] 3.1 Add a findings entry to `docs/ROADMAP.md`, in counts. Order:
  - first, the cost (task 0 unpaid; the static count) and the suite's flattery (the
    attacker's IBAN is new in every injection task);
  - then what is refused;
  - then the contradictions, if any.

  It makes no claim of defence beyond the crossing's rule. Verify: an audit subagent reads
  the entry against the records and tests.

  *Done. The audit recounted every figure independently and found them all correct, the
  order met, and no claim of defence beyond the crossing. It raised seven wording points,
  all taken. Three were real: task 6 is a scheduled payment, not a `send_money`; under
  `[any]` the goal was met 10 times of 38, the confined runs included; and "utility lost"
  became "utility false", because some runs never had it. Four tightened the text: D1's
  truncated IBAN, injection 7 naming no payee, D3 being pinned at the handle, and where
  the predictions came from.*

## 4. Close

- [x] 4.1 Run `make build` and `make spec-check`. Verify: both green, and the Paper 2, 3
  and 4 figure pins pass without re-seeding.
  *Done: `make build` green (1822 passed, 1 skipped); `make spec-check` 40/40; no pin
  re-seeded.*
- [x] 4.2 With the author's go, archive the change, and write the `payee-provenance`
  spec's Purpose in the archive commit.
  *Done 18 November 2026, on the author's go ("Great, yes, accepted"), after the
  verification below, which the author took in place of their own read. The main spec
  is created with the delta's Purpose.*

## Verification before the archive (17 November 2026)

Two read-only subagents ran in parallel, per AGENTS.md's convention: one for conformance,
one adversarial. Neither was given the implementer's conclusions. Neither found a fault in
the mechanism: the rule, its interaction with binds, both tiers, and the counts in the
findings all held when probed independently. Their findings, and what was done:

**Fixed (tests and harness; no result moved):**
- 2.1's "the validator accepts all three" was not asserted: `check_graph` returns a list,
  and its result was dropped. Both the validator (`validate_graph_dicts`) and the library
  check, with the right catalogue, are now asserted empty.
- `refused` matched a substring that a bind, `inbound-senders` or a literal list also
  raise. It now requires the class's own refusal (`harness.KNOWN_REFUSAL`), and the tier
  and bind tests assert it. All 41 runs still meet it.
- The confined tier was assumed, not observed. A spy now shows the `SendMoney` component
  instantiated, for the known payee paid and the new one refused.
- The contradiction path was never exercised. Tests now flip one prediction (`utility`,
  `attempted_payee`, `refused`) and drop all of them; each case is listed.
- `attempted_payee` was predicted but not compared. The harness now records and compares
  it. The record gained that field and is otherwise unchanged; the hash-pinned predictions
  file is untouched.
- D3 was pinned only on `MemoryBank`. It is now also pinned through AgentDojo's bank,
  whose `send_money` records the sender as the account's IBAN.
- `_paid` checked only `send_money`; it now counts scheduled payments too.

**For the author before the archive (each changes a claim or the design).** *Accepted by
the author on 18 November 2026 and applied. The ROADMAP entry gives both cost readings,
the predictions' provenance and the host tier's qualification. D1 and open question 1
carry a dated correction. `payee_count` computes the merchant resolution.*
- **The cost is overstated** (both verifiers). "The rule refuses 3 of the 7" reads
  AgentDojo's ground truth literally. Both merchant names resolve to known IBANs, and task
  5's own utility requires the known Spotify IBAN; task 11's checks only the amount. Only
  task 0's refusal is unavoidable: 1 of 7 for certain, 3 of 7 if names are paid as
  written. Affects `docs/ROADMAP.md`, the 2.5 note, and `payee_count`'s `refused`.
- **D1's premise is false** (both verifiers). Four user tasks name an IBAN in their prompt
  (3 and 4: GB29…; 6: US122…; 15: CA133…). D1's conclusion roughly survives, since 3, 4
  and 6 are already known and 15's goes to a standing order. But open question 1 is framed
  on the false premise, and this suite is one whose prompts carry payees.
- **Provenance wording.** The predictions say they were written "before any rewritten
  case was run". Tests in `658b1fe` had already run the rewritten task 0 graph on
  hand-picked payees; the measured run came after. The file is hash-pinned, so only the
  findings entry can say so.
- **Tier qualification.** The findings say "on both tiers" without saying that host-tier
  enforcement is host discipline.
- *(Trivial, file pinned, left as is.)* The predictions' method says "goals 0, 1, 3 and 5
  need a payment". Goals 2, 6 and 8 need one too; 0, 1, 3 and 5 are those any payment
  meets.
