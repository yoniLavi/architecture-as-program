"""Component execution tier — unforgeable, *typed* node confinement.

Where the host tier (`poc/nodes.py`, `poc/handles.py`) demonstrates the *shape* of
capability confinement by discipline, this tier *enforces* it: a node body is a
WebAssembly **component** run under `wasmtime`, and its import set is exactly the
typed WIT interfaces its `with` clause declares (see `wit/caps.wit`).

Two claims, both asserted in `tests/test_poc_sandbox.py` rather than in prose:

* **A capability the node did not declare cannot be named.** It is not in the
  component's world, so there is no import to call — and the host refuses to
  instantiate a component that asks for one, before any guest code runs.

* **There is no ambient authority to reach for.** The components are built for
  `wasm32-unknown-unknown` and converted with no WASI adapter, so the import set
  contains *no* filesystem, socket, environment or clock function at all — not
  even the powerless stubs a `wasm32-wasip1` module links. `wasi_imports()`
  returns the empty list.

The boundary is typed: the host and a node exchange WIT records, enums and
variants, so a value of the wrong shape is a boundary error (`SandboxTypeError`)
rather than a misread of a flat byte buffer.

This package is optional: it imports `wasmtime` (in the `poc` dependency group).
Callers that may run without the toolchain should guard on `available()`.
"""

from __future__ import annotations

from .host import (
    Sandbox,
    SandboxError,
    SandboxTypeError,
    available,
    capability_imports,
    component_imports,
    record,
    wasi_imports,
    wasm_path,
)
from .interfaces import (
    CAPABILITY_INTERFACES,
    CAPABILITY_KINDS,
    CLOCK,
    EVENT_EMITTER,
    HTTP_CLIENT,
    INFERENCE_LLM,
    KB_READ,
    NOTIFIER,
    RESPONSE_CHANNEL,
    TOOL_LLM,
    TYPES,
    expected_imports,
    interface_for,
    interfaces_for_node,
)

__all__ = [
    "CAPABILITY_INTERFACES",
    "CAPABILITY_KINDS",
    "CLOCK",
    "EVENT_EMITTER",
    "HTTP_CLIENT",
    "INFERENCE_LLM",
    "KB_READ",
    "NOTIFIER",
    "RESPONSE_CHANNEL",
    "TOOL_LLM",
    "TYPES",
    "Sandbox",
    "SandboxError",
    "SandboxTypeError",
    "available",
    "capability_imports",
    "component_imports",
    "expected_imports",
    "interface_for",
    "interfaces_for_node",
    "record",
    "wasi_imports",
    "wasm_path",
]
