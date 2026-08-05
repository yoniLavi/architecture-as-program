# Tasks

## 0. Settle the sequencing question first

- [ ] 0.1 Read `design.md` and decide between options A, B and C. The rest of this
      list branches on that decision, so it is not a formality
- [ ] 0.2 If option A: build the pinned-claim guard in `scripts/`, dependency-free so
      the pre-commit hook stays portable, and wire it into `make build`
- [ ] 0.3 If option A: seed the pins from §2.5's eleven current hedge markers, and
      confirm the guard fails when one is removed — a guard whose failure path is
      untested is a green tick
- [ ] 0.4 If option B: record the obligation in `AGENTS.md` and stop pretending it is
      anything more than an obligation

## 1. §6.3 — Effect systems, capabilities, and purity (safe; do this regardless)

- [ ] 1.1 Merge the two Effect paragraphs into one, keeping the `Layer` observation
      and the "host tier at language scale" framing
- [ ] 1.2 Confirm §7.5's hierarchical-routing item still has the `Layer` point behind
      it, since it depends on it
- [ ] 1.3 Confirm no citation is orphaned by the merge (`scripts/check-citations.py`);
      `effect_ts_2026` is cited only here
- [ ] 1.4 Target ~180 words recovered

## 2. §2.5 — Security properties (gated on task 0)

- [ ] 2.1 Do not start until 0.1 is decided and, if option A, until 0.3 passes
- [ ] 2.2 Rewrite for compression, removing what §4.4 and §4.5 now carry with evidence
      rather than removing qualification
- [ ] 2.3 Verify all eleven hedges survive, on the claims they qualified
- [ ] 2.4 Verify every confined-tier-only property still says so
- [ ] 2.5 Verify the privilege-escalation paragraph's caveats-then-measured-fact
      ordering is intact
- [ ] 2.6 Target ~120 words recovered — and miss it rather than weaken a hedge

## 3. The page target

- [ ] 3.1 Re-measure after §6.3 and, if attempted, §2.5
- [ ] 3.2 Decide explicitly whether the residual comes from §3.3.2 (971), §3.4 (938)
      or §7.5 (1368), or whether 42pp is the honest length of this paper now
- [ ] 3.3 Record the decision in `AGENTS.md`, replacing the current tightening note,
      so a fourth attempt does not rediscover this analysis

## 4. Verification

- [ ] 4.1 `make build`, `scripts/check-citations.py`, `check-freeze.py`, pre-commit
- [ ] 4.2 Re-read the rewritten §2.5 against §4.4, §4.5 and §7.4 for a claim that
      grew during compression
- [ ] 4.3 Confirm Paper 3 is untouched and no verdict moved
- [ ] 4.4 Page count before and after, recorded in the archive
