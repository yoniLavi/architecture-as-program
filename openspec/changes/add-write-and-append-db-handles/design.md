## Context
`provision(cap_type, ...)` in `poc/handles.py` maps a capability type string to a handle instance whose
*surface* is the enforcement (a `ReadDBHandle` has no `write`, sinks have no `read`). Today the `DBHandle`
branch accepts only `read` and raises on every other mode. The two canonical graphs diverge here:
`customer-support.json` uses only `read`, so it assembles and runs; `support-platform.json` also declares
`read-write` and `append`, so it validates and renders but cannot be assembled. This change adds the two
missing handles so the composition graph assembles.

## Goals / Non-Goals
- **Goals:** a read-write DB handle and an append-only DB handle whose surfaces match their modes; `provision`
  builds both; `SupportPlatform` assembles; the shipped graph's declared identity routing is tested through
  the real runtime.
- **Non-Goals:** sub-graph *execution* (unchanged — the runtime does not recurse into sub-graphs); rich store
  semantics (transactions, deletes, cross-handle read-your-writes); sandbox-tier versions of these handles;
  any change to the validator's mode subtyping (already correct).

## Decisions
- **Decision: the append handle exposes append and *no* read.** Audit stores are write-once: a node that can
  append must not thereby be able to read the log back. Modelling `append` as append-only keeps the
  least-authority discipline the other handles follow (`ReadDBHandle` has no `write`; `ResponseChannel` /
  `EventEmitter` are write-only), and makes the mode lattice's incomparability of `read` and `append`
  (documented in proposal §5) concrete at the surface: neither handle's operations are a superset of the
  other's. A test asserts the append handle has no `read`, mirroring `test_read_db_handle_has_no_write_method`.
- **Decision: the read-write handle owns a private copy of its store.** `write` mutates, so the handle
  deep-copies the (list-valued) store slice at provision time rather than aliasing the shared `stores`
  mapping — one graph's writes must not leak into another assembly's view. `ReadDBHandle` can keep its
  shallow copy because it never mutates.
- **Decision: keep the store/operation model minimal.** `read(key) -> list[str]` and
  `write(key, value)` (append a record to that key's list) for read-write; `append(record)` for the
  append-only log. This is the smallest surface that lets `write`-then-`read` be observable and the append
  log be inspectable in tests, matching the existing handles' modesty. Richer semantics are out of scope.
- **Decision: an unknown mode is a loud error naming the known modes.** The `DBHandle` branch dispatches on
  `read` / `read-write` / `append` and otherwise raises `ValueError` listing them, replacing today's
  "models only read-mode" message. Fail-closed on an unmodelled mode rather than silently picking one.

## Risks / Trade-offs
- **Surface creep on `handles.py`.** Two new classes. → Kept minimal and symmetric with the existing handles;
  no new dependencies (the module stays import-light).
- **Store aliasing bugs.** A shared mutable store could let writes bleed across assemblies. → The read-write
  handle copies its slice; a test writes through one handle and confirms a fresh assembly is unaffected.

## Migration Plan
Additive. `read`-mode provisioning is byte-for-byte unchanged; `customer-support.json` assembles exactly as
before. The new modes only affect graphs that declare them (today, `support-platform.json`).

## Open Questions
- Should `read-write` provisioning seed from `stores` like `read` does, or start empty? (Chosen: seed from
  `stores`, copying, so a read-write handle can also be given fixture contents — symmetric with `read`.)
- Whether to later unify the three DB handles behind one class parameterised by mode. (Deferred; three small
  classes read more clearly as distinct surfaces, which is the whole point.)
