# Tasks

Each session first checks the feed recorder (`strengthen-generation-evidence` 0.3) and
`git status`. Everything long-running runs at low priority (`poc/polite.py`).

## 0. Setup

- [x] 0.1 Add the `agentdojo` dependency group, pinned at commit `089ed468…`. Add a test that
      no module under `scripts/`, and nothing `poc/evaluate.py` imports, can import it
- [x] 0.2 Read `docs/agentdojo-spike.md` and its three graphs, and re-check the pin's banking
      paths (`task_suite.py`, `user_tasks.py`, `injection_tasks.py`,
      `ground_truth_pipeline.py`)

## 1. Banking kinds (full vocabulary only)

- [x] 1.1 `Payments<[payees], cap>`, `ScheduledPayments<…>`, `UserProfile<[fields]>` and
      `Credentials` in the type parser, `CAPABILITY_HEADS`, `caps.wit` and `interfaces.py`.
      None goes in `PAPER2_*`, and `tests/test_paper2_figures_pinned.py` stays green
- [x] 1.2 Narrowing at composition: set inclusion and cap ≤ cap. A grant of `Credentials` is a
      validator rejection, pinned as a corpus case
- [x] 1.3 Handles check scope at the crossing: an off-list payee or an over-cap amount is
      refused like an off-allowlist request. Tests for each refusal

## 2. Adapter and pipeline element

- [x] 2.1 Handles backed by AgentDojo's `FunctionsRuntime.run_function`, with scope checked
      first
- [x] 2.2 A graph-backed `BasePipelineElement`, modelled on `ground_truth_pipeline.py`, that
      ends with a final assistant message. Scoring stays AgentDojo's own
- [x] 2.3 The exclusive-branch merge node (design, Decision 3), with two corpus cases pinned:
      accepted when the branches are exclusive, rejected when they are not

## 3. The node library

- [x] 3.1 The library's catalogue as data: one generic node per banking tool operation,
      deterministic selectors, and inference-only extraction nodes with closed output schemas
- [x] 3.2 Host-side implementations, with tests
- [x] 3.3 The spike's three graphs rewritten over the library. They run through the harness,
      and AgentDojo scores them. Reported as **oracle plans** only
- [x] 3.4 Confined components for the library, time-boxed to one session. Each is held to its
      clause by the derivation gate. If the timebox fails, record the fallback (host tier,
      host-side scope) in `design.md`, and the narrower claim it implies

## 4. The baseline (same model, undefended)

- [ ] 4.1 A spike, time-boxed: `claude -p` plus an MCP server exposing the banking tools, or
      pi. Choose by the design's three criteria, and record the choice in `design.md`
- [ ] 4.2 Build the chosen route. It is scrubbed like `ClaudeCLIBackend`, resumes after the
      usage ceiling, and records the model ID each call resolved to
- [ ] 4.3 Run the baseline over the banking suite, for utility and attack success, on the
      subscription only. Commit the records. Write the report to
      `dist/agentdojo-banking.{md,json}`, rendered from committed records. The build calls no
      model

## 5. Predictions

- [ ] 5.1 A script that derives each task–injection pair's static prediction (impossible,
      bounded or residual) from a graph
- [ ] 5.2 Predictions for the oracle graphs, committed. The format is the one the architect's
      graphs will use

## 6. Records

- [ ] 6.1 `AGENTS.md`, `docs/ROADMAP.md`, and spec deltas reconciled; then
      `openspec validate --strict`
