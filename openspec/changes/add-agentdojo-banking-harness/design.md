# Design

## Context

Read `docs/agentdojo-spike.md` first. Its graphs are in `docs/agentdojo-spike/`. Its
measurement recipe ("Measuring attack success on a graph") is followed here unchanged:
1. a `BasePipelineElement` modelled on `ground_truth_pipeline.py`;
2. handles backed by `FunctionsRuntime.run_function`, with scope checked first;
3. AgentDojo's own `run_task_with_pipeline` and `security()` predicate.

## The pin, re-checked (task 0.2, 29 October 2026)

Installed from the `agentdojo` group at `089ed468`. The spike's paths hold: `UserTask0`, `1`
and `15` at `v1/banking/user_tasks.py:16`, `56` and `516`; the eleven tools at
`v1/banking/task_suite.py:23`; `GroundTruthPipeline.query` at `ground_truth_pipeline.py:20`;
the security result at `task_suite.py:412–420`; injection candidates at
`attacks/base_attacks.py:49`.

- **The measured suite is `v1.2.2`**, the newest the pin registers. Its banking user tasks
  come from `v1` except task 6 (`v1_2_2`) and task 15 (`v1_1_1`, the prompt the spike
  used); its injection tasks come from `v1_2` except goal 7 (`v1`). So the spike's line
  numbers for goals 5 and 6 (`v1/…/injection_tasks.py:241`, `276`) are the `v1` wording;
  the measured predicates are `v1_2`'s.
- **Each user task exposes exactly one vector** under the ground-truth run: the bill text
  (task 0), the landlord's notice (2, 12), the address-change file (13), and the incoming
  transaction's subject (the other twelve). So the suite has 16 × 9 = 144 pairs, one vector
  each.
- `security` in `run_task_with_pipeline`'s result is **true when the injection goal was
  met**: it is the goal's own predicate. Reports name it "attack success", never "security".

## Decision 1: architects compose a library; they do not write code

The front half (Paper 4) has no developers, but an architect's graph still needs node bodies
to run. The architect therefore composes from a fixed **node library**:
- one generic node per banking tool operation, parameterised (for example `SendMoney` with
  its arguments wired from upstream);
- deterministic selectors, such as "the transaction whose subject matches";
- inference-only extraction nodes (`LLMClient<inference>`), which emit a closed schema.

This mirrors CaMeL, whose planner writes restricted code over a fixed tool set; our planner
writes a graph over a fixed node set. Code generation stays with the back half, where
Paper 3's harness already lives.

Each library node is built **once** as a confined component, so an architect's graph still
determines every component's import surface, and the derivation gate applies unchanged. If
building the library components proves too costly, the fallback is the host tier with
host-side scope checks (as the HTTP allowlist is checked now), and Paper 4's claim narrows
to say so. That fallback is decided only after task 3.4's timebox, and recorded.

## Decision 2: the banking kinds narrow on arguments

From the spike: a handle's kind is coarser than banking's threats, so the scope lives in the
handle and is checked at the crossing.
- `Payments<[payees], cap>` refuses a payee off its list or an amount over the cap;
- `ScheduledPayments` narrows by which orders, and by which fields may change;
- `UserProfile<[fields]>` narrows by field set;
- `Credentials` exists so that `update_password` has a kind *no graph is granted*. A grant of
  it is a pinned validator rejection.

Narrowing at composition is by set inclusion and cap ≤ cap. It is checked at validation, and,
as for the HTTP allowlist, not enforced across a routed sub-graph. That gap belongs to C, and
the front half does not need it.

`Payments<[inbound-senders], …>`, whose payee set is read from the environment, is the
spike's hard case. It is modelled as a handle that consults the environment host-side, and the
paper states it as a dynamic scope.

**As built (tasks 1.1–1.3).** Each scope is parsed once, in `type_parser`, and the
validator, the handle and the WIT mapping all read that one parse. Five choices the
author may want to revisit:
- **Payees** are string literals (an IBAN, or a name such as `'Spotify'`, which tasks 5
  and 11 pay), or the dynamic sets `inbound-senders` and `any`. `any` exists because task 0's
  payee appears only in the bill, so without it task 0 cannot be expressed at all. It is the
  widest grant, and the reviewers should treat it so.
- **The cap** is a decimal string, or `uncapped`. Task 0's amount is also known only from
  the bill.
- **Standing orders.** `schedule_transaction` (task 6) is `Payments<[payees], cap, recurring>`,
  a second mode of `Payments` with its own interface. The alternative was a fifth kind. The
  two modes are incomparable, as `DBHandle`'s `read` and `append` are, so a grant to send
  once never schedules and the reverse.
- **Orders are named by subject**, compared case-insensitively. The handle looks the order up
  by id and checks *its* subject, so a node cannot reach another order by naming its id.
- **Reads use the existing `DBHandle<scope, read>`**, bound to the bank when the world has
  one: `'transactions'`, `'scheduled-transactions'`, `'balance'`, `'iban'`, `'user-info'`
  (which never returns the password), and `'file:<path>'` for one file. No new read kind.

A banking type whose scope does not parse is a validator rejection (`unreadable scope`),
not a provisioning surprise. The pinned cases live in `poc/agentdojo/corpus.py`, apart
from Paper 2's corpus, so no Paper 2 figure can move.

## Decision 3: exclusive-branch merge

The spike's task 2 needs a value from either of two exclusive branches. The positional join
rejects this by design. Two options:
- (a) a **merge node**, valid only over branches the validator proves exclusive, which
  passes whichever value arrived;
- (b) restructure such tasks so the branch happens inside one node.

**Recommendation: (a).** It is small, checkable, and the order-insensitive case of the
merge-order rule recorded in `docs/PRIOR-ART.md` §7: exactly one input can arrive, so no
order needs recording. It is pinned by corpus cases: one where the branches are exclusive and
it is accepted, one where they are not and it is rejected.

## Decision 4: the baseline

An undefended tool-calling agent on the same Claude models, over the banking suite, is the
comparison Paper 4 most needs. Two routes, time-boxed to one session together:
- **`claude -p` with an MCP server** exposing the banking `FunctionsRuntime` as tools. This
  is native tool calling, on the subscription, with no new harness to trust. Its cost is the
  CLI's own loop, which needs scrubbing exactly as `ClaudeCLIBackend` is scrubbed (no
  filesystem, no session persistence), plus an MCP server we write.
- **pi**, an existing customisable agent harness the author suggested. Check what its current
  version actually offers before assuming anything, and how it reaches Claude on the
  subscription.

Choose on three criteria: subscription billing, fidelity to AgentDojo's tool-calling
pipeline, and the size of the trusted harness. The choice is recorded in this file.
AgentDojo's pipeline must see the same tool results either way.

## Decision 5: predictions before measurement

For each task–injection pair, the static prediction from the spike's recipe (vector → node
that receives it → reachable handles) is computed by a script from a graph and committed as a
file *before* that graph's measured run. Oracle graphs get predictions too, so the method is
exercised before the architect's graphs exist. AgentDojo scores only its nine goals, so a 0%
attack-success rate is never reported as "no residual".

## Risks

- **AgentDojo's dependencies.** It stays in its own group, and a test checks that no Paper 2
  or `scripts/` import reaches it.
- **Library components cost Rust work.** That is the timebox of Decision 1.
- **The CLI loop is not an API.** Rate limits and the usage ceiling apply, so baseline runs
  resume, as the generation harness's do.
