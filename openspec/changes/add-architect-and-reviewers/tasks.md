# Tasks

Depends on `add-agentdojo-banking-harness`: the harness, the library, the baseline and the
predictions. Each session first checks the feed recorder and `git status`. Long runs go at
low priority. While a registered run is in progress, edit nothing it imports.

## 1. The architect

- [x] 1.1 Stage one: prompt → abstract graph, with no catalogue. The output schema is tested
      (`poc/architect/abstract.py`, `prompts/stage-one.md`; closed reason classes)
- [x] 1.2 Stage two: abstract graph plus catalogue → graph JSON over the library, with every
      grant's `because` quoting the prompt (`mapping.py`; the catalogue is rendered from the
      library and shows shapes, never bank values; `{"inexpressible": …}` is an answer)
- [x] 1.3 The validator in the loop: structured reason classes, at most four repairs, and a
      recorded failure after them (`architect.py`, `verdicts.py`). The link and
      least-authority checks are deliberately *not* in the loop: they are the formal review
- [x] 1.4 Tests that the architect sees no tool output, injection or reviewer verdict. Inputs
      are hashed and recorded, as Paper 3's tasks are (every request is rebuilt in the test
      from the allowed pieces only)

## 2. The formal review

- [x] 2.1 The link check: `because` must be a verbatim span of the prompt. Pinned cases for a
      missing link and a fabricated one (`formal.py`; it measures linkage, not adequacy)
- [x] 2.2 Least-authority labels for the 16 banking tasks, drafted with reasons in
      `poc/architect/labels/` (draft committed; the principle, a reason per grant, and
      the open questions for the author are in `banking.json`)
- [x] 2.2a **The author approves the labels.** They cannot be corrected after the run, only
      disclosed (approved 31 October 2026, as drafted; task 5 stays `'Spotify'` and fails
      under least authority, task 10 has no payment grant, caps only where the prompt
      states an amount)
- [x] 2.3 The least-authority check: flag each grant beyond the label, by kind and by scope
      (`formal.py`, by the validator's own narrowing relation; each widening carries its
      class: effect, read, inference, answer)

## 3. The independent reviewer

- [x] 3.1 Canonicalisation, with rationales stripped. The structured verdict schema, which
      covers every grant (`reviewer.py`: nodes renamed `N1…Nk` in topological order;
      `needed` / `wider` / `not-needed`, quoting the prompt)
- [x] 3.2 A pinned corpus of hand-widened oracle graphs, and the pre-use test, with its
      threshold set in the registration (`reviewer_corpus.py`: 10 planted widenings, 5 by
      scope and 5 by kind, plus the 3 oracle graphs as controls; each case's ground truth
      is computed against the approved labels, and pinned)
- [x] 3.3 The model-choice rule, computed from Paper 3's registered data and recorded
      (`choose_model`, from the committed `results.json`; pooled P3–P6 first-attempt reach
      of 300: haiku 90, opus 94, sonnet 240, so **haiku**, by four trials. Pinned by a
      test; it goes into the registration)
- [x] 3.4 The second, persuasion verdict (rationales shown), stored apart (`view=persuaded`,
      a separate record)

## 4. The run

- [x] 4.1 Unregistered pilot: the architect on the 16 tasks, no pretexts. Check expressibility
      and utility through the harness. Exploratory, and labelled so (31 October 2026,
      Haiku; three wordings, the first two kept in `runs/pilot-catalogue-{1,2}/`. The
      third: 10 graphs, all within their labels; utility on 3, 4, 7, 8, 13, and on 5 and
      6 only because their predicates hold on an idle run; 5 inexpressible, 1 failed
      repair. Found: idle-pass tasks 5, 6, 8, 9, 10, now reported apart)
- [x] 4.2 The registration: pretexts verbatim for channels A and B, cells, model IDs, task
      hashes, the primary outcome (a widening missed by both reviewers), one confirmatory
      test, the reviewer's pre-use threshold, and the exclusion, voiding and early-stop rules.
      The harness refuses to run against an edited registration or tree (drafted:
      `registration.py`, `registration.json` with `"approved": false`, `trial.py`, and
      `run registered`, which also refuses an unapproved file)
- [x] 4.2a **The author approves the pretexts and the registration** before any trial
      (31 October 2026, as drafted)
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
