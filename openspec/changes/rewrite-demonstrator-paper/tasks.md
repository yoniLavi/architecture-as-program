## 1. Structure
- [ ] 1.1 Restructure Paper 2 into a paper arc: Abstract → Introduction (falsifiable central claim) → Design →
      Implementation → Evaluation → Related Work → Research Agenda → Conclusion
- [ ] 1.2 Write the Introduction's central claim scoped to what the artifact backs (assembly-time rejection +
      confined-tier enforcement at stated cost), not "provably secure"

## 2. Evaluation + implementation
- [ ] 2.1 Add an Evaluation section sourced from `dist/evaluation.md` (corpus verdicts, overhead,
      prompt-injection/tier results); do not restate figures by hand
- [ ] 2.2 Write the Implementation section covering the validator, runtime, two tiers, capability
      identity/revocation/rotation, and operational composition (sub-graph execution)

## 3. Positioning
- [ ] 3.1 Add the predictions-vs-outcomes thread: each vision prediction and its status (substantiated /
      partial / still conditional), citing Paper 1 as the archived original vision
- [ ] 3.2 Recast Technical Note A as Research Agenda + Threats to Validity (open problems forward; honest
      limits stated)

## 4. Discipline + wrap-up
- [ ] 4.1 Preserve hedging: present tense only where the artifact backs the claim; no strengthening of unproven
      claims
- [ ] 4.2 Full gate green: Paper 2 renders, citations resolve, evaluation artifact included; ruff, pytest,
      corpus `make build`

## Notes for whoever picks this up
- The predictions-vs-outcomes spine and the Evaluation section are the *real* deltas from Paper 1. A rewrite
  that only reshuffles paragraphs has not done the job.
- Scope the central claim to the evaluation and foreground threats to validity — this is what survives review.
- Numbers come from the generated artifact, never hand-typed into the prose.
