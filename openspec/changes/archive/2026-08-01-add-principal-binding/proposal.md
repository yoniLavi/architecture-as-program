# Change: Bind capabilities to a principal, and record it on every crossing

## Why

User-level authorisation is the largest undesigned item in the corpus, and the confused-deputy
attenuation argument depends on it entirely: capabilities are supposed to be bound at the graph
boundary to the calling user's credentials and propagated downstream, so a node acts only within that
user's authorised scope. Nothing implements this, so the argument rests on prose.

The July 2026 survey (`docs/PRIOR-ART.md`) supplied the shape of the answer. Every system that keeps
delegation *reasoned about* — Cedar's analysable fragment, Biscuit's append-only Datalog attenuation,
IAM's policy intersection — restricts the narrowing operation to something decidable and monotone;
those taking unrestricted dynamism (UCAN chains, Zanzibar's live tuple store) make the authority
topology unknowable until run time. That is exactly the trade already made for trust, which means the
design generalises rather than needing invention: **keep the topology static and validator-checked,
let the values be dynamic, restrict narrowing to a monotone operation.**

## What Changes

- A run binds a **principal** at assembly (`assemble(..., principal=...)`), representing the
  authenticated user on whose behalf the graph runs. Absent, behaviour is exactly as today.
- A node may declare `binds_principal: true` in the graph JSON, mirroring `discharges_trust`: it is
  the sole node kind licensed to **rebind** the acting principal — a genuine, auditable
  acting-on-behalf-of hop, visible in the graph source rather than hidden in node logic.
- Every other node may only **narrow**, never widen or rebind. Narrowing is intersection over fixed
  dimensions, not an open predicate language — the restriction that keeps it enumerable.
- Capability crossings record the acting principal in the shape of the delegation chain of RFC 8693:
  `{principal, acting_as: [...]}`. This is what converts the confused-deputy claim from prose into a
  pinned test: **no crossing anywhere in a run, including nested sub-graph runs, may record a
  principal outside the scope bound at entry unless it passed through a declared binder.**
- The validator rejects `binds_principal` on a node holding no capabilities, and rejects a graph
  declaring a principal-scoped capability with no binder upstream.

## Impact

- Affected specs: `signal-graph-runtime` (two ADDED requirements), `trust-typing` (one ADDED)
- Affected code: `poc/graph.py`, `poc/handles.py`, `poc/trace.py`, `poc/trace-schema.json`,
  `graphs/schema.json`, `scripts/graph_validator.py`, tests
- Affected papers: §3.4 and §7.5 of Paper 2 — the open problem narrows to what remains
- Deliberately out of scope: putting the principal scope into the **type grammar**
  (`DBHandle<'orders', read-write, ScopedTo(u)>`). That is the fuller design and would change the
  parser, the emitted grammar, and every capability annotation in the canonical graphs. This change
  implements principal binding at the instance and trace level, which is what makes the claim
  testable; the type-level form stays an open problem and must be reported as one.
