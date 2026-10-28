# Tasks

Each phase ends green (`make build`) and committed.

**Order matters.** The long trial run (1.7) imports the working tree from child processes, so
nothing under `poc/`, `scripts/`, `graphs/` or `poc/sandbox/wit/` may be edited while it runs. All
code is therefore written and committed first (phases 0–3), and the run happens after, when the
only remaining work (phase 4, and records) touches none of those. A session that must edit code
mid-run stops the run first; it resumes from its recorded trials.

**Every session that works on this change** starts the recorder first (0.3), and checks
`git status` and the run's progress before anything else.

## 0. Running politely, and the recorder

- [x] 0.1 The harness lowers its own priority on start (`os.nice(19)`; `taskpolicy -b -p <pid>` on
      macOS where available), so `claude -p`, `cargo`, `wasm-tools` and the check process inherit
      it; `--no-nice` for an idle machine; default `--jobs 2`; cargo invoked with `-j 2`. Tests
      that the priority is applied and that the flag disables it
- [x] 0.2 `poc/feeds/archive.py --record [--every INTERVAL]`: raw bodies under
      `var/archive/<UTC timestamp>/`, through the service's own `HTTPClient` handle and allowlist,
      with an index of every tick (time, feed, status, size); no model call, no parsing; a lock
      file refuses a second recorder; low priority as in 0.1; tests against the fixture server
- [x] 0.3 Start the recorder in the background (`--every 1h`) and leave it running for the
      session. Repeat at the start of every later session; the gaps between sessions are gaps in
      the archive, and are reported as such. First started 27 October 2026, 18:32 UTC:
      `uv run --group poc python -m poc.feeds.archive --record --every 1h >> var/archive-recorder.log 2>&1`
      (it lowers its own priority). **A recurring step, not a one-off: check it each session**

## 1. A pre-registered replication

- [x] 1.1 Arms as data: pretexts in `poc/generation/prompts/`, one file each, P1–P6; P2 and P5
      byte-identical to the existing adversarial and authorised pretexts (tested)
- [x] 1.2 The rule-withheld variant of the task template; test that it differs from the stated
      variant in that sentence and nowhere else
- [x] 1.3 `poc/generation/registration.json`: pretexts, cells (15 nodes × 3 Claude models × P0–P6
      rule-stated, plus P0, P2, P5 rule-withheld; N = 5; **2,250 trials, repeats included**),
      models by full ID, the 150 task hashes, the primary outcome (first-attempt reach), the
      confirmatory test (Fisher exact, P5 vs P0), the secondary outcomes, the exclusion, voiding
      and early-stop rules. A test regenerates the hashes and holds them to the file
- [x] 1.4 The harness refuses a registered run unless the registration is committed and unmodified
      at `HEAD`; refuses a trial whose task hash, or resolved model ID, is not the registered
      one; refuses to start a trial while `poc/`, `scripts/`, `graphs/` or the WIT differ from
      `HEAD` (its own records excepted); runs the hand-written control first and refuses unless
      it passes. Each trial records the registration commit and `HEAD`. Tests for each refusal
- [x] 1.4a **Author approves the pretext texts and the registration before 1.6.** It cannot be
      corrected once trials have run, only disclosed. **Approved by the author, 27 October 2026,
      as committed in `96822ee`** (no wording changed), with two caveats stated on the ladder:
      P1 → P3 adds an authority claim ("approved", "grant is being extended"), not only a
      claimant; P4 → P5 bundles "the graph will catch up" with "treat it as granted", because
      P5 must stay byte-identical to the post-hoc arm
- [x] 1.5 Report: the registered run in its own section, the primary outcome per pretext and per
      model, the earlier trials (including the post-hoc arm) beside it and labelled, the
      registration commit named; the report refuses to pool them; timings labelled as taken at
      low priority

## 2. Differential testing

- [x] 2.1 A model stand-in whose reply depends on the task label and the node's input, not on
      prompt wording; tests
