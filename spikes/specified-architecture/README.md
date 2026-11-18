# Spikes: specified architecture

The spikes of `openspec/changes/explore-specified-architecture`. **No build step imports
anything here**, `make test` does not collect it (`testpaths = ["tests"]`), and nothing
here may move a Paper 2–4 figure. Each spike ends in a `RESULT.md` with a recommendation:
propose a change, or stop.

| Dir | Strand | Run |
|---|---|---|
| `s1/` | Budgets as capability scopes | `uv run --group poc pytest spikes/specified-architecture/s1` |
| `s2/` | Contracts that compose along edges | `uv run pytest spikes/specified-architecture/s2` |
| `s3/` | Proofs of node bodies | see `s3/README.md` |
| `s4/` | Proofs of resource bounds | see `s4/README.md` |

Measurement scripts run from this directory with the repo's import paths:

```sh
cd spikes/specified-architecture
PYTHONPATH=../../scripts:../.. uv run --project ../.. --group poc python -m s1.measure
```

Spike crates have their own Cargo workspaces (so `make wasm` never builds them); their
built components are committed beside them, and `target/` is ignored.
