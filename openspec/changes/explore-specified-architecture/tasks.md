# Tasks

## 0. Approval

- [x] 0.1 After the Paper 4 work is finished, the author discusses this direction, approves
  it or amends it, and answers `design.md`'s open question 1: a prover as an external gate,
  for spikes only. Record the date and the answers here. Nothing below starts before this
  box is checked.

  **Approved by the author, 18 November 2026**, after a discussion grounded in the code.
  - **The Paper 4 gate is waived.** Paper 4 is drafted and reviewed; it waits on the
    author's read, not on work. Nothing here touches Paper 4's files, records or runs.
  - **Order amended: S1 first** (D3 now reads S1, S2, survey, S3, S4). Tasks keep their
    numbers; section 3 (S1) runs before section 2 (S2).
  - **Q1, a prover: yes, pre-approved.** Install or upgrade Lean (`elan`), Rust
    verification tooling (`rustup`/`cargo`) and similar in their usual home-directory
    locations without asking. Repo-side dependencies go in their own group, in no build
    step.
  - **Model calls: approved within the Claude Max subscription** (the author: quota to spare
    this week). This answers the approval task 5.2 waits on. No paid API spend.
  - **Q2 (what a proof earns): deferred** until S3 has numbers, as recommended.
  - **Q3 (prover): the survey decides.** The author leans to Lean, from prior experience and
    its weight in agent training data.
  - **Q4 (grammar form): left to the implementer.** Decided: handle-reached budgets are
    trailing scope arguments the parser already accepts, `LLMClient<inference, Calls<'5'>>`,
    `StateHandle<'seen', read-write, Bytes<'5242880'>>`, `HTTPClient<[...], Requests<'50'>>`
    (quoted numbers, as `Payments` writes its cap). Store-bounded budgets (fuel, memory, a
    deadline) are not reached through a handle, so they are a `budget` annotation on the
    node. S1 tests this split; S1's write-up may revise it.
  - The author asked that the work be pushed as far as it can go without them, asking only
    before a dangerous or one-way-door step. The archive still needs the author's go.

## 1. The direction note

- [x] 1.1 Write `docs/SPECIFIED-ARCHITECTURE.md` from `design.md`, covering:
  - the four strands;
  - the split between proved, enforced, and neither;
  - the treatment of model calls as quantified inputs.

  Link it from `docs/ROADMAP.md`. Verify: the author reads it.

  Written 18 November 2026 and linked from the roadmap (its 18 November entry). It keeps a
  table of what is proved, what is enforced and what is neither, filled in from the spikes.
  **The author has not read it yet**; the box is ticked for the writing.

## 2. S2: contracts that compose along edges

- [x] 2.1 In `spikes/specified-architecture/s2/`, write the implication check: per edge,
  and per variant on a sum. It must be stdlib-only. Run it over `graphs/*.json`.
  - Report: edges with contracts on both sides, edges that pass, and edges it cannot
    decide.
  - Verify: the spike's own tests include one edge that fails by construction.

  Done 18 November 2026 (25 checks, including `len(q) <= 600 ⇒ len(q) <= 512`, not
  implied, and `len(q) > 600 ⇒ len(q) <= 512`, contradicted). The corpus was widened with
  Paper 3's generation contracts.
  - **Over the graphs:** 6 requirement-edges; 3 discharged, 3 with no guarantee, 0
    undecided.
  - **The evaluator fuzz** (3,000 cases) found a soundness bug in the first draft, now
    fixed.
- [x] 2.2 Write up the result and a recommendation: propose a validator analysis, or stop.
  `s2/RESULT.md`. The finding: a guarantee does not survive a pass-through node, because
  the vocabulary cannot relate output to input. Recommendation: a stdlib validator
  analysis at warning strength (contradicted or vacuous are errors; unguaranteed
  preconditions are listed). The relational atom is deferred to S3.

## 3. S1: budgets as scopes

- [x] 3.1 In the spike directory, run one confined node with wasmtime fuel and an epoch
  deadline, and give one `LLMClient` a token scope. Verify:
  - an overrun is refused, and classed as budget exhaustion, never as an ungranted
    capability;
  - fuel's cost per crossing is measured against the crossing band.

  Done 18 November 2026 in `spikes/specified-architecture/s1/` (27 checks pass). Fuel and a
  deadline stop a runaway guest, classed `Fuel`/`Deadline`; `Calls` and `Tokens` scopes are
  metered at the backend, beneath the parent's meter. The crossing is 18–26 µs on all four
  engines (inside the band), and guest compute moves within noise. Found on the way:
  - fuel overshoots by one check interval (23–86 units);
  - a memory-limit refusal cannot be told from a guest panic in wasmtime-py;
  - shipped `uses` exhaustion is a `CapabilityError`.
