# Design

## Decisions

- **D1. One argument, three changes.** The paper is not a changelog. Its spine is:
  value-bound grants, then the gap they leave (where the value came from), then
  provenance at the crossing, then what that costs. Split escalation appears as the means
  by which a developer obtains the extractor a bind needs.
- **D2. Exploratory throughout.** Every run behind this paper is unregistered and small
  (single digits to tens of runs, Haiku, stand-in models for injections). The paper
  states counts, never rates, and has no confirmatory test. Paper 4's registered results
  are cited from Paper 4, never re-stated as this paper's.
- **D3. Limits travel with claims.** Each claim's pinned limit appears in the same
  paragraph:
  - binds pay a wrong extractor's value;
  - provenance pays an injected known payee;
  - labels follow declarations.

## Open questions (answered in task 0.1)

1. **Title and directory.** Proposed: *Bound to the Value: Provenance-Checked Authority
   for Agent-Built Graphs*, in `papers/05-grants/`.
2. **One paper or two?** Recommended: one. The specified-architecture work (budgets,
   contract composition, proved cores) is a separate paper, proposed once its three
   changes land.
3. **Does a replication come first?** Recommended: no. Report the exploratory counts as
   exploratory, and leave a registered run for when a second model family is available.
