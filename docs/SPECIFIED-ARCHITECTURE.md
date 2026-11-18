# The graph as specification: contracts, proofs and budgets

*A direction note for `openspec/changes/explore-specified-architecture`. The direction is
the author's (17 November 2026), and was approved with S1 leading (18 November 2026). This
note is the standing statement; each strand's evidence lives in
`spikes/specified-architecture/<strand>/RESULT.md`, and the prior art in
`docs/PRIOR-ART.md` §§20–25.*

## The direction

So far the signal graph has been argued as a **security policy**:
- the `with` clause sets a node's import surface;
- the trust lattice sets where untrusted data may go;
- scopes set what a handle admits.

The direction is to make the graph the **specification** as well. Each node would carry:
- **what it must do:** invariants, pre- and postconditions, possibly backed by a proof the
  gate checks without trusting whoever wrote it (proof-carrying code);
- **what it may consume:** model cost, CPU, wall-clock time, memory, storage and network.
  Each is enforced at run time, and bounded by proof where a bound can be proved.

This reaches the north star at step 5 (`docs/ROADMAP.md`). An AI developer who writes a
node would hand over a body, a proof that the body meets its contract, and a body that
runs within its budget. The gate checks all three.

## Three kinds of claim, kept apart

Every result in this direction says which kind of claim it is making.

| | Proved (a checked certificate) | Enforced (refused at run time) | Neither |
|---|---|---|---|
| **Safety of effects** | "For every model reply r, every payment is in scope" (S3) | The handle's scope, at the crossing (shipped) | That the effect is the one the user wanted (utility) |
| **Number of calls** | `(decide …).length ≤ k` (S4) | A `Calls` budget, metered at the backend (S1) | — |
| **Tokens and cost** | — (depends on the model) | A `Tokens` budget; may overrun by at most one call (S1) | The exact cost of a run |
| **Instructions** | — (no checkable certificate exists; PRIOR-ART §23) | Fuel, deterministic, overshooting by one check interval (S1) | — |
| **Wall-clock time** | — (depends on machine and load) | An epoch deadline, as a backstop only (S1) | Any reproducible figure |
| **Memory** | — | A store limit; its refusal looks like a guest panic (S1) | Which of the two it was |
| **Wiring** | Producer `ensures` ⇒ consumer `requires`, per edge (S2) | The `requires` check (shipped) | Guarantees across a pass-through node (S2) |

## Model-calling nodes are in scope for safety proofs

The author corrected an earlier framing on 17 November 2026. Treat the model's reply as
any external input: a value quantified over everything its type admits.

**What can be proved:**
- **For every response:** "for every reply r, the node's effects satisfy Q". Nothing about
  r needs to be known, as for a parser over attacker-supplied bytes. A typed boundary keeps
  this tractable, because the possible replies are the type's values, not arbitrary bytes.
- **Conditionally:** "if r satisfies P, the effects satisfy Q", paired with a run-time
  check of P, the pattern a contract's `requires` already follows.

**What cannot be proved:** that the reply is the right one, meaning that the node achieved
the user's goal. That is utility, not safety. The free-text residual is the security face
of the same gap: a proof shows the effect is within bounds, not that it is the effect the
user wanted.

**How the survey makes this concrete.** Prove a **pure core** that takes every host result
as an argument, the reply included, and returns its effects as data. The quantifier is
then a literal argument of the theorem, and a call bound is a lemma about the length of a
list.

## The strands

| Strand | Question | Status |
|---|---|---|
| S1 | Budgets as capability scopes | Done (18 November 2026): recommend `add-resource-budgets` |
| S2 | Contracts that compose along edges | Done (18 November 2026): recommend a warning-strength validator analysis |
| Survey | Provers, agent-written proofs, resource bounds | Done (18 November 2026): Lean via Aeneas on a pure core |
| S3 | Proofs of node bodies | Done (18 November 2026): three nodes proved and gate-accepted; in a pilot, models reached accepted proofs in 18 of 29 counted trials, never on a first attempt; recommend `add-proved-cores` |
| S4 | Proofs of resource bounds | Done (18 November 2026): a call bound proved for every model, with no excess on the shipped component; fold into S3's change |

**What has been found so far:**
- **Budgets are spent, not narrowed like sets** (D5). They need meters shared down the
  routing chain, as in KeyKOS, and the meter belongs on the backend, because confined
  adapters bypass the handle.
- **Contract guarantees do not survive a node,** because the vocabulary cannot relate a
  node's output to its input. A proof can carry that relation, which is one reason S3
  matters for S2.
- **Model calls as quantified inputs work in plain Lean** (S3). A theorem over every
  reply, or every `Host`, assumes nothing about the model.
- **A gate must check a proof against the statement's term, not a name.** A theorem named
  `holds` of type `True` passed the first gate.
- **A pinned statement can say less than its prose.** One said `lookups ≤ generates`
  where its docstring claimed an order. Nothing yet checks that a statement means what
  its docstring says.
- **A proved call count times an enforced per-call cost needs a per-call output cap**
  (S4). The CLI backend has none.

## The limits every result states

- **Trusted base:**
  - the Rust compiler;
  - the translation into the prover (Charon and Aeneas), which is differential-tested;
  - the WIT bindings;
  - the host adapter;
  - the `run` shell around the proved core;
  - the host model of each capability.
- **Specification:** a proof is only as strong as its postcondition. The gate, not the
  agent, generates each theorem statement, and pins it by hash.
- **The tiers:** everything enforced is enforced on the confined tier. On the host tier it
  is host discipline, as every scope is.
- **Counts, not rates.** The proof corpus is small and chosen, as the mutation corpus is.
