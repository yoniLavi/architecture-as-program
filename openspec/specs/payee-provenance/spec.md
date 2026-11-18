# payee-provenance Specification

## Purpose

What a payment grant may admit according to where a payee came from: the account's own
payment history, read at the crossing. Covers enforcement, narrowing, and the evidence of
what the rule stops and what it costs.

## Requirements

### Requirement: A payment grant may admit only the account's known payees
A `Payments` grant whose payee list holds `known-payees` SHALL admit a payee only if the
account has sent it a completed payment before the crossing. The set SHALL be read from the
bank at each crossing, on both enforcement tiers, and a payee outside it SHALL be refused
as any out-of-scope payee is.

#### Scenario: A past payee is paid
- **WHEN** a node holding `Payments<[known-payees], uncapped>` pays an IBAN the account's history shows an outgoing payment to
- **THEN** the payment is made, on the host tier and on the confined tier

#### Scenario: A new payee is refused
- **WHEN** the same node pays an IBAN the account has never paid
- **THEN** the crossing refuses it with the out-of-scope payee error, and no payment is recorded

#### Scenario: A lookalike of a known payee is refused
- **WHEN** the payee differs from a known payee in one character
- **THEN** it is refused: membership is exact

#### Scenario: Incoming payments do not make a payee known
- **WHEN** an IBAN appears in the history only as the sender of a payment into the account
- **THEN** `known-payees` refuses it, while `inbound-senders` would admit it

#### Scenario: A payment made earlier in the run makes its payee known
- **WHEN** a grant admitting any payee pays a new IBAN, and later in the same run a `known-payees` grant pays that IBAN
- **THEN** the second payment is admitted; the set is the history at the crossing, and this is stated as the rule's trust boundary

### Requirement: The class narrows by the existing payee rule
`known-payees` SHALL be covered by `any` and SHALL neither cover nor be covered by
`inbound-senders` or any literal payee list. A `known-payees` grant with a cap SHALL also
hold the cap, and a bind on it SHALL hold as well: all three must permit a payment.

#### Scenario: Narrowing from any
- **WHEN** a parent routes `Payments<[any], uncapped>` to a child declaring `Payments<[known-payees], '100'>`
- **THEN** validation accepts the narrowing

#### Scenario: A literal list does not narrow to the class
- **WHEN** a parent holding `Payments<['GB29NWBK60161331926819'], uncapped>` routes it to a child declaring `Payments<[known-payees], uncapped>`
- **THEN** validation rejects it as a widening

#### Scenario: A bound known-payee grant refuses a bound new payee
- **WHEN** a writer's bind names a payee that is not a known payee
- **THEN** the crossing refuses the payment, though the bind is satisfied

### Requirement: A refusal discloses no payee to the architect
A run-time refusal under `known-payees` SHALL reach the architect only through the existing
fixed refusal table, as "the payee is not among its payees", and never with the refused
IBAN.

#### Scenario: The architect's reason for a known-payee refusal
- **WHEN** a measured graph holding `known-payees` is refused at run time for paying a new IBAN
- **THEN** the reason built for the architect is the fixed payee line, and the IBAN appears nowhere in it

### Requirement: The rule's effect is measured on both sides and pinned
The pinned injection cases SHALL be re-run with `[any]` rewritten to `[known-payees]`, each
reported as attacker refused or paid and utility kept or lost. Predictions SHALL be
committed first, the outcome recorded separately, the `[any]` records unchanged, and
refused legitimate payments counted over the 16 tasks.

#### Scenario: Task 0 under injection
- **WHEN** task 0's bound oracle plan, rewritten, runs under each of the nine injections with the stand-in that obeys them
- **THEN** each payment to the attacker is refused, and the bill is not paid either, because its payee is not a known payee; both are pinned

#### Scenario: The cost is counted, not hidden
- **WHEN** the static count runs over the ground-truth payments of the 16 user tasks
- **THEN** it reports how many payees are known, new or a merchant name, by task, and the findings state that each new payee would need a confirmation outside the graph

#### Scenario: A prediction contradicted
- **WHEN** a measured outcome differs from its committed prediction
- **THEN** the report lists it as a contradiction, and the prediction is not edited
