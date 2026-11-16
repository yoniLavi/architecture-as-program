# Design

## Context

The motivation is in `proposal.md`, and the survey and the full questions are in
`docs/value-bound-grants-design-questions.md`. Five facts about the code shape the approach:

- **Scopes are parsed once.** `type_parser.payments_scope` parses a `Payments` scope into a
  `PaymentsScope` (literal payees, dynamic sets `any` and `inbound-senders`, a cap, a mode).
  The validator's narrowing rule, the handle's check and the WIT mapping all read it.
- **A handle checks its own scope and each bound passed in `within`.** `PaymentsHandle.send`
  does this in `poc/bank.py`. Routing-point facades (`poc/attenuate.py`) narrow a handle by
  adding a bound to `within`, so nested narrowing composes.
- **Both tiers call the same handle.** The host-tier library body calls `handle.send`
  (`poc/agentdojo/library.py`). So does the confined adapter, behind the component's
  `payments` import (`poc/agentdojo/confined.py`). A facade therefore holds on both tiers.
- **Paths already exist.** `inN.field` paths and their resolver are the library's
  (`library.resolve`), and `Compose` uses them.
- **The registered architect run hashes things this change must not touch**: its catalogue
  (`CATALOGUE`), the reviewer's prompt and scale, the labels. The slice composes from
  `SLICE_CATALOGUE`, which is not hashed.

## Goals / Non-Goals

**Goals:**
- Make D2's request expressible, checkable before the run, and enforced at the crossing.
- Give the formal review two rules that the slice showed were missing, and give the human
  page the verdict that the judges lacked.
- Pin the bind's limits as limits.

**Non-Goals:**
- A dependent type language. The bind is an attenuation beside the type, not part of it.
- Choosing the bound value safely. The bind moves trust to the value's producer. Whether
  that producer is right is the job of contracts, a later change.
- Re-running or re-scoring any registered result.

## Decisions

The author's answers of 16 November 2026, each the recommendation:

**D1. Spelling: a `bind` annotation beside the grant.**

    "bind": {"Payments<[any], '2000'>": {"payee": "in0.iban", "amount": "in0.total", "uses": 1}}

A bind may also carry `"trusted": true` (D2). The key is the grant's type string exactly as
it appears in the node's inputs. Every field is optional except `uses`, so a payee-only bind
is expressible. The `Custom` rule (D5) then decides whether a payee-only bind suffices on
developer code; it does not.
- *Rejected:* the bound in the type (`Payments<[in0.iban], in0.total, once>`). It would make
  types depend on node inputs, change the grammar and `is_assignable`, and give a graph
  parameter a meaning it cannot have.
- *Rejected:* naming the producer node (`ExtractBill.iban`). The value would reach the
  holder by a route that is not an edge.

**D2. Trust: untrusted sources are allowed, and labelled; `trusted` is enforced where
claimed.**
- The label is `untrusted` if any input a path reads is `Untrusted<_>`, including through a
  sum variant. This uses the same per-variant reading that closed `launder_trust_via_variant`.
- CaMeL's rule, requiring trusted sources only, was rejected, because it makes every task
  whose payee is in a document inexpressible.
- "Trusted" here means the label of the input. Discharge in this artifact is declared
  (`Extract` may discharge), so a `trusted` bind fed by an `Extract` that discharged trust is
  trusted only nominally. The rendering shows the discharging node, so a reviewer can see
  this. The design says so, and no paper may claim more.

**D3. Bindable kinds: `Payments` only**, in both send and recurring modes. A table maps
each bindable kind to its fields: `Payments` → `payee` (string), `amount` (number),
`uses`. Adding `ScheduledPayments` or `HTTPClient` later is one entry in the table and one
facade.

**D4. Enforcement: a bound facade, built at activation.**
- Before a node with a bind runs, the runtime resolves each path against that activation's
  input values.
- It then builds a `PaymentsScope` with `literal = {payee}`, no dynamic set, and
  `cap = amount`. With no payee bound, the static payees are kept; with no amount bound, the
  static cap is kept.
- It wraps the routed handle in a facade (`BoundPaymentsFacade`) that passes that scope down
  as `within`.
