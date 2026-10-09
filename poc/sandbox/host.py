"""The wasmtime component host: instantiate a node with a typed capability set.

A `Sandbox` links a WASM **component** against exactly the typed WIT interfaces
its world imports, and nothing else. Compare what this replaced:

    core-wasm tier (retired)          component tier (here)
    ────────────────────────          ─────────────────────
    module + empty WasiConfig         component, no WASI adapter
    imports `cap_infer` (a symbol)    imports `aap:caps/inference-llm@0.1.0`
      plus powerless WASI stubs         and nothing else — no stubs to be powerless
    flat (ptr, len) i64 into memory   typed records / variants / enums
    fields framed with 0x1F, 0x1E     `list<string>` is a list

Two properties follow, and they are why the tier was ported:

* **No ambient authority is structural.** The old module's import table contained
  `fd_write`, `environ_get`, `path_open`. They were harmless because the host
  handed them an empty `WasiConfig` — confinement was a fact about the host's
  *configuration*. Here they are absent from the artifact. `wasi_imports()` returns
  the empty list, and the hostile-node suite asserts it.

* **The boundary is typed.** The host does not hand the guest bytes to reinterpret;
  it hands it a `customer-query` whose `intent` is one of five enum cases. A value
  of the wrong shape is refused at the boundary by wasmtime, not silently
  misparsed downstream. `SandboxTypeError` surfaces that refusal.

If a component imports a capability interface the caller did not provide,
`instantiate` fails — that is the enforcement for "a node cannot call a capability
it was not granted", and it now fails naming the *interface*, not a bare symbol.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator, Mapping
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from .interfaces import CAPABILITY_INTERFACES, TYPES

# Built component artifacts live here (committed, so tests run without a Rust or
# component toolchain); `make wasm` rebuilds them from rust/ + wit/.
WASM_DIR = Path(__file__).resolve().parent / "wasm"


class SandboxError(RuntimeError):
    """Raised when a component cannot be instantiated or run — most importantly,
    when it imports a capability interface the caller did not grant."""


class IncompleteHostBinding(SandboxError):
    """Raised when a component calls a function of a *granted* interface that the
    host's binding of that interface does not supply.

    Neither a confinement failure nor a fault in the component: the adapter that
    links the node was written short. Kept apart from `SandboxError` proper so
    that it is never reported — to a reader, or to a model being asked to fix its
    code — as a capability the node was not granted."""


class SandboxTypeError(SandboxError):
    """Raised when a value does not conform to a WIT interface's declared type.

    This class of failure is what the typed boundary buys. On the flat ABI a
    malformed value was just bytes: it would be reinterpreted as *something*, and
    the mistake surfaced later as a nonsense field, or not at all. Here it cannot
    cross the boundary."""


# One shared engine, and a cache of compiled components keyed by artifact path.
# Compilation (parse + JIT) is a one-time cost; only instantiation (a fresh store,
# linker and instance) is paid per node invocation. Without this cache every
# sandboxed node call would recompile — the dominant cost. The benchmark reaches
# into `_compiled` to measure cold compile against warm reuse.
_ENGINE: Any = None
_COMPONENT_CACHE: dict[str, Any] = {}

# Address space each store reserves for a guest's linear memory, and the guard
# region after it. wasmtime's defaults are tuned for a server running a few
# long-lived guests: a 4GiB reservation plus a 64MiB guard, sized so that every
# 32-bit guest address is representable and bounds checks fold into the guard.
#
# That is the wrong trade here and it failed in practice. A node body is a few
# hundred KiB of Rust that touches a fraction of a page, but every node
# invocation builds a *fresh* store, so the tier asks the OS to reserve 4.06GiB
# per instantiation. The reservation is virtual and normally free — until the
# machine is loaded, at which point `mmap` refuses and instantiation fails with
# "Cannot allocate memory". The symptom is badly misleading: the failure lands in
# the same place an ungranted capability does, so a busy machine produced what
# looked like a capability error.
#
# 32MiB is roughly two orders of magnitude more than any node here uses, and
# `memory_may_move` keeps the cap from being a correctness limit: a guest that
# outgrows the reservation gets its memory reallocated rather than trapping. The
# cost is that accesses past the smaller guard need an explicit bounds check;
# @sec:eval-overhead's crossing measurement is unmoved by it, which is the only
# number that would have noticed.
MEMORY_RESERVATION = 32 * 1024 * 1024
MEMORY_GUARD_SIZE = 64 * 1024


def engine_config() -> Any:
    """The engine configuration both the runtime and the benchmark build from, so
    the tier is measured as it is run."""
    import wasmtime

    config = wasmtime.Config()
    config.memory_reservation = MEMORY_RESERVATION
    config.memory_guard_size = MEMORY_GUARD_SIZE
    config.memory_may_move = True
    return config


def _is_resource_exhaustion(error: Exception) -> bool:
    """True if an instantiation failure is the host running out of memory rather
    than the guest reaching for authority it was not granted."""
    text = str(error).lower()
    return "cannot allocate memory" in text or "mmap failed" in text


def _compiled(path: Path):
    """Return `(engine, component)` for an artifact, compiling and caching on first use."""
    import wasmtime
    from wasmtime.component import Component

    global _ENGINE
    if _ENGINE is None:
        _ENGINE = wasmtime.Engine(engine_config())
    key = str(path)
    component = _COMPONENT_CACHE.get(key)
    if component is None:
        component = Component.from_file(_ENGINE, key)
        _COMPONENT_CACHE[key] = component
    return _ENGINE, component


def available() -> bool:
    """True if the component tier can run here (the `wasmtime` package is present).

    Building the artifacts needs a Rust toolchain and `wasm-tools`; running them
    needs only wasmtime and the committed `.wasm` files."""
    from importlib.util import find_spec

    return find_spec("wasmtime") is not None


# Two hooks for the generation experiment (`poc/generation/`), which runs bodies
# a model wrote through the same adapters as the committed ones. Both are empty
# in every ordinary run, and both are process-wide on purpose: the experiment
# evaluates one component per child process.
#
# `_SUBSTITUTED` maps an artifact's name to another file to load in its place — a
# freshly built, generated body standing in for the hand-written one.
#
# `_PERMISSIVE` is the *gate-off control*, and it weakens the tier deliberately.
# It holds capability interfaces to link beside whatever a node was granted, so
# that a component importing an ungranted interface instantiates instead of
# being refused. That is exactly the failure the gate exists to prevent; the
# control turns the gate off to count how many over-importing bodies would then
# have built, passed their contracts, and run.
_SUBSTITUTED: dict[str, Path] = {}
_PERMISSIVE: dict[str, Mapping[str, Callable[..., Any]]] = {}


@contextmanager
def substituted(components: Mapping[str, Path]) -> Iterator[None]:
    """Load `components` (artifact name → file) in place of the committed
    artifacts of those names, for the body of the `with`."""
    previous = dict(_SUBSTITUTED)
    _SUBSTITUTED.update(components)
    try:
        yield
    finally:
        _SUBSTITUTED.clear()
        _SUBSTITUTED.update(previous)


@contextmanager
def permissive(extra: Mapping[str, Mapping[str, Callable[..., Any]]]) -> Iterator[None]:
    """Link `extra` beside every node's granted interfaces: the gate, off. For the
    generation experiment's control only — see `_PERMISSIVE` above."""
    previous = dict(_PERMISSIVE)
    _PERMISSIVE.update(extra)
    try:
        yield
    finally:
        _PERMISSIVE.clear()
        _PERMISSIVE.update(previous)


