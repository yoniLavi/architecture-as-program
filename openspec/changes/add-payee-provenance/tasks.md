# Tasks

## 0. Approval

- [ ] 0.1 The author approves the proposal and answers `design.md`'s open questions 3
  (counting only, with no modelled user) and 4 (no `SLICE_CATALOGUE` entry). Record the
  date and the answers here. Nothing below starts before this box is checked.

## 1. The class

- [ ] 1.1 Add `known-payees` to `DYNAMIC_PAYEES` in `scripts/type_parser.py`. Verify:
  - a case in `tests/test_type_parser.py` parses it as dynamic;
  - narrowing cases pass: `any` covers it, and it is incomparable with `inbound-senders`
    and with a literal list;
  - the parser stays stdlib-only;
  - `dist/grammar.md` regenerates with the class.
- [ ] 1.2 Add `known_payees(bank)` (D2) to `poc/bank.py`: outgoing, completed payments only.
  `_check_payment` admits a payee in it. Verify, with `tests/test_banking_kinds.py` cases on
  AgentDojo's default environment:
  - the four past payees are admitted;
  - the attacker's IBAN, the lookalike, the bill's IBAN and an inbound-only sender are
    refused with "outside the handle's payees";
  - a payment made earlier in the run makes its payee known (D3).
- [ ] 1.3 Check the confined tier. Verify, with a test in `tests/test_payee_provenance.py`:
  a known payee is paid and a new one refused through the confined banking adapter, with
  `banking.wit` byte-identical.
- [ ] 1.4 Check the bind and the refusal. Verify, in `tests/test_payee_provenance.py`:
  - a bound `[known-payees]` grant refuses a bound new payee;
  - `measure.refusal` of that failure is the fixed payee line, and contains no IBAN.

## 2. Predictions, then the re-run

- [ ] 2.1 Rewrite grants with a harness function. It replaces `Payments<[any], uncapped>`
  with `Payments<[known-payees], uncapped>` and touches nothing else (D6). Verify: a test
  diffs each rewritten graph against its source, and the validator accepts all three.
- [ ] 2.2 Write predictions to `poc/agentdojo/predictions/known-payees.json`. Cover:
  - task 0's plan under the clean run and the nine injections;
  - the split answer under the same;
  - D1's bound replay.

  Each prediction says whether the attacker is paid and whether utility holds. Verify: a
  test holds the file's hash. **Commit before 2.3.**
- [ ] 2.3 Run the rewritten graphs. Use `OracleModel`/`FooledModel`, the host tier for all,
  and the confined tier for injection 0. Write the results to
  `poc/agentdojo/records/known-payee-plans.json`. Verify:
  - a test regenerates the record and compares it;
  - every outcome is compared with its prediction, and any mismatch is listed as a
    contradiction;
  - the existing tests still hold `oracle-plans.json` and `bound-oracle-plans.json`
    unchanged.
- [ ] 2.4 Pin the cost and one limit, in `tests/test_payee_provenance.py`:
  - task 0's bill is unpaid on the clean run;
  - an injected value equal to a known payee is paid (design, Risks).
- [ ] 2.5 Write the static count over the 16 tasks' ground-truth payments: payees that are
  known, new, or a merchant name, by task. Verify: a test pins it, and it currently reads
  4 known, 1 new, 2 merchant names.

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
