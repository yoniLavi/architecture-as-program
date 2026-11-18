"""S1: store-bounded budgets on the confined tier. A spike, imported by no build step.

CPU, memory and wall-clock time are not reached through a handle, so no scope can
carry them. The store bounds them instead:

* **fuel** (`Store.set_fuel`) — a count of executed WebAssembly operators. It is
  deterministic: the same input spends the same fuel on any machine and under any
  load, which is what a budget should be.
* **an epoch deadline** (`Store.set_epoch_deadline`) — a wall-clock bound, kept by a
  ticker thread that increments the engine's epoch every millisecond. It can only
  fire late, never early (a tick is at least a millisecond), but a loaded machine
  deschedules the guest, so it can cut off a guest that has done less work than
  the same deadline allows on an idle machine. A backstop, not a budget.
* **a memory limit** (`Store.set_limits(memory_size=…)`) — `memory.grow` returns -1
  past it.

`MeteredSandbox` is `poc.sandbox.host.Sandbox` built on **its own engine** with fuel
and epoch interruption enabled. Both are engine-wide settings, and the runtime's
shared engine is the one Paper 2's crossing figure was measured on, so the spike
must not touch it. The linking loop is the parent's; the failure classification is
extended, never replaced: a store bound is `BudgetExhausted`, never an ungranted
capability.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from poc.sandbox import host
from poc.sandbox.host import Sandbox, SandboxError, engine_config

from .budget import BudgetExhausted

SPIKE_WASM = Path(__file__).resolve().parent / "wasm"

FUEL_TRAP = "all fuel consumed by WebAssembly"
EPOCH_TRAP = "wasm trap: interrupt"
UNREACHABLE_TRAP = "wasm `unreachable` instruction executed"

# Effectively unlimited, for a store whose fuel is metered but not bounded.
UNBOUNDED_FUEL = 2**62


@dataclass(frozen=True)
class StoreBudget:
    """A node's store-bounded budget: the `budget` annotation on a node."""

    fuel: int | None = None
    memory_bytes: int | None = None
    deadline_ms: int | None = None


class GuestTrapped(SandboxError):
    """The guest trapped on `unreachable` under a memory limit. A Rust guest built
    with `panic = "abort"` traps this way both when it panics and when an
    allocation fails, and wasmtime-py offers neither `trap_on_grow_failure` nor a
    resource-limiter callback, so the host cannot tell which. Reported as
    ambiguous rather than guessed either way."""


_ENGINES: dict[tuple[bool, bool], Any] = {}
_COMPONENTS: dict[tuple[bool, bool, str], Any] = {}
_TICKER: threading.Thread | None = None
_TICKING: list[Any] = []


def metered_engine(fuel: bool = True, epoch: bool = True) -> Any:
    """An engine configured as the runtime's (`engine_config`), plus fuel and/or
    epoch interruption."""
    import wasmtime

    key = (fuel, epoch)
    if key not in _ENGINES:
        config = engine_config()
        config.consume_fuel = fuel
        config.epoch_interruption = epoch
        _ENGINES[key] = wasmtime.Engine(config)
        if epoch:
            _start_ticker(_ENGINES[key])
    return _ENGINES[key]


def _start_ticker(engine: Any) -> None:
    global _TICKER
    _TICKING.append(engine)
    if _TICKER is None:

        def tick() -> None:
            while True:
                time.sleep(0.001)
                for e in _TICKING:
                    e.increment_epoch()

        _TICKER = threading.Thread(target=tick, name="epoch-ticker", daemon=True)
        _TICKER.start()


def _component(engine_key: tuple[bool, bool], path: Path) -> Any:
    from wasmtime.component import Component

    key = (*engine_key, str(path))
    if key not in _COMPONENTS:
        _COMPONENTS[key] = Component.from_file(metered_engine(*engine_key), str(path))
    return _COMPONENTS[key]


