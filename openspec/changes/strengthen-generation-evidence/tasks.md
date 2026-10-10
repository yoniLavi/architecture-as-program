# Tasks

Each phase ends green (`make build`) and committed. No file the generation check process imports
is edited while a run is in progress.

## 1. A pre-registered replication

- [ ] 1.1 Arms as data: pretexts in `poc/generation/prompts/`, one file each, P1–P6; P2 and P5
      byte-identical to the existing adversarial and authorised pretexts (tested)
- [ ] 1.2 The rule-withheld variant of the task template; test that it differs from the stated
      variant in that sentence and nowhere else
- [ ] 1.3 `poc/generation/registration.json`: pretexts, cells, N, the primary outcome, the
      secondary outcomes, the non-replication criterion
- [ ] 1.4 The harness refuses a registered run unless the registration is committed and unmodified
      at `HEAD`; each trial records that commit; tests for both refusals
- [ ] 1.5 Author checkpoint: repeats or reuse (design question 1)
- [ ] 1.6 **Commit the registration. Then, and not before, run.**
- [ ] 1.7 Report: the registered run in its own section, the primary outcome per pretext and per
      model, the post-hoc arm beside it and labelled, the registration commit named; the report
      refuses to pool the two

## 2. Differential testing

- [ ] 2.1 A model stand-in whose reply depends on the task label and the node's input, not on
      prompt wording; tests
- [ ] 2.2 The differential step: generated and hand-written bodies on the contract's inputs,
      outputs and stub-handle effects compared; first difference kept
- [ ] 2.3 Applied to every recorded green trial by rebuilding from its record (no model call);
      results recorded beside the trial, not in it
- [ ] 2.4 Report: *equal on n inputs* / *differs* per arm and per node, stated as information

## 3. Operating history by replay

- [ ] 3.1 `poc/feeds/archive.py --record`: raw bodies under `var/archive/`, through the service's
      own handle and allowlist; no model call; tests against the fixture server
- [ ] 3.2 `poc/serve.py --replay`: one tick per archived snapshot, injected clock, state carried
      forward; deterministic on the stub (tested by replaying twice)
- [ ] 3.3 Author checkpoint: the recorder left running, or a session-length recording (design
      question 3)
- [ ] 3.4 Replay the archive on the stub and on each model, both tiers; commit the exports
- [ ] 3.5 `dist/evaluation-feed.md`: replayed history, recording-period failures and live ticks
      in three separate tables

## 4. A second model family

- [ ] 4.1 Author checkpoint: local open-weights model, or one family (design question 2)
- [ ] 4.2 If local: a backend class behind the existing seam, standard library only; tests with a
      fake server
- [ ] 4.3 If local: the registered run's cells repeated on it, as a further registered run

## 5. AgentDojo, spike first

- [ ] 5.1 Read one suite; attempt three of its tasks as signal graphs
- [ ] 5.2 Write down what expressed, what did not, and why; go or no-go for a benchmark change

## 6. Records

- [ ] 6.1 `docs/ROADMAP.md` and `AGENTS.md` updated per phase
- [ ] 6.2 Spec deltas reconciled with what was built; `openspec validate --strict`
