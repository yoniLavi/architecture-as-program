# Design: Paper 4

## Context

The evidence is fixed and generated:
- **`dist/architect.{md,json}`**:
  - the registered pretext experiment (400 trials, registration `b900365`), with its pre-use
    gate, the confirmatory test and the descriptive outcomes;
  - the AgentDojo measurement of one architect graph per task, beside the undefended
    baseline;
  - the pilot, kept apart.
- **`dist/agentdojo-banking.{md,json}`**: the banking corpus, the oracle plans with their
  predictions, the undefended Haiku baseline, and the idle-pass tasks.
- **`openspec/changes/archive/2026-11-07-add-architect-and-reviewers/design.md`**: every decision and finding
  ("As built", "What the registered run found").
- **`docs/paper-4-survey/`** and **`docs/paper-4-design-questions.md`** (D1–D9).

## Central claim (draft, for approval)

> From a task in natural language, an architect model writes a signal graph whose every grant
> of authority cites the task, and the graph is reviewed before anything runs: first
> formally, then by a second model. Because the authority is an artefact, each grant can be
> held to registered least-authority labels, so whether review catches a widening is
> measurable. On AgentDojo's banking suite, with one model (Claude Haiku 5.5) as both
> architect and reviewer, a pretext in the task raised the rate of widenings that review
> missed from 7.5% to 18.1% of trials. The registered test of that rise did not reach its
> threshold (p = 0.019 against α = 0.01). The reviewer caught all ten widenings planted to
> test it, but 17 of 76 trials with a widening the architect wrote; the citation check
> caught none. The graphs completed 7 of 16 tasks, against 13 for the same model undefended.

All figures come from `dist/architect.json` by interpolation, never typed.

What it does not say, stated in the introduction:
- that the pipeline defends against injection (attack success was zero for the undefended
  baseline too, and the two graphs predicted vulnerable failed before any writer);
- that a pretext raises widening (the registered test was not supported; the rates are
  descriptive);
- that automated review is independent (the architect and the reviewer are one model);
- that the labels are ground truth in any sense beyond the author's registered judgement;
- that the results hold beyond one model, one suite, two fixed pretexts and one attack.

## Budget (~7,000 words)

| § | Section | Target | Carries |
|---|---|---:|---|
| 1 | Introduction | ~700 | Run-time escalation as practice; the claim block; what it does not say; ≤4 contributions |
| 2 | Setting | ~600 | Paper 2's graph, validator and derivation, cited; the banking harness: kinds, library, scorer as written, idle-pass tasks |
| 3 | The pipeline | ~1,100 | Two stages, shapes never values; grants cite the prompt; the formal review; the reviewer's view and its model rule; no run-time escalation |
| 4 | Method | ~1,000 | Labels as upper bounds from the prompt alone, approved and registered; the registration; channels; the primary outcome; the pre-use gate; the pilot's three wordings, told straight |
| 5 | Results | ~1,400 | The confirmatory result first; the reviewers per column, never summed; pretexts loosen rather than steer; the quoted-name slips counted apart; AgentDojo beside the baseline, with the writer column |
| 6 | Related work | ~1,000 | CaMeL, ACE, Conseca, FIDES, Progent (published numbers, labelled as other models), the design-patterns paper, AI Control, self-preference and correlated errors |
| 7 | Limitations | ~1,000 | See below |
| 8 | Future work | ~250 | A different family as reviewer; content-borne pretexts; run-time-value bounds; escalation by reviewed edit; placement; the back half |
| 9 | Conclusion | ~150 | |

## What is not negotiable

- **The null is the headline.** The confirmatory result is stated in the abstract and the
  introduction exactly as registered. No descriptive rate is called an effect.
- **Every figure is interpolated**, counts of things in the data included. Paper 2's figures
  are cited, never typed.
- **Registered, pilot and AgentDojo results are never pooled.** The pilot's three wordings
  are disclosed as what changed the prompt.
- **The limits stay whole**, each where it bounds a claim:
  - one model as both architect and reviewer, stated as a lower bound on independence;
  - labels that are the author's judgement;
  - the link check measures linkage, not adequacy;
  - review measured need, never placement (which node holds a grant);
  - shapes, never values, cost utility, by design;
  - tasks 5 and 14 cannot succeed under least authority;
  - AgentDojo's idle-pass tasks and its goal-predicate precedence slip;
  - one attack, nine goals, so 0% is not the absence of a residual;
  - pure library nodes run on the host tier;
  - the quoted-name parser hole, found by the run and since closed;
  - the one harness fault before any trial;
  - pre-registration inside one repository, not a registry entry.
- **Demos get a mention**, if any, never a section.

## Open questions for the author

