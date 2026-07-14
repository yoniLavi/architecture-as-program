"""Executable signal-graph runtime — proof of concept.

This package is the runtime increment of the "Architecture as Program" PoC. It
loads the same canonical graph JSONs that drive the proposal (`graphs/*.json`),
instantiates each node with injected capability handles, and propagates signals
along the active path.

Enforcement fidelity (stated honestly, per the proposal's hedging discipline):
capability confinement here is *host-discipline* enforcement — a node receives
only the handles its signature declares, and each handle's surface is scoped to
its declared authority. This demonstrates the *shape* of capability confinement.
It does NOT make confinement unforgeable: nothing stops a determined node from
`import os`. Memory-level unforgeability requires the WASM/WASI sandbox tier
(a named follow-up change) and, ultimately, CHERI hardware — both described in
the proposal's runtime section.
"""

# Put the repo's `scripts/` directory on sys.path so this package can reuse the
# existing, stdlib-only `type_parser` and `graph_validator` modules instead of
# duplicating them.
#
# This lives in __init__ rather than in a submodule imported for its side effect:
# Python guarantees a package's __init__ runs before any of its submodules, so the
# bootstrap cannot be silently broken by an import sorter reordering a submodule's
# imports above it — which is exactly what happened when it lived elsewhere.
import sys as _sys
from pathlib import Path as _Path

_SCRIPTS = _Path(__file__).resolve().parent.parent / "scripts"
if str(_SCRIPTS) not in _sys.path:
    _sys.path.insert(0, str(_SCRIPTS))
