# Change: Model write-capable and append-only database handles in the runtime

## Why
The runtime's `provision` models only `read`-mode `DBHandle`s (a deliberate slice for the security vertical,
which only reads the knowledge base). As a result the canonical `SupportPlatform` composition graph — the one
that motivates and demonstrates sub-graph capability-identity routing — can be *validated* and *rendered* but
not *assembled*: it declares `DBHandle<'billing', read-write>` and `DBHandle<'audit', append>`, and
`provision` raises on both. The graph-level identity routing added in `add-graph-level-capability-identity`
therefore had to be exercised end-to-end on a synthetic parent graph, while the shipped graph's own routing
went untested at the runtime. Modelling the two missing modes closes that gap: the shipped composition graph
assembles, and its declared `customer_session` / `billing_session` routing runs through the real runtime.

## What Changes
- Add two capability handles whose surface matches the declared `DBHandle` mode: a **read-write** handle
  (read *and* write operations) and an **append-only** handle (an append operation and **no** read — audit
  logs are write-once, never read back through the handle).
- Extend `provision` to build them: `DBHandle<scope, read-write>` and `DBHandle<scope, append>` provision
  their respective handles; an unrecognised mode still raises with a message naming the modes it knows.
- The canonical `SupportPlatform` graph becomes **assemblable**: every capability it declares is now
  provisionable, so a test can assemble it and assert the graph-declared `ResponseChannel<user-session>`
  identities route distinct instances to `CustomerSupport` and `BillingService` — the shipped graph, not a
  synthetic stand-in.
- Not in scope: sub-graph *execution* (the runtime still does not recursively execute sub-graphs, so
  `SupportPlatform` assembles but is not run); richer store semantics (transactions, key deletion,
  read-your-writes across handles); the sandbox tier for these handles; changing the validator's mode
  subtyping (`read-write ⊒ read` is already implemented and unchanged).

## Impact
- Affected specs: `signal-graph-runtime` (ADDED: the runtime provisions write-capable and append-only DB
  handles; the SupportPlatform composition graph assembles and routes identity end-to-end).
- Affected code: `poc/handles.py` (two new handle classes + `provision` cases), `tests/` (handle-surface and
  assembly tests), and — only if a claim needs adjusting — `proposal.typ` §5, which currently notes the
  demonstrator models only read-mode DB handles.
- Builds on: archived `add-graph-level-capability-identity` (the identity this change lets run end-to-end on
  the shipped graph) and `add-capability-identity` (the assembly-time routing).
