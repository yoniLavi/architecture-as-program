## Context

Paper 2 accumulated two papers because the corpus structure encouraged it: one living document folding in
"what the demonstrator has since substantiated" has no natural place to stop. The split is the first time the
corpus gains a second living paper, so the conventions it sets (how living papers cite each other, how the
prediction accounting is owned by exactly one of them) matter more than this change's own content.

## Goals / Non-Goals

- Goals: two papers each with one claim and one reader; the confinement-derivation result led rather than
  buried; the agent-security literature engaged; the inspector bounded to a mention; both under ~18pp.
- Non-Goals: new artifact work; new evaluation; changing any interpolated figure; publishing; renaming
  `papers/02-demonstrator/` (its GitHub Pages URLs are live and the label still fits).

## The seam

The dividing question is **"what does the evidence support?"** versus **"what did predicting-then-building
teach?"**. Everything that interprets the artifact against the *vision* goes to Paper 3; everything that
establishes what the artifact *does* stays in Paper 2.

| Current §                          | Goes to | Note |
|---|---|---|
| §1 Introduction                    | both    | rewritten per paper; each states its own claim |
| §2 Design                          | P2      | cut ~13pp → ~4pp; FRP history to one paragraph |
| §3 Implementation                  | P2      | inspector §3.7 → a mention in §3.6 (trace) |
| §4 Evaluation                      | P2      | unchanged; figures keep interpolating `dist/evaluation.json` |
| §5 Predictions and outcomes        | **P3**  | including `tab:outcomes` and §5.3's four corrections |
| §6 Related work                    | split   | technical prior art → P2 (+ new agent-security subsection); MDA/SDD/research-method framing → P3 |
| §7 Research agenda                 | **P3**  | the agenda is the *output* of the accounting, so it belongs with it |
| §8 Threats                         | split   | construct/internal/external/security → P2; §8.5 threats-from-method → P3 |
| §9 Conclusion, Annex A             | split   | one each; Annex A (collaboration) → P3 |

Paper 2 keeps a two-paragraph §5-shaped summary ("what this does and does not substantiate") so it stands
alone without the accounting; Paper 3 restates no evidence, citing P2 for every figure.

## Decisions

- **Titles** (the decision most worth confirming before the rewrite):
  - P2: *Confinement by Construction: Capability Surfaces Derived from an Architecture Model*
    → `lavi-2026-confinement-by-construction.pdf`
  - P3: *Predicting Before Building: A Pre-Registration Protocol for Architecture Research, and What One
    Instance Corrected* → `lavi-2026-predicting-before-building.pdf`
  Paper 1's "Architecture as Program:" prefix is dropped from both. It is the corpus's name, and keeping it
  on every paper buries each paper's actual claim in a shared brand — the specific failure this split exists
  to fix. The corpus relation is stated in each abstract instead.
- **Directory `papers/02-demonstrator/` is kept.** Renaming would churn the Makefile and break the live
  GitHub Pages URLs in `README.md` for no reader benefit; per `papers/README.md` the directory label carries
  sequence and a rough content label, not the title.
- **Paper 3 is `papers/03-method/`**, living, built from the shared artifact like P2.
- **The prediction accounting has exactly one owner.** After this change, `tab:outcomes` exists only in
  Paper 3. Paper 2 stating its own limits is not the same artifact and must not grow into a second copy —
  two accountings that can disagree is precisely the drift the corpus discipline exists to prevent.
- **Publication order is P2 then P3**, because P3 cites P2's DOI. Zenodo can reserve a DOI before publishing
  if the two need to go out together, but sequential is simpler and there is no reason to rush P3.
- **Inspector reporting is bounded by spec, not by good intentions.** The existing `graph-inspector`
  requirement that paper claims map to tests stays; a new `paper-corpus` requirement caps the *volume* and
  fixes the verdict, so a future edit cannot quietly re-promote it.

## Risks / Trade-offs

- **Paper 3 is thin on its own** — a methods paper generalising from n=1 instance. Mitigation: its subject is
  the *protocol and its mechanisation* (a freeze guard in CI, errata-only discipline, published-DOI anchor),
  with the instance as worked evidence. If it still reads thin after drafting, the fallback is to hold it
  back and let the agenda ride along as a P2 appendix — decided on the draft, not now.
- **Cutting §2 risks removing the self-containment that lets P2 stand alone.** Mitigation: the cut targets
  *inherited vision* (workflow, time, intended runtime), not *mechanism* (graph, `with`, trust). A reader
  needs the mechanism to read §3–§4 and needs nothing else.
- **Two living papers doubles the drift surface** for interpolated figures and cross-references. Mitigation:
  P3 interpolates nothing and cites P2 for all figures.

## Open Questions

- Titles, as above — the one input worth having before the rewrite starts.
- Whether Paper 2 should retain a one-page "relation to the founding vision" section, or defer entirely to
  Paper 3. Lean: retain, one paragraph, because P2 will be read alone.
- Whether the deprecated `dist/proposal.*` aliases should now point at P2 still, or be dropped in this change
  since the corpus is gaining a third paper and the alias is already marked for removal. Lean: drop them
  here; the transition has had a release.
