# Design

## Context

See `proposal.md` (Why) for the measured starting point. The constraints that shape the
design:

- **Payee scope is already host-side.** `PaymentsScope` (`scripts/type_parser.py`) splits a
  payee list into literals and the environment-read sets of `DYNAMIC_PAYEES` (`any`,
  `inbound-senders`). `_check_payment` (`poc/bank.py`) checks every scope in `within`, and
  reads `inbound_senders(bank)` at the crossing. The confined tier's banking adapter calls
  the same handle, so a new dynamic set is enforced on both tiers without touching
  `banking.wit`.
- **Narrowing is already general.** `PaymentsScope.covers` admits everything under `any`.
  Otherwise it requires `other.dynamic ⊆ self.dynamic` and `other.literal ⊆ self.literal`.
  A third dynamic set falls into this rule with no new code.
- **Refusals are already classed.** `poc/architect/measure.py` maps "outside the handle's
  payees" to a fixed line. A known-payee refusal raises exactly that message.
- **The pinned limits are fixtures.** Each of them is a `[any]` grant run with the
  stand-ins:
  - task 0's bound oracle plan (`harness.bound_runs`);
  - the split answer (`tests/test_bind_limits.py`);
  - D1's bound replay.

  Re-running them with a different grant needs no model.

## Goals / Non-Goals

**Goals:**
- One new payee class with an exact, testable meaning, enforced where the money moves.
- A measurement that states both what the class stops and what it refuses that the user
  wanted.

**Non-Goals:**
- Making task 0 pass under injection. The proposal shows that no value check can do it,
  because the legitimate payee is as new as the attacker's.
- A general provenance lattice for values. This change covers one field, the payee, and
  one source, the account's history.

## Decisions

**D1. The source of trust is the account's history, not the prompt.**
- *Alternative considered:* admit a payee that appears in the user's own words.
- *Why not:* in banking `v1.2.2` no user task names an IBAN in its prompt. The tasks that
  name a payee name a merchant ("Spotify", "Apple") or a person, and resolving those is a
  lookup in the history anyway.
- *Consequence:* a prompt-quoted class would add a parser and still admit nothing in this
  suite. It stays a candidate for a suite where prompts carry IBANs (open question 1).
- *Correction (verification before the archive, 18 November 2026; accepted by the
  author).* The premise is false. Four user tasks name an IBAN in their prompt: 3 and 4
  (`GB29NWBK60161331926819`), 6 (`US122000000121212121212`) and 15
  (`CA133012400231215421872`). The decision survives on other grounds:
  - the three `Payments` payees among them are already known payees;
  - task 15's goes to a standing order, which `known-payees` does not cover;
  - task 0's bill payee, the one the class refuses, is not in its prompt.

  So a prompt-quoted class would admit nothing here that `known-payees` refuses. This
  suite *is* one whose prompts carry payees, and open question 1 should be read so.

**D2. Outgoing, completed payments only.**
- A payee is known if a transaction in the history has the account as sender ('me' or its
  IBAN) and the payee as recipient.
- *Scheduled payments are excluded.* A standing order can be created by the same kind of
  injected instruction this rule is meant to stop. Counting it would let one injection
  launder the next. In this environment it excludes no payee, since both scheduled
  recipients are also past payees.
- *Incoming senders are excluded.* They already have their own class, `inbound-senders`.

**D3. The set is read at the crossing, and a payment earlier in the run counts.**
- *Alternative considered:* snapshot the set at assembly.
- *Why not:* the crossing is the only place the handle sees the bank. `inbound-senders`
  already works this way, and a snapshot would need a new plumbing path through `World`.
- *Consequence:* a graph that holds both `[any]` and `[known-payees]` can make a payee
  known and then pay it again. That is a property of the graph's grants, which the
  validator and review see. It is stated as the trust boundary and pinned by a scenario.
  No pinned case holds both grants.

**D4. Exact string membership.**
- No normalisation of spaces or case. The lookalike scenario pins the consequence.
- *Alternative considered:* normalise IBANs.
- *Why not:* normalisation is a parser of attacker-supplied text sitting in front of an
  authority check, and nothing in the suite needs it.

**D5. No amount provenance in this change.**
- The idea in the request was "an amount must match a figure in the document". Under
  injection the document is the attacker's: in every case pinned here, the injection is the
  bill's text. A figure in the document is therefore a figure the attacker chose.
- An amount check that would mean something compares against the history, for example
  "no more than the largest past payment to this payee". It is left as open question 2
  rather than built, because the cap already bounds the amount and nothing pinned here
  separates the two.

**D6. The evidence rewrites grants by hand, and says so.**
- The re-run takes the three pinned graphs and replaces `Payments<[any], uncapped>` with
  `Payments<[known-payees], uncapped>`. Nothing else changes. The rewrite is a function in
  the harness, tested to touch only that string.
- *Alternative considered:* have the slice architect choose the class.
- *Why not:* that needs the class in `SLICE_CATALOGUE` and a live run, and the result would
  mix two questions: whether the architect picks it, and what it does once picked.

**D7. Predictions before outcomes, and a separate record.**
- Predictions go in `poc/agentdojo/predictions/known-payees.json`, committed before the
  run. The outcomes go in `poc/agentdojo/records/known-payee-plans.json`.
- `oracle-plans.json` and `bound-oracle-plans.json` are held unchanged by their existing
  tests.

## Risks / Trade-offs

- **The headline reads as a defence.** Task 0 shows zero attacker payments under the rule.
  → The same record pins that the bill is unpaid. The findings entry opens with the cost,
  and with the fact that a refused legitimate payment and a refused attack look identical at
  the crossing.
- **The suite flatters the rule.** The attacker's IBAN is new in every injection task.
  → An attacker who can first get one payment made, for example to a payee already known,
  is out of the rule's reach. The findings name this limit. A test pins one case of it: an
  injection whose goal is a known payee is paid.
- **The history is part of the environment.** On a real account, an attacker who can write
  the history can grant themselves the class. → Stated as an assumption, the same one
  `inbound-senders` already makes.
- **Paper 4's numbers.** `known-payees` is in no registered graph, and the labels file
  never names it. The Paper 4 pins are held by test, unchanged.

## Migration Plan

None. The class is additive: no existing graph holds it, and `any` keeps its meaning.

## Open Questions

1. *(deferrable)* A prompt-quoted payee class (D1), for a suite whose prompts carry
   payees. It stays out of this change; it is recorded so the decision is not lost.
   *(Corrected: banking `v1.2.2`'s prompts do carry payees, in four tasks; see D1. Here
   the class would add nothing, which is a fact about this suite, not about the class.)*
2. *(deferrable)* An amount bound read from history (D5). It is left out; this question
   asks whether to propose it after the findings are read.
3. *(for task 0.1)* The confirmation channel. This change counts where a confirmation
   would be needed and models no answer. The author confirms that counting is the scope,
   and that a modelled user (always confirm, never confirm, or confirm only payees named in
   the prompt) is a later change, if any.
4. *(for task 0.1)* Offering `known-payees` in `SLICE_CATALOGUE`. Recommended **no** for
   this change (D6). The registered `CATALOGUE` is not a candidate either way.
