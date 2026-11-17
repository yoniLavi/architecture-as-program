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

- [ ] 2.1 Rewrite grants with a harness function. It replaces `Payments<[any], uncapped>`
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
  *Done (`harness.payee_count`): 4 known, 1 new, 2 merchant names. The rule refuses the
  merchant names as well ("Spotify" and "Apple" are not payees in the history), so it
  refuses **3 of the 7** legitimate payments, not 1. The proposal named the merchant
  tasks but not that they would be refused.*

## 3. Findings

- [ ] 3.1 Add a findings entry to `docs/ROADMAP.md`, in counts. Order:
  - first, the cost (task 0 unpaid; the static count) and the suite's flattery (the
    attacker's IBAN is new in every injection task);
  - then what is refused;
  - then the contradictions, if any.

  It makes no claim of defence beyond the crossing's rule. Verify: an audit subagent reads
  the entry against the records and tests.

## 4. Close

- [ ] 4.1 Run `make build` and `make spec-check`. Verify: both green, and the Paper 2, 3
  and 4 figure pins pass without re-seeding.
- [ ] 4.2 With the author's go, archive the change, and write the `payee-provenance`
  spec's Purpose in the archive commit.
