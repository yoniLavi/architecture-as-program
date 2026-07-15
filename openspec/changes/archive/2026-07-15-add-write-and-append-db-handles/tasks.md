## 1. Handles
- [x] 1.1 Add a read-write DB handle (`read` + `write`, owning a private copy of its store slice) to
      `poc/handles.py`
- [x] 1.2 Add an append-only DB handle (`append` + inspectable log, **no** `read`) to `poc/handles.py`
- [x] 1.3 Update the module docstring's handle inventory to list both new handles

## 2. Provisioning
- [x] 2.1 Extend `provision`'s `DBHandle` branch to dispatch on `read` / `read-write` / `append`, building
      the matching handle; an unrecognised mode raises a `ValueError` naming the known modes
- [x] 2.2 Confirm `read`-mode provisioning is unchanged (existing tests stay green)

## 3. Tests
- [x] 3.1 `provision` builds the right handle for each mode; read-write reads and writes; append appends and
      has no `read`; unknown mode raises
- [x] 3.2 The read-write handle does not alias the shared `stores` (writes don't leak into a fresh assembly)
- [x] 3.3 `SupportPlatform` assembles end-to-end, and its graph-declared `ResponseChannel<user-session>`
      identities route distinct instances to `CustomerSupport` and `BillingService` (the shipped graph, not a
      synthetic one)

## 4. Proposal + wrap-up
- [x] 4.1 If any proposal claim needs it, note in §5 that the composition graph now assembles end-to-end so
      its identity routing is tested on the shipped graph (only if accurate; do not overclaim execution)
- [x] 4.2 Full gate green: ruff, pytest (`--group poc`), `make build`

## Notes for whoever picks this up
- Keep the append handle read-less: that incomparability with `read` (proposal §5's mode lattice) is the
  point, and a test should assert it, mirroring `test_read_db_handle_has_no_write_method`.
- The runtime still does not execute sub-graphs; the win here is *assembly* of `SupportPlatform` and running
  its capability-identity routing, not running the composed pipeline.
