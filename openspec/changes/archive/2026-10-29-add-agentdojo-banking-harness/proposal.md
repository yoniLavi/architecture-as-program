# Run signal graphs on AgentDojo's banking suite, with a same-model baseline

> **Status:** written 29 October 2026. The design decisions came from the author the same day
> (`docs/paper-4-design-questions.md`, D1–D9), and the author asked for implementation in a
> new session. This is the first of two changes for Paper 4. The second is
> `add-architect-and-reviewers`, which depends on this one.

## Why

Paper 4 evaluates an architect model that writes signal graphs from AgentDojo's prompts.
Nothing in the repository can run a graph against AgentDojo yet. The spike
(`docs/agentdojo-spike.md`) found that the banking suite expresses as graphs. A benchmark
needs four things the spike listed:
- capability kinds narrow enough for banking's threats;
- an adapter from those handles to AgentDojo's tools;
- a pipeline element that runs a graph inside AgentDojo's scorer;
- a fix for one missing construct, the merge of exclusive branches.

It also needs a baseline on the same model, which the earlier no-paid-API rule ruled out. The
author has since relaxed that rule, but the subscription comes first.

## What Changes

- **AgentDojo, pinned and isolated.** Commit `089ed468…` (the spike's) goes in its own
  dependency group, never imported by `scripts/` or the evaluation Paper 2 typesets.
- **Banking capability kinds, full vocabulary only:**
  - `Payments<[payees], cap>`, which narrows by payee set and amount cap;
  - `ScheduledPayments<…>`;
  - `UserProfile<[fields]>`;
  - `Credentials`, a kind that is never granted.

  Each kind gets its WIT interface, its derivation in `interfaces.py`, and narrowing rules in
  the validator. None of them goes in the `PAPER2_*` sets.
- **A node library**, with one generic node per banking tool operation, plus inference-only
  extraction nodes. Each is built once as a confined component. An architect composes from
  the library and writes wiring and parameters, never code. Writing code is the back half's
  job, Paper 5's.
- **The adapter and the pipeline element.** Handles are backed by `FunctionsRuntime`, with
  scope checked host-side before each call. A `BasePipelineElement` runs `assemble`/`execute`
  and leaves scoring to AgentDojo's unchanged scorer.
- **Exclusive-branch merge**, or an accepted workaround, decided in `design.md`.
- **A check of the harness on oracle graphs.** The spike's three hand-written graphs run
  through the harness and AgentDojo's scorer, and are reported as *oracle plans*, never as a
  benchmark result.
- **A same-model, undefended baseline on the subscription.** A tool-calling agent runs on
  Claude over the banking suite, for utility and attack success. Two routes are compared in a
  time-boxed spike: `claude -p` with the banking tools exposed by an MCP server, or an
  existing harness (pi, which the author suggested). The one chosen is recorded with its
  reasons.
- **Static predictions per task–injection pair**: impossible, bounded or residual, as the
  hostile-feed corpus does. They are committed before any measured run on a graph.

**Not in this change:** the architect, the reviewers, the registration and Paper 4's prose
(`add-architect-and-reviewers`). Any paid API.

## Impact

- **Specs:** a new `agentdojo-evaluation` capability.
- **Code:**
  - `poc/agentdojo/`: the adapter, the pipeline element, the node library's host side, and
    the baseline;
  - `poc/sandbox/wit/caps.wit` and `interfaces.py`: the banking kinds, full vocabulary only;
  - `scripts/graph_validator.py` and `type_parser.py`: narrowing for the new kinds;
  - `poc/sandbox/rust/`: library components;
  - `pyproject.toml`: a new `agentdojo` dependency group.
- **Paper 2 is unchanged.** `tests/test_paper2_figures_pinned.py` stays green. The banking
  kinds never enter `PAPER2_KINDS`.
- **Cost:** subscription only. The baseline is 16 utility runs plus 144 task–injection pairs
  per repetition, at low priority, resumable.
