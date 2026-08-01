# Update the living papers after the Paper 2 review

## Why

A full critical review of Paper 2 (`/review-proposal 2`) found one defect class that
the corpus's existing guards cannot catch, plus a set of smaller drifts.

**The defect class.** The corpus has strong machinery against *numeric* drift —
`#ev`/`#d` interpolation, pinned verdicts, one owner per number — and nothing at all
against **capability drift**: a sentence asserting that the demonstrator *lacks* some
capability stays green forever after the capability is built. Two capabilities landed
after the paper split (`87b7d7e`) and neither reached the prose:

- `eee4e71` **the contract language**. Paper 2 §3.5 reports it built, with blame and a
  closed vocabulary, and pins a corpus case to its reason class. Five other passages in
  Paper 2 still say the demonstrator has no contract language, and one of them points at
  the very section that describes it. Paper 3 states three times that it does not exist.
- `1740657` **principal binding**. Paper 2 §3.4 reports a principal bound at assembly, a
  `binds_principal` marker, an RFC 8693 delegation chain in the trace, and propagation
  across composition — all tested. Paper 3 §5.1 says these are "all undesigned".

Because Paper 3 owns the accounting, this is not cosmetic: two rows of `tab:outcomes`
carry a verdict of *Conditional* with no evidence either way, for predictions the
artifact has partial evidence for. That is a verdict not traceable to the artifact,
which is the one thing the accounting exists to guarantee.

**The lead result has no evaluation entry.** Paper 2's central claim is derive-and-compare:
the permitted import set is computed from the `with` clause and checked against the built
binary. That gate is asserted by `tests/test_poc_sandbox.py`, reported in §3.3.2, and
appears in no §4 table. §4 evaluates four other things. A reader weighting the Evaluation
section finds the lead result evaluated nowhere.

**Plus one hand-typed count that has already drifted.** §4.1 says "The two mutations"
directly beneath an interpolated `4/4` — the exact defect class the interpolation
discipline was built to eliminate.

## What Changes

- **Evaluation harness** — `poc/evaluate.py` gains a derive-and-compare block: per ported
  node, the interface set derived from its `with` clause, the set its built component
  actually imports, and whether they agree. Pinned in the established style, so an
  over-granting world fails the build rather than emitting a passing report. Paper 2 §4.4
  gains a table interpolating it, giving the lead result evidence in the Evaluation.
- **Paper 3** — the accounting is re-synced with the artifact: the contract and
  user-authorisation rows move from *Conditional* to *Partial* with their restrictions
  stated, the cascading prose counts are corrected, and the four false "the demonstrator
  has none" sentences are replaced by what is actually built and what is actually missing.
- **Paper 2** — the five self-contradicting contract sentences are corrected; the contract
  layer is added to the contributions and to §5; the hand-typed mutation count is removed;
  `ServiceOutcome`, the CHERI clause, the agent-generation tense, and the uncited
  graph-tooling claim are fixed; §3.7's replay discussion is trimmed of the accounting
  framing that belongs to Paper 3.
- **New spec rule** — a capability-drift guard for the corpus: no paper may state that the
  artifact lacks a capability the artifact has, and an accounting verdict must reflect the
  artifact at build time. This is the rule that would have caught both drifts.

Length: Paper 2 is at 40 pages against a low-to-mid-30s target; the §3.7 trim and the
de-duplication of Paper 3's accounting framing are the recovery.

## Impact

- Affected specs: `evaluation`, `paper-corpus`
- Affected code: `poc/evaluate.py`, `tests/test_poc_evaluate.py`
- Affected papers: `papers/02-demonstrator/proposal.typ`, `papers/03-method/proposal.typ`
- Affected docs: `AGENTS.md`, `papers/README.md`, `citations.bib`
- Paper 1 is untouched (frozen); no errata arise from this review.
