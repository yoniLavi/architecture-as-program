"""Sandbox execution tier — unforgeable node confinement via WASM/WASI.

Where the host tier (`poc/nodes.py`, `poc/handles.py`) demonstrates the *shape*
of capability confinement by discipline, this tier *enforces* it: a node body is
a WebAssembly module run under `wasmtime` with an empty WASI context — no
filesystem preopens, no sockets, no environment, no clock. The module's only
imports are the host functions that back the capability handles its signature
declares. A capability the node was not granted is not merely unexposed; it is
absent from the import table, so the module cannot even instantiate if it asks
for one.

This package is optional: it imports `wasmtime` (in the `poc` dependency group).
Callers that may run without the toolchain should guard on `available()`.
"""

from __future__ import annotations

from .host import (
    FS,
    RS,
    Sandbox,
    SandboxError,
    available,
    wasm_path,
)

__all__ = ["FS", "RS", "Sandbox", "SandboxError", "available", "wasm_path"]
