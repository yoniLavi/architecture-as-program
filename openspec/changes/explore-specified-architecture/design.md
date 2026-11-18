# Design

## Context

See `proposal.md` (Why) for the direction and the machinery measured at `9b710ff`. This
document sets out the four strands, the questions a spike must answer for each, and the
decisions the author must make. It is a direction, not a plan of record: each strand that
survives its spike becomes its own change.

## Goals / Non-Goals

**Goals:**
- State each strand precisely enough that a spike can confirm or refute it.
- Separate what could be **proved** from what can only be **enforced** at run time, and
  both from what is **neither**.
- Keep the repo's disciplines: counts rather than rates, limits stated first, and no paper
  claim ahead of an artifact.

**Non-Goals:**
- Building any strand beyond its spike.
- Picking provers or papers before the survey and the spikes.

## The strands

### S1. Budgets as capability scopes, enforced at run time

Almost every resource a node uses is reached through a handle. A budget becomes one more
scope on the handle's type:
- `LLMClient<inference, tokens ≤ N>`: tokens or cost, counted at the crossing;
- `StateHandle<'name', read-write, ≤ 5MiB>`: storage, checked at each write;
- `HTTPClient<[...], ≤ 50 requests, ≤ 10MiB>`: network.

CPU, memory and wall-clock time are not reached through a handle. On the confined tier the
store bounds them instead: fuel for instructions, an epoch deadline for wall-clock time,
and store limits for memory.

- **Composition:** a child's budget fits within its parent's. The validator checks this
  as narrowing, and the routing-point facades enforce it.
- **Graph totals:** add along a path, take the maximum over exclusive branches, and
  multiply by the list's length under `each`. A per-item map therefore needs a bound on
  that length.
- **Limit, the same as the security results:** the host tier cannot enforce CPU,
  memory or time against a hostile body; it follows them by discipline.
- **Prior art:** KeyKOS/EROS meters and space banks, where CPU time and storage were
  themselves capabilities.

**Spike:** add fuel and an epoch deadline to one confined node, and a token scope to one
`LLMClient`.
- Show that an overrun is refused at the crossing or the store. Show that the refusal is
  classed as a budget exhaustion, never as an ungranted capability (the same rule the
  engine config states for resource failures).
- Measure what fuel metering costs per crossing, against the band of `CROSSING_BAND_*`.

### S2. Contracts that compose along edges

Each node already has `requires`/`ensures` in a closed vocabulary.
- **Check:** for each edge A→B, A's `ensures` implies B's `requires`.
- **Decidability:** the vocabulary is comparisons, set membership, presence and `len` over
  paths, with no quantifiers and no arithmetic. Implication between conjunctions of such
  atoms is decidable with interval and set reasoning alone, so the check stays stdlib-only
  and needs no solver. The spike confirms this or finds the case that breaks it.
- **What it would prove:** the wiring is consistent. A run-time contract failure then
  indicts a body, never the graph.
- **Sum types:** with variants on an edge, the implication must hold per variant.

**Spike:** write the implication check over the canonical graphs and the feed-triage
graphs. Report how many edges have contracts on both sides, how many pass, and every edge
it cannot decide.

### S3. Proofs of node bodies, model-calling nodes included

A node ships a proof that its body meets its contract, and the gate checks the proof
without trusting whoever wrote it (proof-carrying code). This extends Paper 3's gate from
"what does it import" to "what does it do".

**Model-calling nodes (the author's correction, 17 November 2026).** An earlier framing
said these could not be proved correct. That conflated two properties:
- **Provable, for every response:** treat the model's response as any external input, a
  value quantified over everything its type admits. A theorem then reads "for every
  response r, the node's effects satisfy Q": every payment is in scope, every write
  within budget, at most k calls. Nothing about r needs to be known, exactly as for a
  parser over attacker-supplied bytes. Typed boundaries make this tractable, because the
  set of possible responses is the type's values, not arbitrary bytes.
- **Provable, conditionally:** "if r satisfies P, the effects satisfy Q". This is paired
  with a run-time check of P, the pattern a contract's `requires` already follows.
- **Not provable:** that the response is the right one, meaning that the node achieved
  the user's goal. This is utility, not safety. The free-text residual (adversarial
  content in a permitted field) is the security face of the same gap: the proof shows the
  effect is within bounds, not that it is the effect the user wanted.

So model-calling nodes are in scope for safety proofs, and they are where such a proof is
worth most. This matches how the security argument already treats them, extended from
"what the node can touch" to "what the node does with what it touches".

**Limits to state in any result:**
- **What is trusted:** the compiler, the translation into the prover, the WIT bindings
  and the host adapter.
- **Specification:** a proof is only as strong as its postcondition, so whoever writes the
  postcondition sets how much the proof is worth.

