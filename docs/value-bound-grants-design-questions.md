# Value-bound grants: design questions for the author

16 November 2026. This document comes before any OpenSpec change. It takes the first item of
direction C (authority below kinds) from the vertical slice (`docs/ROADMAP.md`, "7 November
2026: what the vertical slice found"): a **grant bound to a run-time value that an upstream
node produces**, "this payee, this amount, once known", rather than a literal. It also says
which of the slice's other proposals belong in the same change. Each question has a
recommendation. Routing-point attenuation (task 9.1, `poc/attenuate.py`) now exists, and the
mechanism below is built on it.

## The case

In the slice's unit D2 (banking task 0, "pay the bill"), the developer of `PayBill`, a
`Custom` node, asked for:

    Payments<['<IBAN parsed from the bill>'], '<total due parsed from the bill>'>

The type language has no way to say that. The architect granted `Payments<[any], uncapped>`,
and every check passed it. In D1, a developer's body paid a 16-character prefix of the
bill's IBAN, and `Payments<[any], uncapped>` admitted that too. Both times the right
authority was a bound that exists only once an upstream node has run.

## What practice does

The survey asked "what should we change?", not "who should we cite?".

- **PSD2 dynamic linking** (Delegated Regulation (EU) 2018/389, Art. 5) is the production
  precedent, and it is exact. A payment's authentication code must be specific to the amount
  and the payee the payer agreed to, and any change to either invalidates it. *So:* bind
  payee **and** amount, and make the grant spent once it is used. A bound payee with an open
  amount would not meet the bank's own rule.
- **OAuth Rich Authorization Requests** (RFC 9396) carry a payment's
  `instructedAmount` and `creditorAccount` in the grant. The RFC leaves enforcement and
  single use to each type. *So:* putting a value in a grant is not enough. Enforcement at the
  crossing, and "once", must be ours.
- **Macaroons and Biscuit** let a holder add caveats or checks that only restrict. A
  Biscuit block "can only restrict what a token can do, and never extend it", and a check
  reads facts the authorizer supplies at request time. *So:* keep the static grant as the
  **upper bound**, and make the run-time value an attenuation within it. A bound can never
  widen what the type grants.
- **UCAN 1.0** puts a policy over invocation arguments in the delegation
  (`["==", ".from", "mailto:me@example.com"]`), and a re-delegation must be equal or
  narrower. *So:* a selector into a value is ordinary practice. Ours selects from the node's
  **input**, which is the value an upstream node produced, rather than from the call.
- **Progent** lets a model update its tool-argument policy during a run. An SMT check
  applies a narrowing automatically and holds an expansion for approval. The update model
  sees tool results, and the paper says those "cannot always be considered trustworthy".
  *So:* a narrowing computed from data may apply without review, but its provenance is a
  real question. That is Q2.
- **CaMeL** tags every value with its sources. Its banking policy requires a payment's
  recipient and amount "to have the user as a source", with no untrusted parent. A
  violation is blocked, or in deployment asks the user. *So:* this is the strict answer to
  Q2. It would make task 0 inexpressible without a confirmation, because the payee exists
  only in the bill.

**What no surveyed system does**, as far as the survey reached: declare the binding in an
architecture artefact that is **reviewed before anything runs**, and hold the binary's import
surface to it. The import surface does not change: a bound `Payments` grant is still the
`payments` interface. The bound narrows what that interface will do.

## What it would buy, and what it would not

It would buy three things:
1. **The holder cannot choose the value.** A bound `Payments` handle pays exactly the payee
   and amount an upstream node produced. In D2 the developer-written `PayBill` both read the
   bill and paid. Under a bind, its code could pay nothing but what the extractor returned.
2. **Authority splits from the choice.** An inference-only `Extract` picks the payee and
   holds no authority. The writer holds authority and picks nothing. That is CaMeL's
   separation of data and control, on a graph.
3. **An escalation can be answered narrowly.** D2's request becomes expressible, so the
   architect has a narrower option than `[any], uncapped`.

It would not do two things:
- **It would not have caught D1.** There the developer-written node was the *extractor*
  (`ParseBill`), and a library `SendMoney` held the grant. A bind on `SendMoney` reads
  `ParseBill`'s output, which is the truncated IBAN. A bind moves trust to the producer of
  the value, and it cannot tell that the value is wrong. Only a contract or a value check
  catches that. That is the roadmap's "contracts are not optional", and it is out of this
  change (Q5).
- **It would not close injection.** If the bill names the attacker's IBAN, the extractor
  returns it, and the bound handle pays it. This is the free-text residual again, on a new
  field.

Tests should pin both cases as **succeeding**, as the feed corpus pins its residual cases.

## Questions

**Q1. How is a value-bound grant spelled?**
- *Recommended: a `bind` annotation beside the grant.* The type string stays the static
  upper bound, and the node adds:

      "bind": {"Payments<[any], '2000'>": {"payee": "in0.iban", "amount": "in0.total", "uses": 1}}

  Paths are the `inN.field` paths the library's `Compose` already uses. The grammar,
  `is_assignable`, the WIT and the derivation do not change, so neither Paper 2's frozen
  vocabulary nor its figures can move. The canonical rendering the reviewers see prints it
  as one line: `Payments<[any], '2000'> bound payee=in0.iban, amount=in0.total, once`.
- *Alternative: in the type*, as `Payments<[in0.iban], in0.total, once>`. The reviewer reads
  one string, but the type depends on the node's inputs. That changes the grammar,
  narrowing, and a graph parameter's meaning, because a parameter has no inputs.
- *Alternative: name the producer*, such as `ExtractBill.iban`. This needs a new kind of
  reference across the graph. The value would reach the holder by a route that is not an
  edge.

**Q2. May the bound value come from untrusted data?**
- *Recommended: yes, and its provenance is computed and shown.* The validator labels each
  bind `trusted` or `untrusted`, from the trust label of the input it reads. The label
  appears in the rendering, in the behaviour view, and on the review page. Requiring trust
  would make task 0 inexpressible. It would also be nominal here, because discharge is a
  declaration: `Extract` may discharge.
- *Alternative: CaMeL's rule.* A writer's bound must come from the trusted task request.
  This is strict and simple, and it costs every task whose payee is in a document.
- *Option, with either:* a `trusted` modifier on a bind, which the validator enforces. The
  architect can then claim the stronger form where it holds, and the reviewer can see when it
  was not claimed.

**Q3. How is it checked and enforced?**

These are mechanics, not a decision. They are listed here so the cost is visible.
- **The validator** (structural, dependency-free) checks four things. A bind names a grant
  the node holds, of a bindable kind. Each path names a *data* input, never a capability.
  `uses` is a positive integer. The trust label is computed. The library check (`poc/agentdojo/library.py`), which knows the
  record schemas, checks that each field exists with the right type: a string for a payee,
  a number for an amount. The validator knows types by name only, not by fields, and the
  design says so.
- **Enforcement** happens at node activation. Before the holder runs, the runtime resolves
  the paths against the node's inputs and wraps the handle in a facade from
  `poc/attenuate.py`. The facade's scope is the bound value, and its `uses` counter is spent
  by each successful call. The handle checks its own static scope and the bound through
  `within`, so the bound can only narrow. The facade lives for one activation. With
  `each: true`, every item gets its own facade.
- **Both tiers.** The confined adapter calls the same handle (`poc/agentdojo/confined.py`),
  so the confined tier enforces the bound behind the component's `payments` import, and the
  component cannot see the bound. On the host tier the facade is host discipline, as every
  handle is.
- **A missing or ill-typed path at run time fails the run**, as a missing `Compose` path
  does now. A bind never falls back to the static bound.

**Q4. Which kinds are bindable first?**
- *Recommended: `Payments` only* (payee, amount, uses), in both modes. It is the case the
  slice found twice, and the mechanism generalises: a bind substitutes a value into the
  kind's scope.
- *Alternatives:* add `ScheduledPayments` (an order bound by subject), or `HTTPClient` (a host
  taken from a URL a feed produced, for the feed-triage service). Both are cheap once
  `Payments` exists. Neither has a case from the slice yet.

**Q5. Which of the slice's other proposals go in the same change?**
- *Recommended, in:* **a `Custom` node never holds an unbounded writer grant.** This is a
  formal-review rule. A writer grant on a `Custom` node must have a literal payee set and a
  cap, or a bind of both payee and amount. It is what makes the bind matter: without it, the
  architect can still grant D2's `[any], uncapped`. The rule is cheap, and the slice's
  records can replay it (D2's final graph fails it).
- *Recommended, in:* **an accepted escalation grants no more than was asked.** This is a
  formal check on an escalation's edit. Every grant the edit adds or widens must be
  assignable to the request: `is_assignable(granted, requested)`, with a bound request
  satisfied only by an equal or narrower bind. Anything wider goes back for review. It needs
  Q1, because D2's request was not expressible until then, so the developer's request format
  gains `bind`.
- *Recommended, in, but on the human page only:* **a placement verdict**, "who holds it".
  It is added to the review page and the verdict file's scale (`needed / wider / not-needed`,
  plus `misplaced`), so the author's pending verdicts (slice task 4.3) can use it. The
  registered reviewer's prompt and scale stay untouched. They are pinned by hash, and Paper
  4 reports them.
- *Out:* **contracts at step 5** (the roadmap's "contracts are not optional"). It is a
  separate change with its own question: who writes the contract for a `Custom` node.

## Evidence the change would produce

All of it is deterministic, on the subscription or with no model at all:
- **D2's shape, enforced.** A `Custom` holder with the bound grant, and a hand-written body
  that pays a payee or amount other than the bound one, on both tiers. The pins: the crossing
  refuses it, and a second payment is refused under `uses: 1`.
- **D1 replayed, as a limit.** The committed wrong-account body, with `SendMoney` bound to
  `ParseBill`'s output. The pin: the truncated IBAN is still paid.
- **The injection residual.** An oracle graph for task 0 with the bound grant, run against
  AgentDojo's injections into the bill. The pin: a payee the injection controls is still
  paid. The bound does not defend this, and the report says so.
- **The rules replayed** over the slice's records. D2's final graph fails the `Custom`
  rule. D2's escalation decision fails the no-wider check.
- **Optional, the slice's escalation re-run once** with `bind` offered to the developer and
  the architect, on the subscription. This is exploratory and unregistered, like the slice.

## What does not move

- The architect's registered catalogue (`CATALOGUE`) is hashed by Paper 4's registration.
  `bind` is offered only through `SLICE_CATALOGUE` and its successors.
- `type_parser`'s grammar and `is_assignable` are unchanged under Q1's recommendation, so
  Paper 2's figure pin and the generation registration's `caps.wit` hash stay green without
  re-seeding.
- No paper is edited. This is evidence for the back half, which is likely Paper 5.
