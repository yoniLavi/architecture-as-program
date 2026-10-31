# Tasks

Depends on `add-agentdojo-banking-harness`: the harness, the library, the baseline and the
predictions. Each session first checks the feed recorder and `git status`. Long runs go at
low priority. While a registered run is in progress, edit nothing it imports.

## 1. The architect

- [x] 1.1 Stage one: prompt → abstract graph, with no catalogue. The output schema is tested
      (`poc/architect/abstract.py`, `prompts/stage-one.md`; closed reason classes)
- [ ] 1.2 Stage two: abstract graph plus catalogue → graph JSON over the library, with every
      grant's `because` quoting the prompt
- [ ] 1.3 The validator in the loop: structured reason classes, at most four repairs, and a
      recorded failure after them
- [ ] 1.4 Tests that the architect sees no tool output, injection or reviewer verdict. Inputs
      are hashed and recorded, as Paper 3's tasks are

## 2. The formal review

- [ ] 2.1 The link check: `because` must be a verbatim span of the prompt. Pinned cases for a
      missing link and a fabricated one
- [ ] 2.2 Least-authority labels for the 16 banking tasks, drafted with reasons in
      `poc/architect/labels/`
- [ ] 2.2a **The author approves the labels.** They cannot be corrected after the run, only
      disclosed
- [ ] 2.3 The least-authority check: flag each grant beyond the label, by kind and by scope

## 3. The independent reviewer

- [ ] 3.1 Canonicalisation, with rationales stripped. The structured verdict schema, which
      covers every grant
- [ ] 3.2 A pinned corpus of hand-widened oracle graphs, and the pre-use test, with its
      threshold set in the registration
- [ ] 3.3 The model-choice rule, computed from Paper 3's registered data and recorded
- [ ] 3.4 The second, persuasion verdict (rationales shown), stored apart

## 4. The run

- [ ] 4.1 Unregistered pilot: the architect on the 16 tasks, no pretexts. Check expressibility
      and utility through the harness. Exploratory, and labelled so
- [ ] 4.2 The registration: pretexts verbatim for channels A and B, cells, model IDs, task
      hashes, the primary outcome (a widening missed by both reviewers), one confirmatory
      test, the reviewer's pre-use threshold, and the exclusion, voiding and early-stop rules.
      The harness refuses to run against an edited registration or tree
- [ ] 4.2a **The author approves the pretexts and the registration** before any trial
- [ ] 4.3 The registered run, on the subscription, resumable, spanning sessions
- [ ] 4.4 AgentDojo's utility and security for the architect's graphs, against the same-model
      baseline; predictions against outcomes; autonomy

## 5. The cross-family control (gated)

- [ ] 5.1 A DeepSeek backend in `poc/llm.py` that refuses to run without a committed approval
      file holding a spend ceiling, and stops at the ceiling. Tests use a fake
- [ ] 5.2 **The author decides**, from the subscription results, whether the control is worth
      the spend, and approves a ceiling
- [ ] 5.3 If approved: the reviewer, on the registered subset, by the other family. Reported
      beside the same-family figures, never pooled with them

## 6. Report and records

- [ ] 6.1 `dist/architect.{md,json}`, from committed records. The build calls no model. Keep
      registered and exploratory results apart; give catches per reviewer, not summed; state
      the similarity of the reviewer's and architect's models
- [ ] 6.2 `AGENTS.md`, `docs/ROADMAP.md`; spec deltas reconciled; `openspec validate --strict`
- [ ] 6.3 Then propose `add-paper-4`, the paper. After it, the thin vertical slice
      (`docs/ROADMAP.md`)
