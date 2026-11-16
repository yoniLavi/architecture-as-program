# Value-bound grants: "this payee, this amount, once known"

> **Status: approved by the author, 16 November 2026** (task 0.1; every recommendation
> taken, including the three open questions in `design.md`). The author settled the four design questions on
> 16 November 2026 (`docs/value-bound-grants-design-questions.md`). Each took the
> recommendation, and `design.md` records them.

## Why

The vertical slice found the same gap twice (`docs/ROADMAP.md`, 7 November 2026). The
right authority was a payee and an amount known only once an upstream node has run, and
the type language can name only literals or `any`. In D2 a developer asked for
`Payments<['<IBAN parsed from the bill>'], '<total due…>'>`. The architect granted
`Payments<[any], uncapped>` to developer-written code, and every check passed it. The
grant is common. Measured at `ce74992` over the slice and the registered records:
- 305 registered architect graphs hold 192 `Payments` grants;
- 49 of those are `[any], uncapped`, 104 name literal payees but are uncapped, and 39 are
  capped;
- in the slice, the one writer grant a `Custom` node held (D2) is `[any], uncapped`.

Routing-point attenuation (`poc/attenuate.py`, task 9.1 of
`build-feed-triage-and-generation-experiment`) now gives a narrowed handle that every tier
enforces. That is the mechanism a run-time bound needs.

## What Changes

- **A `bind` annotation on a node** narrows a `Payments` grant it holds to a payee and an
  amount read from the node's own data inputs (`inN.field` paths), and to a number of uses.
  The grant's type stays the static upper bound. A bind only narrows it.
- **The validator checks a bind structurally.** It names a held `Payments` grant, its paths
  name data inputs, and `uses` is a positive integer. It also computes each bind's **trust
  label** from the input it reads. Untrusted sources are allowed, and the label is shown. An
  optional `trusted` modifier, when claimed, is enforced. The node library checks the
  fields' types against its record schemas.
- **The runtime enforces a bind at node activation** with a facade over the routed handle.
  The facade's scope is the bound value, and its use counter is spent by each successful
  call. It works on both tiers, and the WIT import surface does not change. A path that does
  not resolve fails the run, and nothing falls back to the static bound.
- **The rendering the reviewers and the human page see** prints a bind beside its grant,
  with its trust label.
- **Formal rule: a `Custom` node never holds an unbounded writer grant.** A writer grant on a
  `Custom` node needs a literal payee set and a cap, or a bind of both payee and amount.
- **Formal check: an accepted escalation grants no more than was asked.** The developer's
  request may carry a `bind`. Every grant the architect's edit adds or widens must be
  assignable to the request, and a bound request is met only by an equal or narrower bind.
  A wider edit goes back for review.
- **A placement verdict on the human review page**: `misplaced` (needed, but held by the
  wrong node) joins `needed / wider / not-needed` in the verdict file's scale. This lets the
  author's pending slice verdicts (`add-vertical-slice` task 4.3) use it.
- **Evidence, pinned by tests:**
  - a body holding a bound grant that pays another payee or amount, or pays twice, is
    refused at the crossing on both tiers;
  - D1's wrong-account body is **still paid** when the writer is bound to its extractor's
    output (a limit);
  - an injected payee in the bill is **still paid** (the residual);
  - D2's final graph fails the `Custom` rule, and D2's escalation decision fails the
    no-wider check.

**Not in this change:**
- bindable kinds other than `Payments` (`ScheduledPayments` and `HTTPClient` are later
  candidates);
- contracts for `Custom` nodes at step 5, which need their own change;
- any change to the type grammar, `is_assignable`, `caps.wit`, `banking.wit`, or the
  derivation;
- any change to the registered architect's catalogue, prompts or reviewer scale (Paper 4's
  registration pins them);
- any paper edit, including Paper 2 v1.1 (task 9.2 of the feed-triage change), which still
  awaits the author's go;
- a registered experiment, and any paid spend.

## Capabilities

### New Capabilities
- `value-bound-grants`: grants narrowed at run time to values an upstream node produced.
  This covers how a bind is declared, checked, labelled for trust, rendered, and enforced on
  both tiers.

### Modified Capabilities
- `architect-pipeline`: gains two formal-review rules (a `Custom` node holds no unbounded
  writer grant, and an accepted escalation is no wider than its request) and a placement
  verdict on the human review page.

## Impact

- **Code:**
  - `scripts/graph_validator.py`: structural bind checks and trust labels, stdlib-only;
  - `poc/attenuate.py`: a bound facade with a use counter;
  - `poc/runtime.py`: binding at node activation;
  - `poc/agentdojo/library.py`: field-type checks and the bind in the slice catalogue;
  - `poc/architect/formal.py`: the two rules;
  - `poc/slice/` (`developer.py`, `escalate.py`, `behaviour.py`, `page.py`): the request
    format, the rendering, and the placement verdict.
  - `graphs/schema.json` is untouched: no canonical graph uses a bind, and library graphs
    are not validated against it.
- **Tests:** new files for binds, the bound facade and the two rules. Paper 2's figure pin
  (`tests/test_paper2_figures_pinned.py`), Paper 3's generation pins and Paper 4's
  architect pins stay green without re-seeding.
- **Usage:** none required. An optional single re-run of the slice's escalation on the
  subscription, if the author wants it (design, open question).
