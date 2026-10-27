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

- [ ] 0.1 The harness lowers its own priority on start (`os.nice(19)`; `taskpolicy -b -p <pid>` on
      macOS where available), so `claude -p`, `cargo`, `wasm-tools` and the check process inherit
      it; `--no-nice` for an idle machine; default `--jobs 2`; cargo invoked with `-j 2`. Tests
      that the priority is applied and that the flag disables it
- [ ] 0.2 `poc/feeds/archive.py --record [--every INTERVAL]`: raw bodies under
      `var/archive/<UTC timestamp>/`, through the service's own `HTTPClient` handle and allowlist,
      with an index of every tick (time, feed, status, size); no model call, no parsing; a lock
      file refuses a second recorder; low priority as in 0.1; tests against the fixture server
- [ ] 0.3 Start the recorder in the background (`--every 1h`) and leave it running for the
      session. Repeat at the start of every later session; the gaps between sessions are gaps in
      the archive, and are reported as such

## 1. A pre-registered replication

- [ ] 1.1 Arms as data: pretexts in `poc/generation/prompts/`, one file each, P1–P6; P2 and P5
      byte-identical to the existing adversarial and authorised pretexts (tested)
- [ ] 1.2 The rule-withheld variant of the task template; test that it differs from the stated
      variant in that sentence and nowhere else
- [ ] 1.3 `poc/generation/registration.json`: pretexts, cells (15 nodes × 3 Claude models × P0–P6
      rule-stated, plus P0, P2, P5 rule-withheld; N = 5; **2,250 trials, repeats included**),
      models by full ID, the 150 task hashes, the primary outcome (first-attempt reach), the
      confirmatory test (Fisher exact, P5 vs P0), the secondary outcomes, the exclusion, voiding
      and early-stop rules. A test regenerates the hashes and holds them to the file
- [ ] 1.4 The harness refuses a registered run unless the registration is committed and unmodified
      at `HEAD`; refuses a trial whose task hash, or resolved model ID, is not the registered
      one; refuses to start a trial while `poc/`, `scripts/`, `graphs/` or the WIT differ from
      `HEAD` (its own records excepted); runs the hand-written control first and refuses unless
      it passes. Each trial records the registration commit and `HEAD`. Tests for each refusal
- [ ] 1.4a **Author approves the pretext texts and the registration before 1.6.** It cannot be
      corrected once trials have run, only disclosed
- [ ] 1.5 Report: the registered run in its own section, the primary outcome per pretext and per
      model, the earlier trials (including the post-hoc arm) beside it and labelled, the
      registration commit named; the report refuses to pool them; timings labelled as taken at
      low priority

## 2. Differential testing

- [ ] 2.1 A model stand-in whose reply depends on the task label and the node's input, not on
      prompt wording; tests
- [ ] 2.2 The differential step: generated and hand-written bodies on the contract's inputs,
      outputs and stub-handle effects compared; first difference kept
- [ ] 2.3 Applied to every recorded green trial by rebuilding from its record (no model call);
      results recorded beside the trial, not in it
- [ ] 2.4 Report: *equal on n inputs* / *differs* per arm and per node, stated as information

## 3. Operating history by replay

- [ ] 3.1 `poc/serve.py --replay var/archive [--from] [--to]`: one tick per archived snapshot,
      injected clock, state carried forward, low priority; deterministic on the stub (tested by
      replaying twice)
- [ ] 3.2 `dist/evaluation-feed.md`: replayed history, recording-period failures and live ticks
      in three separate tables; the recorded span and its coverage stated

## — Commit everything above. From here until 1.7 ends, edit nothing under `poc/`, `scripts/`, `graphs/` or `poc/sandbox/wit/`. —

## 1 (continued). The run

- [ ] 1.6 **Commit the registration. Then, and not before, run** (`harness run` at low priority,
      in the background; it spans sessions and resumes)
- [ ] 1.7 When complete: derive results, check for contaminated trials (as `voided/` records),
      regenerate the report, commit
- [ ] 2.5 Run the differential step (2.3) over the registered run's green trials; commit

## 3 (continued). Replays

- [ ] 3.3 Replay the archive on the stub (both tiers) and on each Claude model (confined tier
      only), at low priority; commit the exports. Model replays are trials on the same subscription and wait for 1.7 to
      finish

## 4. AgentDojo, spike first

Reading and writing a short document; touches no code, so it may run alongside 1.6.

- [ ] 4.1 Read one AgentDojo suite; attempt three of its tasks as signal graphs, kept under
      `docs/` (not `graphs/`, which the runtime loads)
- [ ] 4.2 Write down what expressed, what did not, and why; go or no-go for a benchmark change

## 5. Records

- [ ] 5.1 `docs/ROADMAP.md` and `AGENTS.md` updated per phase
- [ ] 5.2 Spec deltas reconciled with what was built; `openspec validate --strict`
