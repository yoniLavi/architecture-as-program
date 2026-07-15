# Change: Rewrite Paper 2 into paper form

## Why
After the paper-corpus restructure, Paper 2 (the demonstrator) is a *relocated* copy of the founding vision —
measured at ~75% identical to the frozen Paper 1 (a 68/34 line delta at the freeze point). Two near-identical
documents do not justify two papers; posted as a preprint, that overlap reads as duplication. Paper 2 earns
separate-paper status only by being restructured into paper form and saying something the vision structurally
cannot: *we predicted this, we built it, here is what held and what remains open*, backed by an evaluation.
This change is the rewrite.

## What Changes
- Restructure Paper 2 from the proposal arc (the window → central thesis → prior art → proposed system →
  research agenda → why now) into a **paper arc**: Abstract → Introduction (stating a falsifiable central
  claim) → Design → **Implementation** → **Evaluation** → Related Work → Research Agenda → Conclusion.
- Add an **Evaluation section built from the generated evaluation artifact** (`dist/evaluation.md`) — corpus
  verdicts, overhead, prompt-injection/tier results — so the section's numbers trace to a reproducible run.
- Add explicit **predictions-vs-outcomes positioning against Paper 1**: state which of the vision's
  conditional claims the demonstrator substantiates (assembly-time rejection of unsafe wirings, capability
  scoping/identity/revocation/rotation, confined-tier enforcement, operational composition) and which remain
  conditional (noninterference soundness, the full type system, user-level authorisation, replay), citing
  Paper 1 as the archived original vision.
- Convert **Technical Note A into a Research Agenda + Threats to Validity** — the same open problems, reframed
  as the forward agenda and the honest limits of what the artifact establishes.
- Preserve the project's hedging discipline: substantiated claims move to present tense *only* where the
  artifact backs them; everything else stays conditional.
- Not in scope: new artifact or evaluation work (those are the sub-graph-execution and evaluation-harness
  changes); editing Paper 1; the act of posting the preprint (a separate, human step).

## Impact
- Affected specs: `paper-corpus` (ADDED: the demonstrator paper is in paper form, carries an evaluation drawn
  from the artifact, and positions itself against the frozen vision).
- Affected code/docs: `papers/02-demonstrator/` (the rewrite), which now includes `dist/evaluation.md`; the
  bibliography may gain related-work entries; no artifact-behaviour change.

## Dependencies
Depends on `restructure-into-paper-corpus` (Paper 2 exists as a corpus entry referencing Paper 1),
`add-subgraph-execution` (operational-composition evidence for the Implementation section), and
`add-evaluation-harness` (the Evaluation section's source artifact). This is the last step before Paper 2 is
preprint-ready.
