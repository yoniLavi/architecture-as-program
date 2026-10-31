# Paper 4: an architect that writes authority, and reviewers that check it before it runs

> **Status: proposed, 31 October 2026. Not approved. No paper text is written until it is.**
> The evidence is complete (`add-agentdojo-banking-harness`, archived;
> `add-architect-and-reviewers`, 21/23 tasks, 5.3 open because no spend is approved).
> Three questions are the author's before any prose (`design.md`, "Open questions").

## Why

The north star's front half (`docs/ROADMAP.md`, steps 1–4) has been built and measured. A
Product Owner's prompt goes to an architect model, which writes a signal graph. A formal
review checks it, and an AI reviewer checks it again, before anything runs. The graph then
determines each component's import surface, as Paper 2 established. The survey
(`docs/paper-4-survey/`) narrows what is new to three properties together: the authority
artefact is **persisted**, it is **reviewed before execution**, and it **determines the
binaries**. It also names the threat every surveyed pattern leaves out of scope: a pretext in
the user's own prompt. No paper reports this yet.

The result is not the one the design hoped for, and the paper must say so first:
- the one registered contrast was **not supported** at its threshold;
- the reviewer passed its pre-use test, then caught a minority of natural widenings;
- the link check caught none;
- the graphs' utility is well below the undefended baseline's.

The method is the contribution, together with what it measured: a reviewable authority
artefact makes widening *countable* against registered labels, and here it showed the
automated reviewers falling short. A paper that reported this as a defence would overstate
the artifact. One that stayed silent would waste a registered null.

## What Changes

- **A new living paper, `papers/04-architect/`**, of about 7,000 words. Its lead claim is
  methodological, then empirical:
  - authority written as a graph can be held, grant by grant, to registered least-authority
    labels;
  - so whether automated review catches a widening is measurable before anything runs;
  - measured on AgentDojo's banking suite with one model as architect and reviewer, it
    mostly did not.

  Every figure is interpolated from `dist/architect.json` and
  `dist/agentdojo-banking.json`.
- **It cites Paper 2** for the graph, the validator, the derivation and the confined tier,
  and restates none of them. How it relates to Paper 3, which is unpublished, is an open
  question for the author: Paper 3 holds the result that claimed approvals move these
  models, and the data the reviewer's model was chosen from.
- **The architect report gains a `display` block** for every non-integer figure the paper
  uses (the confirmatory p first), as Paper 3's did.
- **No accounting of Paper 1** is restated. That has one owner, Paper 2.

**Not in this change:**
- any edit to Paper 2 (the figure pin stands) or to Paper 3's draft;
- a second model family (5.3 is open and unfunded);
- the back half (steps 5–6);
- human review (steps 7–8);
- the vertical slice;
- any upload, DOI reservation or other outward-facing act.

## Impact

- **Specs:** `paper-corpus` gains two requirements, for the architect paper's claim
  discipline and for its figures.
- **Papers:** new `papers/04-architect/proposal.typ`. Paper 1 stays frozen, and Papers 2 and
  3 are unchanged.
- **Build:** the `Makefile` gets Paper 4's targets, and `scripts/check-hedges.py` gets pins
  for Paper 4 once it is drafted.
- **Code:** `poc/architect/report.py`, for the `display` block only. No run is in progress.
- **Docs:** `citations.bib` (the survey's entries: ACE, Conseca, FIDES, the design-patterns
  paper, AI Control, Panickssery et al., Kim et al., CoT Red-Handed), `papers/README.md`,
  `AGENTS.md`, `docs/ROADMAP.md`.
