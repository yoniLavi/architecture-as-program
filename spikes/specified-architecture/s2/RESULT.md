# S2 result: contracts that compose along edges

*Task 2.1–2.2 of `explore-specified-architecture`, 18 November 2026. Stdlib-only
(`implication.py`, `run.py`); checks: `uv run pytest spikes/specified-architecture/s2`
(25 pass). Figures: `results.json`.*

## What was built

`implies(ensures, requirement)` decides, for a producer's `ensures` (a conjunction) and
one conjunct of its consumer's `requires`, one of six verdicts:
- `discharged`, `contradicted` or `not-implied`;
- `no-guarantee`, where the producer says nothing about the path;
- `vacuous`, where the producer's own contract is unsatisfiable;
- `undecided`.

It needs no solver.
- **Why it splits.** Every atom in the vocabulary relates one path to one literal, so
  implication splits path by path into interval reasoning on lengths and numbers, and
  finite-set reasoning on pinned values.
- **Edges it handles.** Joins are handled by position (`in1.date` on the edge into input
  1), and a variant edge is checked against the producer's `ensures`, which the runtime
  applies to every variant's payload.

## What it shows

1. **The check is decidable, small and sound, and it is held to the evaluator, not to a
   logic.**
   - A fuzz of 3,000 random contract pairs evaluates every verdict against
     `poc.contracts`' own `holds()` over concrete values. `discharged`, `contradicted` and
     `vacuous` admit no counterexample; over 95% of `not-implied` verdicts are witnessed
     by a concrete value.
   - **The fuzz found two bugs on the way.** First, a soundness bug: `x != 2` was taken
     to make `x` a number, but `'a' != 2` holds, and only an ordering forces a number.
     Second, a set of completeness gaps where `len` and value atoms on one path
     interacted.
   - The procedure's semantics are the evaluator's, quirks included:
     - an atom is false on a missing path, so any atom implies `present`;
     - an incomparable comparison is false, not an error;
     - `True == 1`;
     - the vocabulary has no float literals, though values may be floats, so numbers
       are reasoned over the reals (sound, slightly incomplete).
2. **On the repository's graphs there is little to check.**

   | corpus | edges | contracts on both sides | requirement-edges | discharged | no-guarantee |
   |---|---|---|---|---|---|
   | customer-support | 8 | 0 | 0 | — | — |
   | support-platform | 6 | 0 | 0 | — | — |
   | triage-item | 2 | 0 | 0 | — | — |
   | feed-triage | 11 | 2 | 1 | 1 | 0 |
   | customer-support + Paper 3's generation contracts | 8 | 2 | 5 | 2 | 3 |

   Nothing is contradicted, vacuous or undecided. The only non-trivial discharge
   (`StartRun → ComposeDigest[1]`, `len(date) == 10`) matches by textual identity.
3. **Guarantees do not survive a node, and that is the real finding.**
   `ModerateContent.ok → FetchContext` gets `no-guarantee` for
   `len(query.question) <= 512`, even though `ParseMessage` guarantees
   `len(question) <= 512` one hop earlier and `ModerateContent` only wraps the query.
   - **Why.** The vocabulary has no form relating a node's output to its input, so a
     pass-through node cannot pass a guarantee on. The ceiling the contract module
     chose ("anything richer would need a solver") is exactly what stops composition
     beyond one edge.
   - **Two ways out:**
     - every pass-through node restates the bound;
     - a fifth, relational atom form (`query == in`). Path equality stays decidable
       without a solver (union-find over paths), but it is a change to the
       vocabulary's design, and the contract module says a fifth form is a deliberate
       decision.
   - **S3 covers part of it.** A proved node body can carry such a relation as a
     theorem, where the run-time vocabulary cannot.

## What it does not show

- That a discharged edge lets a run-time check go. The runtime checks the producer's
  `ensures` anyway, so the `requires` on a discharged edge is redundant. Dropping it is
  only safe once something guarantees the producer actually keeps its `ensures`, which
  is a proof (S3), not this check.
- Anything about the agent-written graphs (Paper 4's architect). The node library
  carries no `requires`/`ensures` today.
- **Two verdicts are not checked against the evaluator** (found by the adversarial
  review). The fuzz checks `discharged`, `contradicted` and `vacuous`. It does not check
  `no-guarantee` (514 of 3,000) or `undecided` (71), and its values include no length-4
  string or list.
  - **What held:** the reviewer's wider fuzz (20,000 cases, with length 4 and fractional
    values) found no unsound `discharged`, `contradicted` or `vacuous`.
  - **One verdict is mislabelled conservatively.** `x >= 0 ⇒ len(x) >= 0` comes back
    `no-guarantee`, although under the evaluator's semantics it is `contradicted`. The
    error is downgraded to a warning, which is the safe direction.
  - **A validator analysis built from this** should fuzz every verdict class and widen
    the value set.

## Recommendation: propose a small validator analysis, at warning strength

- **Errors (wiring that is wrong):**
  - a `contradicted` edge (no run in which the producer keeps its contract can pass);
  - a `vacuous` producer contract.
- **Warnings (wiring nothing checks):**
  - a `requires` with `no-guarantee` or `not-implied`, listed per edge, so a reader
    sees which preconditions rest on run time alone.
- **Cost.** It stays stdlib-only, and roughly 250 lines move from this spike into
  `scripts/`.
- **Defer the relational atom.** Decide it with S3's result, because a proof may be the
  better carrier for input–output relations than a fifth vocabulary form.
- **Pin the fuzz.** The evaluator-agreement fuzz is the analysis's guard and should come
  with it.
