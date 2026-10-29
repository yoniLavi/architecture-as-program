# Design

## Context

Read `docs/agentdojo-spike.md` first. Its graphs are in `docs/agentdojo-spike/`. Its
measurement recipe ("Measuring attack success on a graph") is followed here unchanged:
1. a `BasePipelineElement` modelled on `ground_truth_pipeline.py`;
2. handles backed by `FunctionsRuntime.run_function`, with scope checked first;
3. AgentDojo's own `run_task_with_pipeline` and `security()` predicate.

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
