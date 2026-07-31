# Change: A minimal contract language for node signatures

## Why

Behavioural contracts are the mechanism that is supposed to make AI-generated node implementations
verifiable and interchangeable. The demonstrator has none — it holds node bodies to tests, which is
not the same thing, and Paper 2 says so. This bounds the code-as-compiled-artifact claim directly and
blocks the roadmap's generation experiment, which needs something for a generated body to be checked
*against* beyond "it compiled".

The July 2026 survey (`docs/PRIOR-ART.md`) settled the weight class. Dafny, Lean and F\* are the wrong
end of the spectrum for this. The right precedents are Racket's contracts (whose load-bearing idea is
**blame**: a precondition violation blames the caller, a postcondition the callee), Clojure's
`spec/fdef` (checked both by runtime instrumentation and generatively), and `icontract-hypothesis`
(which *derives* a property-based-test strategy from the precondition, so a contract is written once
and used twice).

## What Changes

- Nodes may carry `requires` and `ensures` in the graph JSON: conjunctions of predicates over field
  paths of the node's already-typed input and output records, reusing `scripts/type_parser.py` rather
  than introducing a second grammar.
- The predicate vocabulary is **deliberately closed**: comparisons, membership in a declared variant
  set, and field presence. No quantifiers, no recursion, no arbitrary code. That ceiling is what keeps
  this a contract rather than a refinement type, and it is what makes the checker small enough to stay
  dependency-free.
- The executor evaluates `requires` before invoking a node body and `ensures` after, raising a
  violation that carries **blame**: a failed `requires` blames the upstream wiring, a failed `ensures`
  blames the node body. Violations surface as a new `contract_violation` reason class, so the
  evaluation harness's existing reason-class pinning applies unchanged.
- The validator rejects a contract referring to a field the node's declared types do not have — a
  contract that cannot be evaluated is a graph error, not a runtime surprise.

## Impact

- Affected specs: `signal-graph-runtime` (one ADDED), `evaluation` (one ADDED)
- Affected code: new `poc/contracts.py`, `poc/runtime.py`, `graphs/schema.json`,
  `scripts/graph_validator.py`, `poc/evaluate.py`, tests
- Affected papers: Paper 2 §3 gains the contract layer; §7.5's "no contract language" narrows to what
  the closed vocabulary cannot express
- Out of scope for this change: the **generative** mode (deriving Hypothesis strategies from
  preconditions). It needs a new dependency in the `poc` group and is only worth building once the
  generation experiment needs it; recorded in `docs/ROADMAP.md` as part of M3.