**Questions for the survey:**
- Verus (proofs in Rust) or Aeneas (Rust into Lean)? A Rocq route as well? Which has
  agent-written proofs that a checker accepts at a useful rate?
- Can the closed contract vocabulary translate mechanically into the prover's
  postconditions, so the graph stays the single source?

**Spike:** pick two or three deterministic nodes and one model-calling node with an
effect (a payment writer, or the feed digest's notifier). Write the proof by hand first,
to measure the specification and proof effort. Then, only with the author's approval,
run a small generation pilot on the subscription in Paper 3's style: the agent writes body
and proof, and the checker decides.

### S4. Proofs of resource bounds

Some bounds can be proved and some cannot:
- **Provable:** the number of handle calls a node makes, and its instruction and
  allocation counts as a function of input size. Resource-aware type systems (RAML,
  Hoffmann's amortised analysis) are the prior art.
- **Not provable:** wall-clock time (it depends on the machine and on contention; the
  benchmark's history in this repo is the evidence) and token cost (it depends on the
  model).
- **Combined guarantee:** prove the count of calls, enforce the cost of each call at run
  time (S1), and the product is the bound. For example, "at most 3 inference calls"
  (proved) times "at most 4k tokens per call" (enforced) gives at most 12k tokens.

**Spike:** for one node, prove a bound on the number of crossings, and check it against
the trace's call layer over the contract's inputs. Count cases where the trace exceeds
the bound (a proof bug, or a trusted-base bug).

## Decisions

**D1. One direction note now, separate changes later.** A change per strand now would
open four changes for ideas none of which has been tested. This change holds the direction
and the spikes, and each strand graduates on its spike's result.

**D2. Spikes live outside `poc/` and `scripts/`.** In `spikes/specified-architecture/`, no
build step imports them, the Paper 2–4 pins cannot move, and the validator stays
stdlib-only. A prover is installed in its own dependency group.

**D3. The order is S1, S2, the survey, S3, then S4** (amended at approval, 18 November
2026; it was S2 first).
- S1 is cheap and demonstrable, and reuses the narrowing machinery the routing point
  enforces.
- S2 is stdlib-only, but the canonical graphs give it two edges with contracts on both
  sides, one of them non-trivial, so it runs second and widens its corpus.
- S3 and S4 depend on the survey's choice of prover.

**D5. Budgets do not narrow as sets do** (added at approval). Set scopes can be granted
twice and still mean the same thing; budgets are spent. Two children may each declare
`≤ N` under a parent's `≤ N` and pass narrowing while together spending 2N. So a budget
has three parts, kept apart in every result:
- *narrowing*, the existing machinery;
- *metering*, one counter held by the parent's handle (or the backend), which every facade
  shares, so the parent's total holds at run time;
- *totals*, a new static analysis (add along a path, maximum over exclusive branches,
  multiply under `each`), which narrowing does not give.

**D4. A proof is offered, not required, at least to start.** In this proposal a proof is a
certificate a node may carry. What it earns (lower review, larger budgets, running without
a run-time contract check) is open question 2. Requiring one before the spikes show the
cost would make it a tax with no measured price.

## Risks / Trade-offs

- **Specifications become the new bottleneck.** → Every spike result records how many
  lines of specification each proof needed, and who wrote them.
- **The dependency ceiling moves.** Lean or Verus is a large dependency. → It stays an
  external gate, as `wasmtime` is for the confined tier. The validator and the contract
  checker stay stdlib-only (open question 1).
- **Results flatter the method.** Deterministic nodes are easy to prove. → S3 includes a
  model-calling node with an effect from the start, and reports each node separately.
- **Scope pressure on Paper 4.** → Nothing here starts before the Paper 4 work is finished
  (task 0.1).

## Migration Plan

None. Nothing ships from this change.

## Open Questions

Answered at approval, 18 November 2026 (task 0.1): 1 yes, pre-approved; 2 deferred; 3 the
survey decides (the author leans to Lean); 4 decided by the implementer (scopes for
handle-reached budgets, a node annotation for store-bounded ones). The questions as posed:

1. *(for task 0.1)* May a proof toolchain enter the repo as an external gate, in its own
   dependency group and in no build step? Recommended **yes** for spikes only. Whether it
   ever joins the build is decided with S3's result.
2. *(for a later change)* What a proof earns a node: lower review, larger budgets, or
   dropping the run-time check of the proved contract. Recommended to defer until S3 has
   numbers.
3. *(deferrable)* Lean or Rocq, Verus or Aeneas. The survey answers it.
4. *(deferrable)* Whether budgets appear in the type grammar, as scopes, or as a separate
   annotation on the node. S1's spike tries scopes first, because narrowing then comes
   free.
