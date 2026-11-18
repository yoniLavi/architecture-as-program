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
- **`check.sh` accepts a proof file only if** (its header has the detail):
  - a text scan finds no forbidden construct;
  - the pinned code builds before the proof does;
  - the proof builds inside a sandbox with no network and no writes outside the build
    directory, and the compiled statements are unchanged afterwards;
  - a separate audit process, which never elaborates the proof file, finds each
    theorem's type to be exactly its statement constant, its axioms within Lean's
    standard three, and every constant outside Aeneas re-accepted by the kernel.

  This is the second gate. The first was fooled by the adversarial review (see "What
  the gate does and does not establish").

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

- **Two holes were found in the first gate, and both are closed.**
  - **A smoke test found the first.** A theorem named `holds` *of type `True`* passed.
    The fix checks against the statement's term, never a name.
  - **The adversarial review found the second, which was worse.** It got `sorry`
    proofs ACCEPTED by both the first `check.sh` and the pilot's gate, in two steps:
    - The proof file redefined `#print axioms` with `macro_rules`. The axiom check
      imported the proof file, so it ran under the proof's own syntax.
    - The pilot's `\bsorry\b` scan does not match `sorryAx`.
  - **The review also showed a proof file runs code at build time.** An `#eval` wrote a
    file during `lake build`.
  - **The fix is above:** a sandboxed build, the compiled statements re-hashed, and an
    audit in a separate process over the compiled environment (`audit/Audit.lean`).
    - Re-run on the review's attack files: the `sorry`s are reported as `sorryAx` and
      refused, and the `#eval` write is denied by the sandbox.
    - The audit's first draft was itself unsound. It walked only definitions' values,
      not theorems', so it would have missed a `sorry` inside the proof. It was caught
      because it reported one axiom where `#print axioms` reported three.
  - **The lessons for a real gate:**
    - Check what the kernel holds, not what a file prints.
    - Never load the proof's syntax into the checker.
    - Treat the build as running untrusted code.
- **The statements are the specification, and they can be weak.**
  - `one_line_spec` admits an empty summary. A body returning `[]` satisfies it, so the
    pilot's body+proof arm runs the differential test beside the gate, as information.
  - `respond_spec`'s docstring says "no lookup without a model call before it", but the
    `Prop` says `lookups ≤ generates`, a count, not an order. The statement is pinned, so
    the gap is recorded here and not edited.
  - **`respond_spec` does not state the tool-scope property, and this is the
    security-relevant gap** (found by the adversarial review).
    - `Effect.Lookup` carries no tool name, and the only clause about tools is "a
      refused tool is never the granted one". So a body that looks up *whatever tool
      the model names*, and never refuses, satisfies the statement as long as the
      counts hold.
    - The shipped body does refuse ungranted tools (the differential test and S4's
      trace check exercise this), but the proof does not say so.
    - A statement that does would put the tool in the effect (`Lookup tool`) and add
      "every lookup's tool is the granted one". That needs the core's effect type
      changed and the proof redone, so it is the change's work, not a spike edit.
  - **`respond_spec` is partial correctness.** A body that always fails, or never
    returns, satisfies it. The other two statements use the total-correctness triple.
  - All of these are instances of the design's open question: a proof is only as good as its
    statement, and **nothing yet checks that a statement says what its docstring
    claims.**
- **The trusted base:**
  - the shell that turns a core's choices into host calls;
  - the WIT bindings;
  - Charon and Aeneas, and Aeneas's Lean library (which defines `⦃ ⦄` and is not
    re-checked by the audit's replay);
  - the lakefile, manifest and toolchain pin, which the hash does not cover (the prover
    cannot edit them, but they are trusted);
  - macOS `sandbox-exec`, which is deprecated;
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
SummariseItem's summary, timed out at 1,800 seconds. The trial interrupted by the first
timeout was re-run from scratch after the amendment. Any attempts it had made were
discarded unrecorded.

| arm | target | Opus | Sonnet |
|---|---|---|---|
| proof | DropSeen | 3/3 (attempts 3, 2, 2) | 3/3 (2, 5, 5) |
| proof | SummariseItem's summary | 3/3 (5, 4, 3) | 1/3 (3) |
| proof | GenerateResponse, every `Host` | 3/3 (5, 3, 4) | 1/3 (4) |
| body+proof | DropSeen | 3/3 (3, 3, 5) | 1/3 (5) |
| body+proof | SummariseItem's summary | 1/2 (3), 1 void | 1/3 (5) |
| **all** | | **13/14** | **7/15** |

**Accepted trials (20 of 29 counted):**
- **None was accepted on its first attempt.** Every success came after one or more repairs
  from the gate's refusal.
- **All 99 refusals were Lean build failures.** No Rust body failed Charon or Aeneas.
  None of the 99 tripped the forbidden-declaration scan or the axiom check.
- **All 20 accepted proofs still pass the hardened gate** (`pilot/reaudit.py`,
  `pilot/reaudit.json`).
  - **Method:** each trial's final reply, re-translated where the model wrote the
    body, through the sandboxed build, the olean pin and the separate audit. No model
    was called.
  - **Why it was needed:** the pilot's own gate could have been fooled. The re-audit,
    together with the review's inspection of the 20 files (no command-level macro,
    `#eval` or `sorryAx`), is what supports "no model gamed the gate". The pilot's gate
    alone does not.
- **Every accepted body+proof body agreed with the shipped body** on the differential
  test: 6 of 6. That test is information, not part of the gate. No body gamed
  `one_line_spec`'s admission of an empty summary.

**How to read it.** These are counts from a pilot, not rates:
- three trials per cell, one round, two models of one family, statements we supplied;
- the targets are small (the largest function, `respond`, is 26 lines of Rust; the whole crate is 174).

What it shows is that the loop works: an agent writes, the gate refuses with a reason,
the agent repairs, and the gate decides. Through that loop, the stronger model reached a
checked proof on all but one counted trial, including the theorem over every model.
No accepted proof gamed the gate. That rests on the hardened re-audit, not on the gate
the pilot ran, which the adversarial review showed could be fooled.

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
