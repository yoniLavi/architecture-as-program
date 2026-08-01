- [x] `poc/contracts.py`: closed vocabulary (comparison, variant membership, presence, `len`),
      parsing, blame, and path resolution
- [x] `requires`/`ensures` on nodes in `graphs/schema.json`
- [x] Validator rejects a predicate outside the vocabulary; assembly rejects one that cannot parse
- [x] Executor brackets each node body — preconditions before, postconditions after, blame attached
- [x] `unevaluatable_contract` corpus variant, pinned to its own `contract` reason class
- [x] Nine tests: the four permitted forms, the rejected ones, blame on both sides, where each
      failure lands, and that graphs without contracts are untouched
- [x] Paper 2 §3.6 reports it; §7.5 narrows "no contract language" to checked-not-verified plus the
      vocabulary ceiling
