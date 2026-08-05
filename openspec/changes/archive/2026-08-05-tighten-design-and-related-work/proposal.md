# Tighten Paper 2's §2.5 and §6.3, and decide how hedging survives a rewrite

## Why

Paper 2 is 42pp against a working target of the low-to-mid 30s. The last review's
tightening item was only half-paid: §3.5 gave up ~190 words of genuinely duplicative
material (`4ab7b43`), and shedding a page wants ~450. The two remaining candidates
`AGENTS.md` names are §2.5 (Security properties, 507 words) and §6.3 (Effect systems,
capabilities, and purity, 562 words), and it records that both "need rewriting rather
than trimming".

That phrasing is right, and it is worth saying exactly why for each, because the two
are hard for different reasons.

**§6.3 is hard because the compressible material is interleaved with load-bearing
material.** Its three paragraphs are: the language survey (Haskell, Koka, Frank,
Idris, Roc, Effekt, Scala capture checking); Effect's requirements channel and its
`Layer` algebra; and the distance-drawing paragraph — that Effect declares
requirements and enforces nothing, so it is "the host tier of @sec:host-tier at
language scale". The last two paragraphs, ~380 words, make essentially one point and
could be one paragraph. But the `Layer` observation sits in the middle of the second
and is not filler: it is the only place the paper says what the demonstrator's
provisioning lacks, and it bears directly on the hierarchical capability-routing
options left open in §7.5. Deleting sentences loses it; the paragraph has to be
rewritten around it.

**§2.5 is hard because it is the densest hedging in the paper.** Its 507 words carry
eleven conditional or tier-splitting markers — *would accept*, *would extend*, *in a
sound realisation*, *intended to*, *only as an object discipline* (twice), *on the
confined tier* (twice), *not claimed* — roughly one every 46 words. It is also the
section `AGENTS.md` singles out as where the hedging discipline fails, for a
structural reason: §2 describes intent inside a paper otherwise written in the
present tense, so a claim reads as substantiated unless its mood is deliberately kept
conditional.

Those two facts together are the reason this needs its own change rather than being
folded into a routine tightening pass. **A rewrite that shortens §2.5 is a rewrite
that can silently strengthen a security claim**, and it is the single highest-risk
edit available in this paper. The corpus has a guard against numeric drift
(interpolation), a guard against capability drift (no paper may say the artifact
lacks something it has), and **no guard at all against hedge drift**. Today the only
thing standing between a shortened §2.5 and an overclaim is the care of whoever makes
the edit — which is exactly the arrangement the rest of the corpus has spent three
changes replacing with checks.

So the sequencing question is not "rewrite before tightening". The rewrite *is* the
tightening. The question worth settling first is whether the hedge-preservation
property gets a mechanism before the riskiest rewrite in the paper is attempted, or
whether it stays a review obligation. `design.md` sets out that decision; it is
genuinely open and should not be pre-empted by whoever picks this up.

## What Changes

- **§6.3** — the two Effect paragraphs become one, keeping the `Layer` observation and
  the "host tier at language scale" framing, which is the sharpest single sentence in
  the related-work section. Target ~180 words recovered.
- **§2.5** — rewritten for compression, not for cuts. Every one of the eleven hedges
  survives the rewrite, and every confined-tier-only property still says so. Target
  ~120 words recovered. If the rewrite cannot hit that without weakening a hedge, the
  hedge wins and the target is missed: length is a target, not a quota.
- **Hedge preservation** — either a mechanical guard in the established style or an
  explicit review obligation recorded in `AGENTS.md`. See `design.md`; this change
  should not begin the §2.5 rewrite until that is settled.
- **The page target itself** is re-examined rather than assumed. ~300 words recovered
  from ~450 needed still leaves the paper at 42pp. Whether the remainder should come
  out of §3.3.2, §3.4, or §7.5 — the three other sections over 900 words — or whether
  42pp is simply the honest length of this paper now, is a question this change should
  answer rather than leave for a fourth tightening attempt.

## Impact

- Affected specs: `paper-corpus`
- Affected papers: `papers/02-demonstrator/proposal.typ` (§2.5, §6.3)
- Affected docs: `AGENTS.md` (the tightening note, and the hedge obligation if it
  stays a review obligation rather than a check)
- Possibly affected code: a hedge guard would live in `scripts/`, and must stay
  dependency-free to run in the pre-commit hook
- Paper 1 is frozen and untouched. Paper 3 is untouched: nothing here is accounting,
  and no verdict moves.
- No evaluation figure changes, so no interpolation or pin is affected.
