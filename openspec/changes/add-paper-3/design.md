# Design: Paper 3

## Context

The evidence base is fixed and generated:

- `dist/generation.{md,json}` holds the registered replication (2,250 trials, one primary outcome,
  one confirmatory test), the earlier pilot and toy runs beside it and never pooled, the
  hand-written control, the gate-off control, and the differential step.
- `dist/evaluation-feed.{md,json}` holds the service's graph and rewiring corpus, its components
  held to their clauses, the hostile-feed corpus, three live ticks, the recording period, and the
  stub replays.
- `docs/agentdojo-spike.md` concludes that banking expresses as graphs, but no comparable number
  exists without a planner.

Paper 2 is reserved (DOI 10.5281/zenodo.23057135), stamped and unpublished. It waits on the
author's read. Its §8 names this experiment as the next one.

## Decided (by the author, 29 October 2026, before scaffolding)

1. **Sequential.** Paper 2 publishes first. Paper 3 cites it by DOI for the gate, the
   derivation, the confined tier and every Paper 2 magnitude, and states none of them in its own
   voice (the existing magnitude requirement already says a later paper cites rather than
   states). Drafting may start at approval. The upload waits on Paper 2's.
2. **Generation-led.** The central claim is about generated bodies and the gate. The service is
   the vehicle, and its hostile corpus gets one section. Live operation, the recording and the
   replays are stated limits; none is a result.
3. **~8,000 words.** A target, not a quota. A hedge wins over it.

## Central claim (draft, for approval)

> Given only a node's signature, contract, types and capability vocabulary, models of one family
> (Claude) did not reach for authority the node was not granted. They did not when a request
> asked them to, and they did not when the sentence stating the rule was withheld. Told that the
> authority had been *approved*, they reached for it. The registered replication confirmed this
> against the honest baseline at its registered threshold. The import gate derived from the graph
> (Paper 2) rejects every such component, which it must, since it is a set comparison. The
> finding is in the two counts on either side of that rejection: how often generated code
> presented an over-import, and how many of those components the gate-off control shows would
> have passed their contracts and run.

What it does not say, stated in the paper's introduction as Paper 2 states its own:

- that the gate's catch rate is an empirical finding (it is by construction);
- that models resist a well-crafted pretext (two of the pretexts are blunt and fixed);
- that the result holds beyond one family, or for a pretext delivered through retrieved
  content rather than in the task;
- that a green body is correct (the contracts are weak, and "equal" is on the contract's
  inputs only);
- that the service has been operated (three live ticks; replays are not operation).

## Budget (~8,000 words)

| § | Section | Target | Carries |
|---|---|---:|---|
| 1 | Introduction | ~800 | The question Paper 2 left; the claim block; what it does not say; ≤4 contributions |
| 2 | Setting | ~600 | Paper 2's gate, cited, not restated: derivation, confined tier, `unknown-unknown`, one paragraph; the fifteen nodes and what a model is shown; the pipeline |
| 3 | Method | ~1,400 | The history told straight: quiet pilot, post-hoc arm, then registration; what the registration fixes and what the harness refuses; primary outcome; confirmatory test; the ladder; rule withheld; gate-off control; the differential step |
| 4 | Results | ~1,700 | Confirmatory result; the ladder, descriptive; rule withheld; the spread across models, observed, not explained; reach by kind (gate, ambient, declared-only) never summed; gate-off; green and first-try; differential |
| 5 | The service | ~800 | The graph's security shape; the policy check, stated as *not* a validator analysis; the hostile corpus by verdict, residual pinned as succeeding; live, recording and replay as limits |
| 6 | Related work | ~1,100 | TACIT, CaMeL, language-based agent control, AgentDojo with the spike's finding, CAmkES (generating vs checking); authority-claim compliance and studies of LLM-written code (to be surveyed) |
| 7 | Limitations | ~1,200 | See "What is not negotiable" |
| 8 | Future work | ~200 | A second family; a pretext delivered through content; a planner for AgentDojo; model replays |
| 9 | Conclusion | ~200 | |

