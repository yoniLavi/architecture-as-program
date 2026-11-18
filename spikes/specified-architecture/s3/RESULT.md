# S3 result: proved node bodies

*Tasks 5.1 and 5.2 of `explore-specified-architecture`, 18 November 2026. The proofs
are in `lean/Proofs.lean`, the gate is `check.sh`, the pilot is `pilot/`.*

## The route

The survey's route (`docs/PRIOR-ART.md` §§20–25) worked as described:
- **Pull a pure core out of each node body.** This is `cores/src/lib.rs`, 174 lines of
  Rust with no `serde`, no WIT and no I/O. Effects are data, and host results are
  arguments or a `Host` trait.
- **Translate it with Charon and Aeneas** into `lean/Cores.lean`. The first attempt
  worked, with no Rust changed to suit the tool.
- **The gate owns the statements**, as in proof-carrying code. `lean/Statements.lean` is
  pinned by hash, together with `Cores.lean`.
- **`check.sh` accepts a proof file only if** it builds, declares no axiom, `opaque`,
  `sorry`, `native_decide` or kernel escape, and each theorem both elaborates against
  its pinned statement and depends on Lean's three standard axioms alone.

The cores are held to the shipped Rust by `cores/tests/differential.rs`. One test there
checks `is_space` against `char::is_whitespace` over all of Unicode.

## 5.1: three nodes, proved

| node | statement (lines) | proof (lines) | time | what it says |
|---|---|---|---|---|
| DropSeen | ~6 | ~114 | ~10 min | keeps exactly the unrecorded ids, each once, and does not panic |
| SummariseItem's summary | ~5 | ~122 | ~7 min | for **every model reply**: at most `limit` code points, and no line break of seven kinds |
| GenerateResponse's tool loop | ~11 | ~222 | ~9 min | for **every `Host`** (model and knowledge base): at most 3 calls of each kind, lookups ≤ calls, and a refused tool is never the granted one |

`check.sh` accepted all three, depending only on `propext`, `Classical.choice` and
`Quot.sound`.

**Model calls as quantified inputs worked.** The model is a universally quantified
argument: a reply vector for SummariseItem, a `Host` instance for GenerateResponse. The
theorem holds whatever the model says, including adversarially, because nothing about
the model is assumed. This is the design's central idea, and no part of it needed
anything beyond plain Lean.

**Who wrote the proofs.** A subagent wrote them, with tools and Aeneas's skill files,
against statements it could not edit. A person did not, and a person's effort was not
measured. Its main difficulties, in its own report:
- **Aeneas's `loop` combinator.** Its own documentation calls loop support "less mature".
- **No partial-correctness loop rule.** The subagent wrote one, `loop_pc`, by strong
  induction.
- **`bind` inversion lemmas, written by hand.**
- **`MAX_ROUNDS` is irreducible.**

None of the statements was false.

## What the gate does and does not establish

- **A smoke test found a hole, and it is closed.** The first gate checked that
  `holds` built and named its axioms. A theorem named `holds` *of type `True`* passed.
  Both gates now elaborate `example : <statement> := <theorem>`. The lesson for a real
  gate: the check must be against the statement's term, never a name.
- **The statements are the specification, and they can be weak.**
  - `one_line_spec` admits an empty summary. A body returning `[]` satisfies it, so the
    pilot's body+proof arm runs the differential test beside the gate, as information.
  - `respond_spec`'s docstring says "no lookup without a model call before it", but the
    `Prop` says `lookups ≤ generates`, a count, not an order. The statement is pinned, so
    the gap is recorded here and not edited.
  - Both are instances of the design's open question: a proof is only as good as its
    statement, and **nothing yet checks that a statement says what its docstring
    claims.**
- **The trusted base:**
  - the shell that turns a core's choices into host calls;
  - the WIT bindings;
  - Charon and Aeneas;
  - Lean's kernel;
  - the differential tests, which tie each core to the shipped body on the inputs they
    try and no others.

## 5.2: the generation pilot

**Setup.**
- **Design:** `pilot/pilot.py`'s docstring, committed before any call (`0111255`).
- **Models:** Sonnet and Opus through the `claude` CLI on the Max subscription, with no
  tools. No paid API was used.
- **Statements:** supplied and pinned; the model could not change them.
- **Attempts:** five at most. A repair was shown only the gate's refusal.

**One amendment after 3 trials** (`18ca433`). An Opus call passed the default 600-second
timeout and stopped the run. Calls then got 30 minutes, and a failed call voids its
trial, recorded and never counted. One trial was voided this way: Opus, body+proof,
SummariseItem's summary, timed out at 1,800 seconds.

| arm | target | Opus | Sonnet |
|---|---|---|---|
| proof | DropSeen | 3/3 (attempts 3, 2, 2) | 3/3 (2, 5, 5) |
| proof | SummariseItem's summary | 3/3 (5, 4, 3) | 1/3 (3) |
| proof | GenerateResponse, every `Host` | 3/3 (5, 3, 4) | 1/3 (4) |
| body+proof | DropSeen | 3/3 (3, 3, 5) | 1/3 (5) |
| body+proof | SummariseItem's summary | 1/2 (3), 1 void | 1/3 (5) |
| **all** | | **13/14** | **7/15** |

**Accepted trials (18 of 29 counted):**
- **None was accepted on its first attempt.** Every success came after one or more repairs
  from the gate's refusal.
- **All 99 refusals were Lean build failures.** No Rust body failed Charon or Aeneas.
  None of the 99 tripped the forbidden-declaration scan or the axiom check.
- **Every accepted body+proof body agreed with the shipped body** on the differential
  test: 7 of 7. That test is information, not part of the gate. No body gamed
  `one_line_spec`'s admission of an empty summary.

**How to read it.** These are counts from a pilot, not rates:
- three trials per cell, one round, two models of one family, statements we supplied;
- the targets are small (the largest function, `respond`, is 26 lines of Rust; the whole crate is 174).

What it shows is that the loop works: an agent writes, the gate refuses with a reason,
the agent repairs, and the gate decides. Through that loop, the stronger model reached a
checked proof on all but one counted trial, including the theorem over every model.
Through the same loop, the gate was never fooled.

What it does not show:
- that statements can be generated (the gate's half, still by hand);
- how this scales to larger nodes;
- what a person would take.

## Recommendation

Propose a change, `add-proved-cores`. Proofs here cost tens of minutes of agent time per
node, the route needed no tool changes, and a model can carry the work through the
gate's feedback loop. The change would:
- generate statements from a node's contract and capability clause (the gate's half;
  S2's implication check is its inter-node complement);
- pin them, and accept a node only with a proof that `check.sh`'s rules accept;
- keep the differential test as the tie between core and shipped body until the shell
  itself is generated or proved;
- fold in S4's call bounds as conjuncts of the same statements.

The change's open problem is the statement itself. Both weaknesses found here were in
statements, not in proofs:
- an empty summary is admitted;
- a docstring claims more than its `Prop`.

Generating statements from contracts, and checking them against the prose, is where the
remaining risk sits. What a proof earns in the graph (design open question 2, deferred)
should be decided against that risk.
