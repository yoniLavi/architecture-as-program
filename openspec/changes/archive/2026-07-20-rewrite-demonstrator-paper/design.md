## Context
Paper 2 is currently the vision text with artifact-backed sentences folded into the original proposal
structure. That structure is optimised to *argue a paradigm is worth pursuing*, not to *report a built
system*. The rewrite re-homes the same material (plus new Implementation/Evaluation content) into a structure
that reports a result and points forward — and differentiates it from the frozen Paper 1.

## Goals / Non-Goals
- **Goals:** paper-form structure; an Evaluation section sourced from `dist/evaluation.md`; explicit
  predictions-vs-outcomes positioning against Paper 1; Technical Note A recast as Research Agenda + Threats to
  Validity; hedging discipline preserved.
- **Non-Goals:** new artifact/evaluation work; editing Paper 1; posting the preprint; a venue decision beyond
  "arXiv preprint".

## Decisions
- **Decision: the central claim is scoped to what the artifact backs.** The Introduction states a falsifiable
  claim of the form "a class of vulnerable wirings becomes ill-typed / assembly-rejected, demonstrated over a
  corpus, with confined-tier enforcement at stated cost" — *not* "prevents prompt injection" or "provably
  secure". This is the claim the evaluation can actually support, and it is what keeps the paper honest under
  review.
- **Decision: predictions-vs-outcomes is the paper's spine, and its differentiation from Paper 1.** A dedicated
  thread states each vision prediction and its status (substantiated / partially / still conditional), citing
  Paper 1. This is the content Paper 1 structurally lacks and is what earns Paper 2 separate-paper status —
  not a diff of the same prose.
- **Decision: the Evaluation section is generated-artifact-sourced.** Numbers and verdicts come from
  `dist/evaluation.md`; the paper does not restate figures by hand. If the artifact and the paper disagree,
  the artifact wins (and the build should surface it).
- **Decision: Technical Note A becomes Research Agenda + Threats to Validity.** The open problems are the
  forward agenda; the honest limits (host-tier escapes, no soundness proof, the free-text residual) are the
  threats. Same content, reframed for a paper's contract with its reader.
- **Decision: hedging discipline is non-negotiable.** Present tense only where the artifact backs the claim
  (the project's standing rule). The rewrite is a structural move, not a licence to strengthen unproven claims.

## Risks / Trade-offs
- **Reviewer expectations rise with the "paper" label.** → Scope the claim to the evaluation; foreground
  threats to validity; target a vision/PL venue framing (arXiv preprint) rather than implying a security-venue
  result.
- **Text drift from Paper 1 that is cosmetic, not substantive.** → Enforce the predictions-vs-outcomes spine
  and the Evaluation section as the real deltas; a rewrite that only reshuffles paragraphs fails the point.
- **Figure/citation churn.** → Reuse the shared artifact's generated figures and the shared bibliography;
  related-work additions are additive.

## Migration Plan
Editorial, within `papers/02-demonstrator/`. No artifact behaviour changes. Build must stay green (Paper 2
renders; citations resolve; the evaluation artifact is included).

## Open Questions
- Venue framing beyond arXiv (Onward!/HotOS-style vision-plus-artifact vs a narrower systems/PL track). The
  maintainer decides; the rewrite targets a preprint that suits either.
- How much related-work expansion the paper needs versus what the proposal's §4 already covers. (Likely light:
  §4 is already substantial; add only what the sharpened claim requires.)