def wasm_path(name: str) -> Path:
    """Path to a built component artifact, e.g. `wasm_path('node_parse_message')`."""
    return _SUBSTITUTED.get(name, WASM_DIR / f"{name}.wasm")


def imports_of(path: Path) -> list[str]:
    """Every interface the component in the file at `path` imports, sorted.

    Read fresh, never from `_COMPONENT_CACHE`. The cache is keyed by path, which
    is right for committed artifacts and wrong here: the generation experiment
    builds one component after another to the *same* path, and a cached answer
    would hold each to its predecessor's imports. (It did, the first time the
    hand-written control was run: every node after the first was reported as
    importing what the first imported.)"""
    import wasmtime
    from wasmtime.component import Component

    global _ENGINE
    if _ENGINE is None:
        _ENGINE = wasmtime.Engine(engine_config())
    component = Component.from_file(_ENGINE, str(path))
    return sorted(component.type.imports(_ENGINE).keys())


def record(**fields: Any):
    """Build a value for a WIT `record` parameter.

    wasmtime lifts records into `wasmtime.component.Record` and lowers anything
    with matching attributes. We construct real `Record`s rather than an ad-hoc
    namespace because wasmtime discriminates *untagged* variant cases by Python
    type: `tool-llm.reply` has a `text(string)` case and a `call(tool-request)`
    case, and a `Record` is how the host says "this is the record case".
    """
    from wasmtime.component import Record

    r = Record()
    r.__dict__.update(fields)
    return r