- [x] 3.2 Write up the result and a recommendation, including the grammar form (open
  question 4). `s1/RESULT.md`: propose `add-resource-budgets` (trailing budget scopes,
  backend meters shared down the routing chain, fuel on the runtime engine with a deadline
  as backstop, totals as a later validator analysis).

## 4. Prior-art survey

- [x] 4.1 Add a survey section to `docs/PRIOR-ART.md`, covering:
  - proof-carrying code;
  - Verus, Aeneas/Lean, Kani, Creusot and Prusti;
  - RAML and amortised resource analysis;
  - KeyKOS/EROS meters and space banks;
  - current agent-written proof results, each cited.

  It ends in a prover recommendation for S3 and S4. Verify: every claim has a source.

  Done 18 November 2026: `docs/PRIOR-ART.md` §§20–25. The full survey, with sources and
  UNVERIFIED marks, is `docs/specified-architecture-survey.md`; a subagent wrote it, and I
  re-checked two load-bearing claims against their primary pages.
  - **Recommendation: Lean via Aeneas, on a pure core** pulled out of each node body (no
    prover takes wit-bindgen glue or `serde_json`). Verus is the fallback.
  - **S4 route:** call bounds as lemmas on effects-as-data; instruction counts stay with
    fuel.

## 5. S3 and S4: proofs

- [x] 5.1 S3, by hand: prove two or three deterministic nodes and one model-calling node
  with an effect against their contracts.
  - The model-calling node's theorem is quantified over every response its type admits.
  - Record the specification lines, the proof lines and the time spent, per node.

  Done 18 November 2026. Three pure cores were translated by Aeneas on the first attempt
  and proved; `s3/check.sh` ACCEPTED, with standard axioms only.
  - **The nodes:**
    - DropSeen (deterministic);
    - SummariseItem's summary, for every model reply (≤ `limit` code points, no line
      break);
    - GenerateResponse's tool loop, for every model and knowledge base (the model-calling
      node with effects).
  - **Statement lines** (in `Statements.lean`): about 6, 5 and 11.
  - **Proof lines:** about 114, 122 and 222, written by a subagent in about 10, 7 and 9
    minutes against statements it could not edit.
  - **Deviation:** the "hand" proofs were written by an agent with tools and the Aeneas
    skill files, not by a person. A person's effort was not measured.
- [x] 5.2 S3, generated (only with the author's approval, on the subscription, and with no
  paid spend): a small pilot in which the agent writes body and proof and the checker
  decides. Report counts.

  Done 18 November 2026 (`s3/pilot/`; design committed before any call, amended once
  after 3 trials for a call timeout).
  - **Accepted:** 20 of 29 counted trials, 1 void; Opus 13/14, Sonnet 7/15. None was
    accepted on its first attempt.
  - **Refused:** all 99 refusals were build failures, and nothing passed the gate
    improperly.
  - **Bodies:** every accepted body+proof body agreed with the shipped one (6/6).
  - **Reading:** pilot counts, not rates.
- [x] 5.3 S4: for one node, prove a bound on the number of crossings, and compare it with
  the trace over the contract's inputs. Report every excess.

  Done 18 November 2026 (`s4/RESULT.md`).
  - **The proof:** GenerateResponse makes at most 3 model calls and at most 3 lookups,
    for every `Host`, that is, every model. It is part of `respond_spec`.
  - **The trace check:** over 81 reply scripts on the unchanged component, at most 6
    crossings; the bound is reached, with 0 excesses and 0 sequence mismatches with the
    core.
  - **Finding:** proved calls times an enforced per-call cost needs a per-call output
    cap, which the CLI backend lacks.
- [x] 5.4 Write up S3 and S4, each with a recommendation.

  Done 18 November 2026.
  - **`s3/RESULT.md`:** propose `add-proved-cores`. The open risk is in statements, not
    proofs.
  - **`s4/RESULT.md`:** fold call bounds into that change, and name a per-call output cap
    as the missing piece of a token bound.
  - **`docs/SPECIFIED-ARCHITECTURE.md`:** strand table and findings updated.

## 6. Close

- [ ] 6.1 The end condition: every spike has a written result, and the author has decided
  on each recommendation (propose a change, or stop). Record the decisions here. Run
  `make build` and `make spec-check` (both green), then archive with the author's go.