1. **Paper 3.** Paper 4 leans on Paper 3's registered result (claimed approvals move these
   models), and its reviewer was chosen from Paper 3's data. Paper 3 is unpublished, and its
   review is deferred until after Paper 4 and the vertical slice, so a published Paper 4 may
   not cite it. Options:
   - (a) Paper 3 publishes first, and Paper 4 cites it;
   - (b) Paper 4 cites the committed artifact, the registered data in the repository at a
     tagged commit, rather than the paper, and restates only the one figure it uses;
   - (c) Paper 4 drops the dependence, and states the reviewer rule's inputs as data.

   **Settled by the author's sequence (1 November 2026, `docs/ROADMAP.md`): (a).** The
   vertical slice comes next, then Paper 3 and this proposal are updated, then Paper 3
   publishes, and Paper 4 is drafted after. The proposal is revisited after the slice.
   **Revisited 7 November 2026:** the slice is done, and Paper 3's DOI is reserved
   (10.5281/zenodo.24043532). Paper 4 cites Paper 3 by that DOI, and the stamp check holds
   it to Paper 3's `RECORD.json`: Paper 4 is not stamped before Paper 3 publishes.
2. **Title.** Working: *Reviewed Before It Runs: Measuring Whether Automated Review Catches
   an Architect's Widened Authority*. The slug follows the title.
   **Answered 16 November 2026:** *Reviewed Before It Runs: Automated Review of an
   Architect's Authority*; the citable PDF is `lavi-2026-reviewed-before-it-runs.pdf`.
3. **Directory.** `papers/04-architect/`. **Answered 16 November 2026: as proposed.**
4. **The slice's replays over the registered records** (added 7 November 2026). Two shadow
   analyses ran over this paper's own registered graphs, after the fact:
   - the scope-binding link check flagged 1 of 61 unseen widenings, with 59 false alarms;
   - the behaviour-shown reviewer caught 21 of 76 widened trials, against 17, and flagged
     7 clean trials, against 3.

   The slice's rule is that its findings are never a figure in a paper. Options:
   - (a) keep the rule: Paper 4 uses them as framing only, in prose without numbers;
   - (b) report both as post-hoc analyses, labelled as such, apart from the registered
     results, interpolated from `dist/slice.json`. They answer the two objections a reader
     will raise first ("bind the link check to scope", "show the reviewer what the graph
     does"), and they are computed from the registered records, with no new model call
     except the reviewer's;
   - (c) drop them.

   Recommendation: (b), because the objections are predictable and the answer is in hand.
   It is the author's call, because it changes the rule the slice was approved under.

   **Answered 16 November 2026: (b).** The two replays appear in Paper 4 as post-hoc
   analyses, labelled so wherever they are cited, in a subsection of their own after the
   registered results, interpolated from `dist/slice.json`, and never pooled with or
   compared as a test against the registered figures. The slice's rule otherwise stands:
   no other slice finding becomes a figure.

## The Q0 spelling slip (the author, 16 November 2026)

The draft's critical review (task 4.1) found that one of Q0's unseen trials,
`user_task_15.Q0.1`, holds only the task's own approved grant written with quotes
(`Payments<['inbound-senders'], '10.00'>`), which the parser at the time read as a literal
payee. It counts as registered. Without it, the contrast is 29/160 against 5/80, one-sided
p = 0.0084, under α. **The author's decision:** the paper states the trial, why it counts,
and the recomputed p, labelled post hoc. The registered verdict stands, and the paper says
that this is the after-the-fact reanalysis registration exists to discount. Computed in
`report.py` (`label_spelling_slip`, `post_hoc_without_spelling_slips`), never typed.

**No replication (the author, 16 November 2026).** A rerun with the parser fix was weighed
and declined. A test rerun because p sat near α cannot rescue the original, and one at the
registered size would have about even power (41–53% at the observed rates). The paper
states what the run found, the slip and the threshold included, and the programme moves on.
A later proposal may revisit a replication if it would bring a new benefit, for example a
changed pipeline or a reviewer from another family. Replication for its own sake is not one.

## What the slice changes (7 November 2026)

- **Limitations gain one item: placement.** Every check, the labels included, asks whether
  the task needs a grant. None asks whether the node holding it should. In the slice, two
  model judges called an open payment grant held by developer code "needed", and said in
  prose that it was a concern. The labels cannot see this, so the paper must not imply its
  reviewers were measured on it.
- **"The link check measures linkage, not adequacy" stays as written**, and gains, under
  4(a) or 4(b), that binding it to the scope does not change that.
- **Future work grows to ~250 words** and takes three items from the slice, as directions
  without evidence: grants bounded by values an upstream node produces; an escalation
  answered by a reviewed edit that grants no more than was asked; placement as a review
  dimension. The back half (steps 5–8) stays out of scope.
- **No human review.** The slice's judges were models standing in for the author, so
  nothing in Paper 4 may describe step 8 as tried.

## Risks

- **The design hoped for a defence.** Prose drifts toward the hoped-for result. Review checks
  every sentence about pretexts or review for a claim the registered test did not support.
- **Over the budget.** The limits list is long, and each item bounds a claim. If it does not
  fit, the lever is scope (the pilot section first). Ask before cutting.
- **The report moves under the paper.** The keys Paper 4 reads are pinned by a test at
  stamping, as Paper 2's are.
