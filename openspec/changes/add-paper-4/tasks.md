# Tasks

Every session working on this change first checks the feed recorder (standing task 0.2 of
`operate-feed-triage`, formerly 0.3 of the archived `strengthen-generation-evidence`) and
`git status`.

## 0. Approval

- [x] 0.1 **The author approves this proposal**: the claim block, the budget, and the three
      open questions (Paper 3, title, directory). No paper text is written before this
      (proposal approved 1 November 2026. The three open questions are still to be
      answered; the first decides the corpus's order, see `docs/ROADMAP.md`)

- [x] 0.2 **The author answers the remaining open questions** (`design.md`): title,
      directory, and question 4, whether the slice's two replays over the registered
      records are reported as labelled post-hoc analyses (added 7 November 2026).
      Answered 16 November 2026: title *Reviewed Before It Runs: Automated Review of an
      Architect's Authority* (citable PDF `lavi-2026-reviewed-before-it-runs.pdf`);
      directory `papers/04-architect/`; question 4 is **(b)**, labelled post-hoc analyses
      from `dist/slice.json`, kept apart from the registered results
- [x] 0.3 Paper 3 published and its `RECORD.json` committed (`add-paper-3` 6.5); until then
      Paper 4 may be drafted but not stamped. Published 16 November 2026
      (https://zenodo.org/records/24043532)

## 1. The evidence, made quotable

- [x] 1.1 `poc/architect/report.py`: a `display` block in `dist/architect.json` with
      pre-formatted strings for every non-integer figure (the confirmatory p first).
      Rates are exact and rounded half up, so 17/80 prints 21.3%, as a reader checks it
- [x] 1.2 Serialise every count the paper states that the JSON only implies: a `counts`
      block. **Trials and grants differ:** the registered `unseen` column counts trials
      (59), and those trials hold 61 unseen grants, the unit the slice's replays use
      ("1 of 61"). The paper names which it states, every time
- [x] 1.3 `make build` green; commit

## 2. Corpus plumbing

- [x] 2.1 `papers/04-architect/proposal.typ`: a title block with no DOI, section labels, and
      `json("/dist/architect.json")`, `json("/dist/agentdojo-banking.json")`, and
      `json("/dist/slice.json")` for its `post_hoc` block only
- [x] 2.2 `Makefile` targets for Paper 4, and its citable PDF name
      (`lavi-2026-reviewed-before-it-runs.pdf`)
- [x] 2.3 The survey's entries in `citations.bib`, each checked against its source, and a
      Paper 3 entry with its DOI (`lavi_granted_2026`). Checked 16 November 2026: ACE
      (NDSS 2026), Conseca (HotOS '25), Kim et al. (ICML 2025) and CoT Red-Handed
      (NeurIPS 2025) are peer-reviewed, not arXiv-only as the survey had them; Kolluri's
      autonomy definition is quoted from its abstract; Panickssery's correlation is from
      fine-tuning. Only the entries the paper cites were added (Ye et al., PlanGuard not)
- [x] 2.4 If question 4 is (b): the replays' keys in `dist/slice.json` given a `display`
      block, kept apart from the registered figures and labelled post hoc: `post_hoc`,
      with its own `label` and `display`. The scope-binding replay counts grants (61),
      the behaviour one trials (76 widened, 76 clean), and the keys say which; the
      behaviour replay's 5 gained and 1 lost are computed (`review.crossover`)

## 3. Drafting

- [x] 3.1 §§1–9 to the budget, figures interpolated, the null first (first draft,
      16 November 2026, ~6,000 words of text; the slice's replays in their own post-hoc
      subsection, §5.3)
- [x] 3.2 Hedge pins for Paper 4 in `scripts/check-hedges.py` (nine)
- [x] 3.3 A test pinning the keys Paper 4 reads (`tests/test_paper4_figures_pinned.py`:
      the whole architect artifact, the banking and slice subtrees it reads, and a check
      that the source reads nothing outside them)

## 4. Review

- [x] 4.1 A full critical review, with the result applied (16 November 2026: 5 blocking,
      18 should-fix, 18 minor, each checked against the records before it was applied.
      The pilot history was corrected: a fourth change, never piloted. Hand-typed outcomes
      are now computed or asserted. The Q0 spelling slip and its post-hoc p are stated, by
      the author's decision (`design.md`). New report keys: within-label false alarms per
      view, effect-class planted widenings, target kind, failed-but-scored runs. Two hedge
      pins were re-seeded where the lower bound became a stated expectation)
- [ ] 4.2 **The author's read**. Deferred by the author, 16 November 2026: the research
      agenda goes further first, and Paper 4 publishes later as a checkpoint, as Papers 2
      and 3 did. The draft stays unstamped, held by its figure and hedge pins meanwhile
- [ ] 4.3 `papers/README.md`, `AGENTS.md`, `docs/ROADMAP.md`; `openspec validate --strict`

## 5. A post-hoc reviewer of greater capability (the author, 18 November 2026)

The author asked for a brief post-hoc run with Sonnet as the reviewer, because the
identical model in both roles is Paper 4's largest threat to validity. Model calls on
the subscription via `ClaudeCLIBackend`; no paid API spend. Then another round of
agentic review, then the author's prepublication read (4.2).

- [x] 5.1 **The plan, committed before the first call** (`poc/architect/posthoc_sonnet.py`,
      `poc/architect/runs/posthoc-sonnet/plan.json`). The registered reviewer's two views,
      re-run with `claude-sonnet-5-5` and nothing else changed, on the behaviour replay's
      fixed sample: 152 registered trials (all 76 with an effect-class widening, and 76
      clean ones chosen by SHA-256 of the trial ID), both views, so **304 calls** plus at
      most two repairs each. Primary view over every trial first, then persuaded. Before
      each call the system text and shown prompt are hashed and must equal the registered
      record's `inputs_sha256` for that view: all 304 reproduce, once the graph is rebuilt
      from the architect's final reply (the committed record sorts the graph's keys; the
      reviewer saw the architect's order). Baseline: the registered Haiku verdict, same
      view, same trials. Post hoc: never pooled, no confirmatory test, described as a
      reviewer of greater capability from the same family (diversity, not independence).
      If the ceiling stops it, it resumes; the paper reports it only once complete
- [x] 5.2 The run, in the background at low priority; no edit to `poc/`, `scripts/` or
      `graphs/` while it runs (18 November 2026: 304 of 304 calls, every one resolving to
      `claude-sonnet-5-5`, every one with a verdict, one repair; records `6b3a729`)
- [x] 5.3 `report.py`: a separate `post_hoc_sonnet` block in `dist/architect.json`, with
      `display` strings; Paper 4's post-hoc subsection, Limitations and Future work;
      the figure pin re-seeded deliberately (`44edd46`; two hedge pins seeded for the
      same-family qualification; headline figures pinned by test)
- [x] 5.4 Agentic review: a critical paper review and an adversarial claims check, in
      parallel, briefed with the paper and code only; findings and actions below.
      The claims check recomputed every figure from the raw records and found **none
      wrong**.

      **Applied:**
      - *Both reviewers:* the paper called Sonnet "more capable" and left out that
        §3's selection rule ranks it the model most moved by claimed approvals
        (240/300, against Haiku's 90), and that in channel A it reads the pretext.
        §5.3 now states both, calls it "larger", and gives its channel-A catches
        (new key `widened_by_channel`). "Changing nothing else" became "changing
        nothing in what it was shown", because CLI version, date and default effort
        differ.
      - *Critical review:*
        - The noise floor is now stated: the rationale view's 23 against 22 is 6
          gained and 5 lost, and no test-retest exists; the test-retest is added to
          Future work.
        - Task 10's label, whose reason cites AgentDojo's scorer, is disclosed in
          §4.1, §5.2 and §5.4, and task 15's plural line in §4.1.
        - The unit for the 59 grants on open-question labels is fixed, with its
          denominator (8 of 16 labels; new key `counts.labels.with_open_question`).
        - The conclusion's wording is now non-causal, and the claim block says
          "channel A".
        - The repeated "pre-use test overstated" in §6 is cut to a cross-reference,
          and the composition of the planted set is added in §5.2.
        - "Answer" became "bear on".
        - The reviewer rule's unit (first attempts) is fixed.
        - §5.1 says that no spelling slip falls in channel A.
        - The model behind `Extract` is named.
      - *Claims check:*
        - The conclusion said "17 of 76 natural widenings", but 76 is trials; it now
          says trials.
        - The behaviour replay showed each graph with its keys sorted, so none of
          its 152 prompts matches the registered hash. This is disclosed in §5.3, and
          `poc/slice/review.py`'s docstring is corrected.
        - A test now covers a clean trial flagged on a read-class widening, which
          counts as a flagged clean trial but not a false alarm.

      **To the author, not applied** (each changes a framing or an author's decision):
      - *Critical review S2:* drop "likely lower bound" in §7. The reviewer argues
        that misses shared with Sonnet on the same contested tasks fit label lines
        better than self-preference, and that catches rose only with false alarms.
        This would re-seed the `limits/lower-bound` hedge pin.
      - *Critical review S3:* take the post-hoc p = 0.0084 out of the abstract and
        keep it in §5.1 (the author decided on 16 November to state it; the
        abstract was not discussed).
      - *Critical review B1, consequence:* 3 of Q0's 6 unseen trials are on task 10,
        whose label draws on the scorer. That is disclosed, not reanalysed.
      - *Minor:* trim the claim block, which repeats the abstract's figures. Survey
        least-privilege permission inference and LLM permission judges in §6
        (unchecked).

      **The author's answers (18 November 2026: "go with your recommendations"):**
      - *S2:* kept the "likely lower bound" reading, because `registration.json`
        (`model_similarity`) and the `architect-pipeline` spec commit to it. Added to
        §7 that the post-hoc run gives the reading little support within the family,
        that the labels share the family, and that the paper keeps the reading as a
        registered prediction, not a finding. The hedge pin is unchanged.
      - *S3:* the abstract now says the verdict sits near the threshold and points to
        §5.1; the post-hoc p stays in §5.1 only.
      - *B1:* task 10 disclosed, not reanalysed.
      - *Minors:* the claim-block trim and the related-work survey are left to the
        fresh review.

      **Noted, not applied:** task 15's unseen grants are mostly a new recurring
      payment in place of the labelled edit, a second judgement line. §4.1 now names
      the plural line only.
- [x] 5.5 Rebuild and send the author the PDF for 4.2; no stamp, publish or push (sent
      18 November 2026)
- [x] 5.6 **A fresh review in a new session** (the author, 18 November 2026). It is
      read-only, and its findings are applied and recorded here. If it finds no remaining
      significant issue, the author does the final read (4.2); otherwise its significant
      findings go to the author first.

      Two read-only subagents, briefed with the paper, the code and the records only: a
      critical referee review (R) and an adversarial claims check (C). C recomputed every
      figure from the raw records with its own scripts, and all of them match. Each
      finding was checked against the records before it was acted on.

      **To the author, answered 18 November 2026 (both as recommended):**
      - *R1:* the paper never said what a reviewer flag does. `measure.py` ran task 5's Q0
        rep-0 graph, whose widening the reviewer had caught (`wider`), and it counts
        toward utility as an idle pass. **Disclosed:** §3 now says review is recorded and
        measured, not enforced; §5.4 says each graph ran whatever its verdict, and names
        task 5 (new key `measured.tasks[].reviewer_caught_widening`).
      - *R11:* §6's figures for CaMeL, FIDES and Progent on banking had no recorded check
        against their papers. **Dropped**; "no head-to-head figure" and its reason stay.

      **Applied:**
      - *Corrections of fact:*
        - C1: validator verdicts reach the architect as the validator's messages under a
          class from a closed set, not "reason classes, never free text"
          (`repair_text`). §3 and `architect.py`'s docstring are corrected.
        - C2: the reviewer still sees the architect's parameters, `Extract` instructions
          among them; this is stated in §3, and the contributions say "rationales".
        - C3: the other-family control has a gated backend, but no registered subset.
        - R3/C4: task 15's unseen grants are 16 of 20 a new recurring payment where the
          label grants an edit, not the plural line; §4.1 now names it (new key
          `unseen_by_task_grant`).
        - C7: "19 open scopes" became "no literal payee or cap to bind"; 2 of the 19 are
          profile fields.
        - C8: the pilot's first run was on one task (asserted).
        - C9, C10, C11, C15, C16, C17: "a widening" not "of scope"; "other unseen
          slips"; task 10's scorer note is its label's open question; the harness
          refuses uncommitted changes and the trials ran from the fix commit; a test
          holds the request builder, not the registered requests; the no-graph tasks are
          those of the first repetition's Q0 trial; the pre-use kind/scope split, which
          is hand-tagged, is dropped; the document date is 18 November.
      - *Hedges and limits added:*
        - R4/C5: "upper bounds … conservative call" is qualified by the contested lines
          on tasks 2, 10 and 15, which hold 48 of the 61 unseen grants.
        - R5: the primary outcome is per trial, so fewer `inexpressible` answers alone
          would raise it; per-graph counts are added in §7 (computed from the table).
        - R6: §5.1 says the test "did not show" a rise, and that a test of this size can
          miss one of the observed size. The `confirm/null-not-effect` hedge pin is
          re-seeded for it.
        - R7: the noise caveat is moved to the head of §5.3, covering every post-hoc
          comparison. "Moved" and "made" became non-causal. In §7, "flagged more clean
          trials" no longer supports the S2 sentence; the author's S2 decision and its
          wording otherwise stand.
        - R8: §7 says the pretext test ran on the model Paper 3 ranks least moved by
          claimed approvals.
        - R9: base rate: the open-question tasks hold 67 of the 76 widened trials too
          (new keys `widened_by_task`, `widened_trials_on_open_label_tasks`).
        - R10: 10 of the 12 target hits are a grant also written, unseen, in Q0 (new keys
          `unseen_target_by_task`, `unseen_target_also_unseen_in_q0`); "part-way" is
          dropped as uncounted.
        - R12: the conclusion allows that a closer look may show where the labels drew a
          line too tight, and its "how little" and "more" are computed.
      - *Rules and wording:*
        - R2: the claim block gives utility beyond the idle-pass tasks too.
        - R13: new asserts: Sonnet ranked most moved, both directions of change, task
          10's Extract failure, task 15's composition, the target share, the pilot's
          task counts, and the open-question majority.
        - R14: first attempts, not trials; Sonnet's 22 "of the 76".
        - R15: Table 2's caption says the graphs' attack success excludes the no-graph
          tasks.
        - R16: "as the pilot suggested" is dropped; both explanations of the `Extract`
          failures are named.
        - R17: "link check" throughout.
        - R18: the abstract's pointer is now "(§5.1)".
        - R21: "or a classifier" is cut; "the cells" became "the conditions"; the
          numerals are reworded; the evidence comment on Paper 3's figures is corrected.
        - R19: the construct paragraph cross-references §2 and §5.2 instead of
          restating them.

      **Rejected, with reason:**
      - *C6:* "today's parser moves the registered counts to p = 0.044". The script
        counted a refused spelling as a widening. Task 0's label is `[any]`; `'any'` read
        as intended or as a literal payee is within it, so the run-time verdict holds
        either way. The paper's one recount (the task-15 slip, by intent) is the
        consistent one.

      **Noted, not applied:**
      - R19: the two "zero is not a defence" sentences in §5.4 bound different claims
        (two graphs; the whole column), and one is a hedge pin. §7's two mentions of
        Claude-drafted labels were the author's S2 addition.
      - R20: related-work additions (Felt et al., Ye et al., AgentBound) are not added,
        because the paper is over its length budget.
      - The claim block is not trimmed: it is the approved claim.
      - C14: the link check's own false alarms (7 grants within their labels) are not
        reported; they bear on no claim.
      - R13: "That failure, on task 2" (§4.3) has no key; the claims check confirmed it
        from the pilot records.
      - C18: the figure pin compares `build()` with its seed, so it catches drift, not
        wrong values, and does not check `dist/` against `build()` (equal now).
      - The `architect-pipeline` spec says the architect receives "the reason classes".
        It also gets the message, which the spec does not forbid; the spec is unchanged.
      - Length: about 8,200 words rendered, against ~7,000. This round added ~210, almost
        all disclosure. The lever left is scope (for example, §5.3's scope-binding
        replay), which is the author's call.
