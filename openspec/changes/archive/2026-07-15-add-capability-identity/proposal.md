# Change: Make per-node capability identity expressible at the graph boundary

## Why
The runtime provisions **one handle per capability *type***, shared across every node whose `with`
clause names that type: two nodes each declaring `DBHandle<'knowledge-base', read>` receive the *same
object*. For read-only handles this is harmless, and the archived runtime change said so. For
**stateful, rate-limited, or revocable** handles it is wrong — two nodes that should have independent
rate limits, or one of which should be revocable without affecting the other, cannot be distinguished.

The sandbox tier **narrowed** this but did not close it: each WASM instance has its own import table,
so the host functions backing a node's capabilities are per-instance even when the underlying handle
object is shared. Instance isolation gives per-node *binding*; what is still missing is a way to say,
at the graph boundary, that two same-typed capabilities are **distinct instances** — capability
*identity*, not merely capability *type*. Technical Note A ("Hierarchical capability routing") flags
this and links it directly to the revocation question.

## What Changes
- Make capability **identity** expressible at the graph boundary, so that distinct instances of the
  same capability type can be provisioned and routed to specific nodes.
- Stop provisioning from **collapsing identity by type**: when identity is specified, two nodes
  declaring the same capability type receive *distinct* handle instances rather than a shared one.
- Preserve the current type-only behaviour as the default for capabilities where identity does not
  matter (read-only handles), so simple graphs are unaffected.
- Lay the groundwork for revocation and rotation (a separate later change): a revocable handle needs a
  nameable identity to revoke.

## Impact
- Affected specs: `signal-graph-runtime` (ADDED: capability identity is expressible at the graph
  boundary; same-typed capabilities are not silently aliased when identity is specified).
- Affected code: `poc/graph.py` (provisioning keyed by identity, not only type), the runtime's
  capability-routing, and possibly `graphs/schema.json` if identity is spelled in the graph JSON. The
  sandbox host already gives per-instance import tables, so much of the binding machinery exists.
- Proposal feedback: Technical Note A "Hierarchical capability routing" and "Capability revocation and
  rotation".
- Not in scope: revocation/rotation itself (a distinct later change this one enables); the full
  hierarchical-routing design for sub-graphs (named slots vs structural matching), beyond what naming
  identity requires.

## Notes on what is deliberately left open (design.md)
The **surface** by which identity is expressed — named capability slots, opaque identity tokens, or
structural matching on capability instances — is an open Phase 1 language-design question. This change
specifies the *outcome* (distinct instances are routable and not aliased) and picks the smallest
surface that demonstrates it, leaving the richer routing designs to a later hierarchical-routing
change.