## What is not negotiable

- **Every figure is interpolated** from `dist/generation.json` or `dist/evaluation-feed.json`,
  including counts of things in the data ("the two components that would not ship"). Paper 2's
  figures and magnitudes are cited from Paper 2 and never typed.
- **Registered and earlier trials are never pooled**, in prose or in a table. The post-hoc
  origin of the authorised arm is stated wherever that arm is cited.
- **Only P5 against P0 carries a significance claim.** The ladder, rule withheld, and per-model
  rows are descriptive. The ladder is called a ladder, and its two bundled steps are named:
  P1 → P3 adds an authority claim as well as a claimant, and P4 → P5 bundles "treat it as
  granted" with "the graph will catch up".
- **The limits stay whole**, each where it bounds a claim:
  - one model family;
  - pre-registration inside one repository, not a registry entry;
  - the pretext placed in the task, not delivered through content;
  - five trials a cell, so no per-node claim;
  - weak contracts;
  - differential "equal" on one to four inputs for some nodes;
  - `feed_policy` is a service check, not a validator analysis;
  - the hostile corpus is curated and the fooled model a stand-in;
  - three live ticks;
  - replays are not operation;
  - no model replays yet;
  - no published suite.
- **Demos get a mention**, if any, never a section.
- **No prediction of Paper 1 is restated with a verdict.** The accounting has one owner.

## Decision: the stamp check

The rule "a published paper cites no unpublished work" is today a review obligation, and review
has missed it once. Following the corpus's preference for a check over an obligation:

- A paper is **stamped** if its `proposal.typ` title block carries a `doi.org/10.5281/…` link.
- A corpus paper is **published** if its directory holds a committed marker with
  `"status": "published"`: `PUBLISHED.json` for a frozen paper (as now), and `RECORD.json` for a
  living one (new; DOI, record URL, date). Paper 2's upload step commits its `RECORD.json`.
- `scripts/check-corpus-citations.py` maps each corpus bib entry to a paper by DOI. It fails if
  a stamped paper cites a corpus entry whose paper is unpublished, or a corpus-like entry (author
  `Lavi`, Zenodo DOI) that maps to no paper. It is stdlib-only and offline, and runs in
  `make build` and pre-commit.

Its limit, stated where the check is documented: it trusts the marker. The build cannot see
Zenodo, so a marker committed before the record goes live would pass. It checks corpus papers
only. External "in preparation" citations stay on review.

*Alternative considered:* a field in the bib entry (`note = {Preprint}` against
`{In preparation}`). Rejected: it is hand-maintained beside the thing it describes, which is the
defect the corpus's other guards exist to remove.

## Risks

- **Narrating the ladder.** The counts invite a story: naming the interface moves the most, and
  "treat it as granted" moves one model down. Registered as descriptive, it stays descriptive.
  Review checks every sentence about a step for a causal verb.
- **Paper 2's read keeps slipping.** Paper 3 can be drafted, reviewed and read regardless. Only
  its upload waits. If Paper 2 changes in the read, Paper 3's citations of its sections are
  re-checked before stamping.
- **Over the budget.** The limits list is long, and every item bounds a claim. If it does not fit,
  the lever is scope (the service section first), not the hedges. The author is asked before
  cutting it.
- **The report moves under the paper.** Paper 3 interpolates from committed results, but
  `report.py` will change in this change. The registered keys Paper 3 reads are pinned by a test
  at stamping, as Paper 2's are.

## Open questions for the author

1. **Title.** Working: *Granted by Claim: Agent-Written Components Against a Derived Import
   Gate*. The slug follows the title.
2. **Directory.** `papers/03-generation/`, with the label as a rough content hint, as for
   `02-demonstrator/`.
3. **Year in the slug.** `lavi-2026-…` is provisional; it follows Paper 2's upload.