def component_imports(component_name: str) -> list[str]:
    """Every interface a component imports, sorted. Includes the type vocabulary."""
    engine, component = _compiled(wasm_path(component_name))
    return sorted(component.type.imports(engine).keys())


def capability_imports(component_name: str) -> list[str]:
    """The capability interfaces a component imports — its authority, at the WASM
    level.

    This is `component_imports` minus the shared `types` interface, which declares
    only records/enums/variants and no functions, and so grants nothing. A node
    cannot import a capability interface that is not here, and the host refuses to
    instantiate it if it imports one the caller did not grant.
    """
    return [i for i in component_imports(component_name) if i != TYPES]


def wasi_imports(component_name: str) -> list[str]:
    """The ambient-authority imports of a component. Always empty, by construction.

    The core-wasm tier's counterpart of this function returned a real list —
    `environ_get`, `fd_write`, `path_open` and friends — which the empty
    `WasiConfig` rendered powerless. The components here are built for
    `wasm32-unknown-unknown` and converted with no WASI adapter, so there is
    nothing to render powerless. Kept as a function, and asserted in the test
    suite, because "the list is empty" is the claim; deleting the function would
    turn a checked property back into prose.

    This is the vocabulary-level check: it reports imports outside the whole
    capability vocabulary — the WASI functions an adapter would add — and so it
    cannot see a vocabulary interface a particular node was not granted. A
    `wasi:clocks/wall-clock` import is in the vocabulary (the `Clock` capability),
    so this function reports it clean on *any* node. Whether a node was granted
    it is the per-node question `ungranted_imports` answers against its `with`
    clause, and the derivation gate enforces.
    """
    vocabulary = CAPABILITY_INTERFACES | {TYPES}
    return [i for i in component_imports(component_name) if i not in vocabulary]


def ungranted_imports(component_name: str, granted: Iterable[str]) -> list[str]:
    """The imports of a component that its node's `with` clause did not grant.

    This is what "ambient" means once `Clock` is a capability: an import the
    graph did not grant, whatever its package namespace. A node whose clause
    names `Clock` imports `wasi:clocks/wall-clock` and is clean here; the same
    import on a node whose clause does not name it is reported. `granted` is the
    node's derived interface set (`interfaces.expected_imports`); the shared type
    vocabulary is always allowed, because it declares no functions."""
    allowed = set(granted) | {TYPES}
    return [i for i in component_imports(component_name) if i not in allowed]