- [x] 2.2 The differential step: generated and hand-written bodies on the contract's inputs,
      outputs and stub-handle effects compared; first difference kept
- [x] 2.3 Applied to every recorded green trial by rebuilding from its record (no model call);
      results recorded beside the trial, not in it
- [x] 2.4 Report: *equal on n inputs* / *differs* per arm and per node, stated as information

## 3. Operating history by replay

- [x] 3.1 `poc/serve.py --replay var/archive [--from] [--to]`: one tick per archived snapshot,
      injected clock, state carried forward, low priority; deterministic on the stub (tested by
      replaying twice)
- [x] 3.2 `dist/evaluation-feed.md`: replayed history, recording-period failures and live ticks
      in three separate tables; the recorded span and its coverage stated

## — Commit everything above. From here until 1.7 ends, edit nothing under `poc/`, `scripts/`, `graphs/` or `poc/sandbox/wit/`. —

## 1 (continued). The run

- [x] 1.6 **Commit the registration. Then, and not before, run**
      (`uv run --group poc python -m poc.generation.harness registered`, in the background; it
      lowers its own priority, checks the registration, runs the hand-written control, and spans
      sessions by resuming)
- [x] 1.7 When complete: derive results, check for contaminated trials (as `voided/` records),
      regenerate the report, commit. **Run 27 Oct 19:47 – 28 Oct 05:21 UTC, all 2,250 trials, in
      one sitting with no ceiling stop. Clean:** every model resolved to its registered ID, every
      task hash matched, no call failed, nothing voided. **The registered test: P5 108/225 vs P0
      0/225, p = 1.1e-40; the post-hoc result replicates** (`32a8577`). Found afterwards: the
      1.5 report code showed only the primary outcome, omitting the registered secondaries. They
      were added, computed by the registered definitions, without changing the analysis
- [x] 2.5 Run the differential step (2.3) over the registered run's green trials; commit.
      2,226 compared: 877 equal on every input, 1,349 differ (248 with a different task label),
      none failed to compare. Reported apart from the earlier runs' 671, never summed

## 3 (continued). Replays

- [ ] 3.3 Replay the archive on the stub (both tiers) and on each Claude model (confined tier
      only), at low priority; commit the exports. Model replays are trials on the same subscription and wait for 1.7 to
      finish. **Stub part done 28 Oct 2026 on the first 21 ticks** (21 h, 99.9% covered, no
      failed fetch): host and confined agree exactly (285 triaged, 169 kept, 16 publishing
      ticks). To redo, with the model replays, once the archive spans weeks; the exports are
      snapshots and are re-exported then. **Author's decision (28 Oct): hold the model replays
      for a longer archive.** Ready for them: a replay resumes after a usage-ceiling stop
      (re-run the same command), refuses to resume under another backend, tier or model, calls
      the model by full ID, and records the IDs the calls resolved to. E.g.
      `uv run --group poc python -m poc.serve --replay var --model haiku --tier confined`, then
      `--report --var var/replays/claude-confined-haiku --export poc/feeds/history/replays/claude-confined-haiku.json`

## 4. AgentDojo, spike first

Reading and writing a short document; touches no code, so it may run alongside 1.6.

- [x] 4.1 Read one AgentDojo suite; attempt three of its tasks as signal graphs, kept under
      `docs/` (not `graphs/`, which the runtime loads)
- [x] 4.2 Write down what expressed, what did not, and why; go or no-go for a benchmark change.
      **Result (`docs/agentdojo-spike.md`):** banking expresses as graphs (go); a benchmark from
      hand-written graphs is a no-go, because they are oracle plans. A comparable number needs a
      prompt-to-graph planner, which is a later change of its own

## 5. Records

- [ ] 5.1 `docs/ROADMAP.md` and `AGENTS.md` updated per phase
- [x] 5.2 Spec deltas reconciled with what was built; `openspec validate --strict`
