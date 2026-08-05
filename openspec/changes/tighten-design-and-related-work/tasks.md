# Tasks

## 0. Settle the sequencing question first

- [x] 0.1 Read `design.md` and decide between options A, B and C. The rest of this
      list branches on that decision, so it is not a formality
      → **Option A**, decided with the author 5 August 2026: build the guard, then
      rewrite §2.5 under it. `design.md` recommended C-then-A-separately; the case
      for folding them into one change is that the guard's *seeding* is itself a
      read of every §2.5 claim against the artifact, which is the work the rewrite
      needs anyway — and it paid off immediately (see 2.2)
- [x] 0.2 If option A: build the pinned-claim guard in `scripts/`, dependency-free so
      the pre-commit hook stays portable, and wire it into `make build`
      → `scripts/check-hedges.py` (stdlib only), `make check-hedges` in the `build`
      chain, and a `check-hedges` pre-commit hook on the living papers
- [x] 0.3 If option A: seed the pins from §2.5's eleven current hedge markers, and
      confirm the guard fails when one is removed — a guard whose failure path is
      untested is a green tick
      → 15 pins seeded from §2.5 (the proposal's "eleven" undercounted; the section
      carries more distinct hedged claims than distinct markers). Grown to 19 with
      §2.3 and the two corrections. Failure path covered by
      `tests/test_check_hedges.py` — 13 tests, most of them assertions that the
      check goes *red*: hedge deleted (every pin, individually), claim rewritten
      while hedge vocabulary survives, fragment migrated to another section, pin
      edited down until it quotes no qualification
- [x] 0.4 If option B: record the obligation in `AGENTS.md` and stop pretending it is
      anything more than an obligation
      → n/a (option A), but the honest half was recorded anyway: `AGENTS.md` now
      states which passages are checked and that everything else rests on review

## 1. §6.3 — Effect systems, capabilities, and purity (safe; do this regardless)

- [x] 1.1 Merge the two Effect paragraphs into one, keeping the `Layer` observation
      and the "host tier at language scale" framing
- [x] 1.2 Confirm §7.5's hierarchical-routing item still has the `Layer` point behind
      it, since it depends on it — the "surface on which the ... options of
      @sec:open differ" clause survives verbatim
- [x] 1.3 Confirm no citation is orphaned by the merge (`scripts/check-citations.py`);
      `effect_ts_2026` is cited only here — still cited, check clean
- [x] 1.4 Target ~180 words recovered → **125 recovered** (562 → 437). The shortfall
      is real: the remaining candidates were the `Layer` observation, the
      "declared dependencies, not unforgeable references" distinction, and the
      language survey, none of which is filler

## 2. §2.5 — Security properties (gated on task 0)

- [x] 2.1 Do not start until 0.1 is decided and, if option A, until 0.3 passes
- [x] 2.2 Rewrite for compression, removing what §4.4 and §4.5 now carry with evidence
      rather than removing qualification
      → **the pass found three stale claims instead.** §2.3 and §2.5 (twice)
      still described the principal binding as *undesigned* after §3.4 built,
      propagated (RFC 8693 chain), and tested it; what is open is the *typed*
      form. That is drift in the understating direction, which no existing check
      catches — the evaluation harness only guards the overstating one. Fixing it
      cost roughly the 30 words the compression freed
- [x] 2.3 Verify all eleven hedges survive, on the claims they qualified — enforced
      mechanically now. One pin was re-seeded deliberately
      (`privilege/principal-binding`), because its claim was corrected; the guard
      is what forced that to be a decision rather than a side effect
- [x] 2.4 Verify every confined-tier-only property still says so — both tier
      restrictions intact and pinned (`privilege/tier-split`,
      `supply-chain/tier-split`), with a test asserting both are pinned so neither
      can lose it while the other keeps it
- [x] 2.5 Verify the privilege-escalation paragraph's caveats-then-measured-fact
      ordering is intact — intact. Only the 24-word sentence *announcing* the
      ordering was compressed to "in a deliberate order"; `design.md` protects the
      ordering, not the signpost
- [x] 2.6 Target ~120 words recovered — and miss it rather than weaken a hedge
      → **missed, deliberately: 507 → 506.** ~30 words of signposting and
      cross-reference slack came out; the correction in 2.2 spent them. The rest
      of §2.5 is qualification, and the spec's own scenario ("a length target
      yields to a hedge") is the governing rule

## 3. The page target

- [x] 3.1 Re-measure after §6.3 and §2.5 → **42pp before, 42pp after.** 125 net words
      is ~0.28 of a page; a page costs ~450
- [x] 3.2 Decide explicitly whether the residual comes from §3.3.2 (971), §3.4 (938)
      or §7.5 (1368), or whether 42pp is the honest length of this paper now
      → **42pp is the honest length, and the low-30s target is retired.** None of
      the three is available: §7.5 is stated limitations, §3.3.2 is the lead
      result, §3.4 is four tested capabilities. Three passes have now recovered
      ~315 words total against the ~450 a page costs, from exactly the sections
      successive reviews named as slack. The structural reason is that hedging is
      a per-claim tax "say each thing once" cannot collect against: the free-text
      residual is stated in §2.3, §2.5, §4.4 *and* §7.4, and each instance bounds
      a different claim in a different section, so deleting any one makes that
      section's claim read as unbounded. The two rules genuinely conflict, and the
      hedge rule wins. If length becomes binding for a venue, the lever is
      dropping a capability from the paper's scope — an author decision, not a
      tightening job
- [x] 3.3 Record the decision in `AGENTS.md`, replacing the current tightening note,
      so a fourth attempt does not rediscover this analysis — done, and four
      drifted section numbers in the old note fixed while replacing it (the
      residual is §4.4 not §4.3, the ambient-authority argument §3.3.2 not §3.4,
      the trace §3.7 not §3.5, and its ~1,100-word figure was pre-`4ab7b43`)

## 4. Verification

- [x] 4.1 `make build`, `scripts/check-citations.py`, `check-freeze.py`, pre-commit —
      all green; 335 tests + 21 subtests pass
- [x] 4.2 Re-read the rewritten §2.5 against §4.4, §4.5 and §7.4 for a claim that
      grew during compression → one clause was dropped as *too strong* rather than
      too long ("so downstream nodes operate only within that user's authorised
      scope"); §3.4 states that property where it is tested. The corrected
      principal-binding wording matches §7.5's ("unanswerable without running the
      graph") rather than exceeding it
- [x] 4.3 Confirm Paper 3 is untouched and no verdict moved — `papers/03-method/`
      clean, 16pp unchanged. Nothing here is accounting
- [x] 4.4 Page count before and after, recorded in the archive → Paper 2 **42pp →
      42pp**; §6.3 562→437 words, §2.5 507→506, §2.3 1006→1014 (the correction)
