# Design: how hedging survives a rewrite

## The decision

§2.5 carries eleven hedges in 507 words and is about to be rewritten shorter. The
corpus mechanises its other drift guards. Does hedge preservation get a mechanism, or
stay a review obligation?

This is open. What follows is the case for each option and the evidence bearing on
it, so whoever picks this up decides rather than inherits.

## Why this is not obviously "just add a check"

The two existing drift guards work because their property is decidable against an
artifact:

- **Numeric drift** — the figure is interpolated from `dist/evaluation.json`. The
  check is that the number in the paper *is* the number in the data, and typst
  enforces it by construction.
- **Capability drift** — "no paper states that the artifact lacks a capability the
  artifact has" is checkable because the capability either exists in `poc/` or does
  not.

Hedge drift has no such artifact. "Is this claim appropriately hedged?" is a question
about the relationship between a sentence's mood and a property's evidential status,
and the second half of that is not machine-readable. A naive check — grep §2 for
`would`/`in a sound realisation` and require a minimum count — is trivially satisfied
by a rewrite that keeps the vocabulary and moves it off the claim it was qualifying.
That is worse than no check, because it converts a review obligation into a green
tick.

## Option A: a pinned-claim guard

Record, as data, the specific unproven claims §2 makes and the hedge each one
requires — the same shape as the evaluation's reason-class pins, which pin *what must
catch a fault* rather than merely *that something did*.

```
("sec:security", "privilege escalation", "would not acquire"),
("sec:security", "supply chain", "on the confined tier"),
...
```

The check asserts each claim's passage still contains its marker. A rewrite that
drops the hedge fails; a rewrite that rephrases it fails too, and has to update the
pin deliberately — which is the point, exactly as widening the overhead band is an
edit to a claim rather than a tuning knob.

- **For:** it catches the actual failure mode, which is a hedge disappearing during
  an unrelated edit. It is dependency-free and fits the pre-commit hook. It makes the
  set of unproven claims *explicit*, which has independent value: right now that set
  exists only in reviewers' heads.
- **Against:** the pin is hand-maintained, so it inherits the mapping-table weakness
  §7.1 already admits about the derivation — a wrong entry is invisible. It also
  cannot tell that a hedge still qualifies the *right* claim. And it risks reading in
  the papers as a stronger guarantee than it is; if it is built, neither living paper
  should describe it as anything more than a regression guard on known passages.

## Option B: an explicit review obligation

Record in `AGENTS.md` that §2.5 is hedge-critical and that any edit touching it
re-verifies the hedges, without a script.

- **For:** honest about what is actually being relied on. No false green tick. Zero
  maintenance.
- **Against:** it is the arrangement the corpus has been steadily replacing, and the
  review that produced this change found a hand-maintained magnitude that had drifted
  in exactly the way conventions decay — silently, and invisibly to a reader.

## Option C: neither, and don't rewrite §2.5

Take the ~180 words from §6.3, accept 42pp, and leave the densest hedging in the
paper alone on the grounds that ~120 words is not worth the risk to the corpus's most
important discipline.

- **For:** the length target is explicitly a target and not a quota, and `AGENTS.md`
  already records that Paper 2 is over it *knowingly*, because the August reviews
  added protected material. Trading hedge safety for a third of a page is a bad trade
  on its face.
- **Against:** it leaves a known-verbose section verbose, and the reason to shorten
  §2.5 is not only length — it restates material §4.4 and §4.5 now carry with
  evidence, which is the "say each thing once" rule rather than the page count.

## Recommendation

Option C for the length work plus Option A built separately, in that order. The
§6.3 rewrite is safe and pays most of what is available. §2.5's rewrite should not be
attempted until the guard exists, because the case for touching it is "say each thing
once" rather than page count, and that case is not urgent enough to justify making
the paper's highest-risk edit unguarded.

Recorded as a recommendation, not a decision.

## What must not be lost, whichever option wins

- Every confined-tier-only property in §2.5 still says so. The host tier demonstrably
  escapes, and a property that reads as universal is an overclaim, not a compression.
- The privilege-escalation paragraph's ordering is deliberate: two design caveats,
  then the measured fact about the artifact, in that order, because the last one most
  changes how the paragraph should be read. Reordering it for flow loses that.
- §6.3's `Layer` observation, which is the only place the paper states what the
  demonstrator's provisioning lacks, and which §7.5's hierarchical-routing item
  depends on.
- §6.3's "host tier at language scale" framing, which is the sharpest sentence in the
  related-work section.