class Sandbox:
    """A single instantiated node component, confined to its declared capability
    interfaces.

    `caps` maps a WIT interface name (e.g. `aap:caps/inference-llm@0.1.0`) to the
    functions of that interface, as plain Python callables — see
    `poc/sandbox/nodes.py` for how the host-tier capability handles are exposed
    through it. Only the interfaces a component actually imports need be provided;
    extras are ignored, and a *missing* one that the component imports is a
    `SandboxError` at construction time, before any guest code runs.

    Every call from the guest into one of these functions is one capability-boundary
    crossing, and the sandbox counts them (`crossings`) — that is the quantity
    `bench.py` measures against the proposal's envelope.
    """

    def __init__(
        self,
        component_name: str,
        caps: Mapping[str, Mapping[str, Callable[..., Any]]] | None = None,
    ):
        if not available():
            raise SandboxError(
                "component tier needs the wasmtime package — install it with "
                "`uv sync --group poc`, or run the node on the host tier"
            )
        from wasmtime import Store
        from wasmtime.component import Linker

        self.component_name = component_name
        self.crossings = 0
        # Granted interfaces win over the gate-off control's stand-ins, so the
        # control only ever *adds* what a node was not granted.
        self._caps = {**_PERMISSIVE, **dict(caps or {})}

        path = wasm_path(component_name)
        if not path.exists():
            raise SandboxError(f"missing component {path.name!r}; run `make wasm` to build it")

        self._engine, self._component = _compiled(path)
        self._store = Store(self._engine)

        linker = Linker(self._engine)
        # Define exactly the granted interfaces. Note what is NOT here: no
        # `add_wasip2()`, no `define_unknown_imports_as_traps()`. An import this
        # loop does not satisfy is an instantiation failure, which is the point —
        # an ungranted capability must not resolve to a trapping stub, because a
        # stub is a thing the node can *call*.
        with linker.root() as root:
            for iface_name, funcs in self._caps.items():
                with root.add_instance(iface_name) as iface:
                    for func_name, fn in funcs.items():
                        iface.add_func(func_name, self._bind(fn))

        try:
            self._instance = linker.instantiate(self._store, self._component)
        except Exception as e:  # wasmtime raises on an unsatisfied import
            # An unsatisfied import is the interesting failure and the one this
            # tier is built to produce, but it is not the only way instantiation
            # can fail — exhausting the host's address space lands here too, and
            # reporting that as an ungranted capability sends the reader hunting
            # for a security bug that is not there. Name the resource failure as
            # what it is; everything else is the capability case.
            if _is_resource_exhaustion(e):
                raise SandboxError(
                    f"{component_name!r} could not be instantiated — the host could not "
                    f"allocate memory for the guest, which is a resource failure and not "
                    f"a capability one: {e}"
                ) from e
            # A third way to fail, and the most misleading of the three: the
            # component imports an interface the caller *did* provide, and calls a
            # function of it the caller's binding left out. That is a fault in the
            # host adapter, not in the component and not in the grant. The
            # generation pilot ran into it — `Heartbeat` bodies calling
            # `http-client.fetch` against an adapter that bound only `get` — and,
            # before this branch existed, every one was told it had imported a
            # capability it was not granted.
            text = str(e)
            for iface_name, funcs in self._caps.items():
                if f"`{iface_name}`" in text and "function implementation is missing" in text:
                    raise IncompleteHostBinding(
                        f"{component_name!r} could not be instantiated — the host binds "
                        f"{iface_name} with only {sorted(funcs)}, and the component calls a "
                        f"function of it that is missing. This is a fault in the host "
                        f"adapter, not an ungranted capability: {e}"
                    ) from e
            raise SandboxError(
                f"{component_name!r} could not be instantiated — it imports a capability "
                f"it was not granted: {e}"
            ) from e

        # Resolving an export reflects over its WIT type, which is not cheap and
        # does not change for the life of the instance. Cache it: without this,
        # every `call` re-derives the signature and the cost swamps the boundary
        # crossing the benchmark is trying to measure.
        self._exports: dict[str, Any] = {}

    def _bind(self, fn: Callable[..., Any]):
        """Wrap a capability function as a component host function.

        wasmtime passes the store as the first argument; the node's own arguments
        follow, already lifted into Python values by the typed boundary — no
        unpacking, no framing, no `memory.read`. Every invocation is one counted
        capability-boundary crossing.
        """

        def callback(_store, *args: Any) -> Any:
            self.crossings += 1
            return fn(*args)

        return callback

    def call(self, export: str, *args: Any) -> Any:
        """Invoke one of the component's exported functions with typed arguments.

        A value that does not conform to the export's WIT signature never reaches
        the guest: wasmtime refuses to lower it, and we surface that as
        `SandboxTypeError`. That is the "type-mismatched value is a boundary
        error, not a marshalling accident" property, and it is what the flat ABI
        could not offer.
        """
        fn = self._exports.get(export)
        if fn is None:
            fn = self._instance.get_func(self._store, export)
            if fn is None:
                raise SandboxError(f"{self.component_name!r} exports no function {export!r}")
            self._exports[export] = fn
        try:
            return fn(self._store, *args)
        except (TypeError, ValueError, AttributeError) as e:
            raise SandboxTypeError(
                f"value rejected at the typed boundary of {self.component_name!r}.{export}: {e}"
            ) from e