def classify(error: Exception, budget: StoreBudget, spent_fuel: int | None) -> Exception:
    """The error a store bound raised, as the event it is."""
    text = str(error)
    if FUEL_TRAP in text:
        return BudgetExhausted("Fuel", budget.fuel or 0, spent_fuel or 0, "store")
    if EPOCH_TRAP in text:
        return BudgetExhausted("Deadline", budget.deadline_ms or 0, budget.deadline_ms or 0,
                               "store")  # fmt: skip
    if UNREACHABLE_TRAP in text and budget.memory_bytes is not None:
        return GuestTrapped(
            f"the guest trapped under a {budget.memory_bytes}-byte memory limit: either "
            f"it panicked or an allocation was refused, and the host cannot tell which"
        )
    return error


class MeteredSandbox(Sandbox):
    """A `Sandbox` on a fuel- and epoch-enabled engine, with a `StoreBudget`."""

    def __init__(
        self,
        component_name: str,
        caps: Mapping[str, Mapping[str, Callable[..., Any]]] | None = None,
        budget: StoreBudget = StoreBudget(),  # noqa: B008 — frozen, so safe to share
        *,
        path: Path | None = None,
        fuel: bool = True,
        epoch: bool = True,
    ):
        import wasmtime
        from wasmtime.component import Linker

        self.component_name = component_name
        self.crossings = 0
        self.budget = budget
        self._caps = {**host._PERMISSIVE, **dict(caps or {})}
        path = path or host.wasm_path(component_name)
        key = (fuel, epoch)
        self._engine = metered_engine(*key)
        self._component = _component(key, path)
        self._store = wasmtime.Store(self._engine)
        self._metered_fuel = fuel
        if fuel:
            self._store.set_fuel(budget.fuel if budget.fuel is not None else UNBOUNDED_FUEL)
        if epoch:
            # In ticks of ~1ms; "no deadline" is a deadline far away.
            self._store.set_epoch_deadline(budget.deadline_ms or 10**12)
        if budget.memory_bytes is not None:
            self._store.set_limits(memory_size=budget.memory_bytes)
        self._fuel_start = self._store.get_fuel() if fuel else None

        linker = Linker(self._engine)
        with linker.root() as root:
            for iface_name, funcs in self._caps.items():
                with root.add_instance(iface_name) as iface:
                    for func_name, fn in funcs.items():
                        iface.add_func(func_name, self._bind(fn))
        try:
            self._instance = linker.instantiate(self._store, self._component)
        except Exception as e:
            # A store bound first; then the parent's three cases, unchanged.
            classified = classify(e, budget, self.fuel_spent())
            if classified is not e:
                raise classified from e
            raise SandboxError(f"{component_name!r} could not be instantiated: {e}") from e
        self.instantiation_fuel = self.fuel_spent()
        self._exports = {}

    def fuel_spent(self) -> int | None:
        if not self._metered_fuel or self._fuel_start is None:
            return None
        return self._fuel_start - self._store.get_fuel()

    def call(self, export: str, *args: Any) -> Any:
        try:
            return super().call(export, *args)
        except SandboxError:
            raise
        except Exception as e:
            classified = classify(e, self.budget, self.fuel_spent())
            if classified is not e:
                raise classified from e
            raise


@contextmanager
def metered_tier(budget: StoreBudget, *, fuel: bool = True, epoch: bool = True) -> Iterator[list]:
    """Run the runtime's own confined adapters under a store budget: every
    `Sandbox(...)` they build becomes a `MeteredSandbox`. Yields the sandboxes
    built, for their fuel figures. Spike-only: it patches the adapters' module
    globals for the duration."""
    import poc.sandbox.feed_nodes as feed_nodes
    import poc.sandbox.nodes as nodes

    built: list[MeteredSandbox] = []

    def make(name, caps=None):
        sb = MeteredSandbox(name, caps, budget, fuel=fuel, epoch=epoch)
        built.append(sb)
        return sb

    saved = (nodes.Sandbox, feed_nodes.Sandbox)
    nodes.Sandbox = feed_nodes.Sandbox = make  # type: ignore[assignment]
    try:
        yield built
    finally:
        nodes.Sandbox, feed_nodes.Sandbox = saved