- The facade counts uses. A call refused by a scope check (`CapabilityError`) or by the bank
  (`BankError`) spends none.
- **The bound amount is a cap, and the amount the node passes is checked against it.** An
  amount *equal* to the bound one would be the stricter reading. PSD2 dynamic linking
  requires that exactness. The cap form is chosen because a bound total may be paid in
  parts under `uses` > 1. With `uses: 1`, the two readings differ only by an underpayment.
  The author may prefer exactness (open question 2).
- **The facade lives for one activation.** A per-item map gets one per item.
- **Ordering with routing-point attenuation:** the facade sits outermost. It wraps whatever
  `_route_handles` produced, so a sub-graph's narrowing and a bind compose through `within`.
- **On the confined tier** the adapter calls the facade. The component cannot see the bound
  and cannot address anything behind it.

**D5. The `Custom` rule lives in the formal review** (`poc/architect/formal.py`) as a
separate function, run by the slice and its successors. It is not added to the registered
run's review, whose outputs are pinned. Its test: "writer grant" means `Payments`
(either mode), `ScheduledPayments` or `UserProfile`. The rule as approved names `Payments`
only, so a `Custom` node holding `ScheduledPayments` or `UserProfile` is reported, not
failed. The design flags this gap rather than widening the rule unasked (open question 3).

**D6. The no-wider check is a function of the request and the edit.**
- `changed_grants(before, after)` already lists what the edit added or changed
  (`poc/slice/escalate.py`). For each such grant, the check requires
  `is_assignable(requested, granted)`, meaning the granted type is no wider.
- Where the request carries a bind, the granted grant must carry one with the same paths, or
  a subset of the request's fields bound to the same paths, and no more uses.
- The developer's request format becomes `{"escalate": {"capability", "bind"?, "because"}}`.
  The prompt that offers it is the slice's, not the registered generation run's.
- A request that does not parse fails the check closed. It never passes as "no request".

**D7. The placement verdict changes the human page and the verdict file only.**
- `poc/slice/page.py` gains `misplaced` in its scale text.
- The verdict file schema accepts it.
- Verdict files already written are not rewritten, because they are written once. The
  author's are still unfilled.
- The judges' records keep the scale they used.

## Risks / Trade-offs

- [A bind reads as a defence against injection] → The residual and D1 cases are pinned as
  *succeeding* tests (spec: "The limits of a bind are pinned as limits"). The rendering
  labels every untrusted bind.
- [A bind on a library writer moves the trust question rather than answering it] → This is
  stated in Non-Goals and in the design-question document. Contracts are the next change.
- [Touching `poc/architect/` moves a Paper 4 pin] → The new rules are new functions. No
  registered code path calls them. Paper 4's pinned tests (`make architect`) must stay
  green, and they are run in the close phase.
- [A use counter is state on the host tier, and a hostile host-tier body can reach around
  it] → This is host discipline, as every host-tier handle is. The confined tier is where it
  is enforced, and the tests say which tier each one runs on.
- [`trusted` is nominal after a declared discharge] → Disclosed in D2. The rendering names
  the discharging node.

## Migration Plan

Additive. A graph without a bind behaves exactly as before. Nothing is pushed or published.

## Open Questions

**Answered by the author, 16 November 2026 (task 0.1): every recommendation taken.** D2's
escalation is re-run once (task 5.3); the bound amount is a cap; the `Custom` rule fails
`Payments` only and reports `ScheduledPayments` and `UserProfile`.

The questions as put:
1. **Re-run the slice's escalation once**, with `bind` offered to the developer and the
   architect, on the subscription: Haiku, a handful of calls, exploratory and unregistered.
   Or leave the evidence fully deterministic? *Recommended: one re-run of D2's escalation.*
   It is the only evidence of whether the architect *uses* a narrower option once one exists.
2. **Bound amount: a cap or exact?** *Recommended: a cap* (D4). Exact is PSD2's rule, and is
   a one-line change if preferred.
3. **The `Custom` rule's reach.** As approved, it covers `Payments` only. Should it also fail
   a `Custom` node holding `ScheduledPayments` or `UserProfile` with no narrowing?
   *Recommended: report only in this change,* and decide when those kinds become bindable.
