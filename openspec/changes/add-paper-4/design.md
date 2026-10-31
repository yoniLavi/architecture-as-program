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
- **`openspec/changes/add-architect-and-reviewers/design.md`**: every decision and finding
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
| 8 | Future work | ~150 | A different family as reviewer; content-borne pretexts; the back half |
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
2. **Title.** Working: *Reviewed Before It Runs: Measuring Whether Automated Review Catches
   an Architect's Widened Authority*. The slug follows the title.
3. **Directory.** `papers/04-architect/`.

## Risks

- **The design hoped for a defence.** Prose drifts toward the hoped-for result. Review checks
  every sentence about pretexts or review for a claim the registered test did not support.
- **Over the budget.** The limits list is long, and each item bounds a claim. If it does not
  fit, the lever is scope (the pilot section first). Ask before cutting.
- **The report moves under the paper.** The keys Paper 4 reads are pinned by a test at
  stamping, as Paper 2's are.
