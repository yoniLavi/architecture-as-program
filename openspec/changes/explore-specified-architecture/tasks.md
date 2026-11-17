# Tasks

## 0. Approval

- [ ] 0.1 After the Paper 4 work is finished, the author discusses this direction, approves
  it or amends it, and answers `design.md`'s open question 1: a prover as an external gate,
  for spikes only. Record the date and the answers here. Nothing below starts before this
  box is checked.

## 1. The direction note

- [ ] 1.1 Write `docs/SPECIFIED-ARCHITECTURE.md` from `design.md`, covering:
  - the four strands;
  - the split between proved, enforced, and neither;
  - the treatment of model calls as quantified inputs.

  Link it from `docs/ROADMAP.md`. Verify: the author reads it.

## 2. S2: contracts that compose along edges

- [ ] 2.1 In `spikes/specified-architecture/s2/`, write the implication check: per edge,
  and per variant on a sum. It must be stdlib-only. Run it over `graphs/*.json`.
  - Report: edges with contracts on both sides, edges that pass, and edges it cannot
    decide.
  - Verify: the spike's own tests include one edge that fails by construction.
- [ ] 2.2 Write up the result and a recommendation: propose a validator analysis, or stop.

## 3. S1: budgets as scopes

- [ ] 3.1 In the spike directory, run one confined node with wasmtime fuel and an epoch
  deadline, and give one `LLMClient` a token scope. Verify:
  - an overrun is refused, and classed as budget exhaustion, never as an ungranted
    capability;
  - fuel's cost per crossing is measured against the crossing band.
- [ ] 3.2 Write up the result and a recommendation, including the grammar form (open
  question 4).

## 4. Prior-art survey

- [ ] 4.1 Add a survey section to `docs/PRIOR-ART.md`, covering:
  - proof-carrying code;
  - Verus, Aeneas/Lean, Kani, Creusot and Prusti;
  - RAML and amortised resource analysis;
  - KeyKOS/EROS meters and space banks;
  - current agent-written proof results, each cited.

  It ends in a prover recommendation for S3 and S4. Verify: every claim has a source.

## 5. S3 and S4: proofs

- [ ] 5.1 S3, by hand: prove two or three deterministic nodes and one model-calling node
  with an effect against their contracts.
  - The model-calling node's theorem is quantified over every response its type admits.
  - Record the specification lines, the proof lines and the time spent, per node.
- [ ] 5.2 S3, generated (only with the author's approval, on the subscription, and with no
  paid spend): a small pilot in which the agent writes body and proof and the checker
  decides. Report counts.
- [ ] 5.3 S4: for one node, prove a bound on the number of crossings, and compare it with
  the trace over the contract's inputs. Report every excess.
- [ ] 5.4 Write up S3 and S4, each with a recommendation.

## 6. Close

- [ ] 6.1 The end condition: every spike has a written result, and the author has decided
  on each recommendation (propose a change, or stop). Record the decisions here. Run
  `make build` and `make spec-check` (both green), then archive with the author's go.
