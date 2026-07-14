"""The wasmtime host: instantiate a node module with zero ambient authority.

A `Sandbox` links a WASM module against exactly two things:

* an **empty** WASI context (`wasmtime.WasiConfig` with nothing inherited and
  nothing preopened) — so the standard-library calls a hostile node might make
  (open a file, read an env var) resolve to WASI functions that have no
  authority behind them; and
* the **capability host functions** the node declares, and only those — provided
  by the caller as plain `str -> str` transforms. Each call across this boundary
  is one capability-boundary crossing, and the sandbox counts them.

If a module imports a capability the caller did not provide, `instantiate` fails:
that is the enforcement for "a node cannot call a capability it was not granted".

ABI (see `rust/abi/src/lib.rs`): bytes live in the module's linear memory,
addressed by a packed ``(ptr << 32) | len`` i64. The host writes an input by
calling the module's exported ``alloc``; the module returns results the same way.
Fields are framed with ``FS`` (0x1F); list elements with ``RS`` (0x1E).
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from pathlib import Path
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    import wasmtime

FS = "\x1f"
RS = "\x1e"

_MASK32 = 0xFFFFFFFF
_MASK64 = 0xFFFFFFFFFFFFFFFF

# Built wasm artifacts live here (committed, so tests run without a Rust
# toolchain); `make wasm` rebuilds them from rust/.
WASM_DIR = Path(__file__).resolve().parent / "wasm"


class SandboxError(RuntimeError):
    """Raised when a module cannot be instantiated or run — most importantly,
    when it imports a capability the caller did not grant."""


# One shared engine, and a cache of compiled modules keyed by artifact path.
# Compilation (parse + JIT) is a one-time cost; only instantiation (a fresh
# store, linker, and instance) is paid per node invocation. Without this cache
# every sandboxed node call would recompile its module — the dominant cost.
_ENGINE: wasmtime.Engine | None = None
_MODULE_CACHE: dict[str, wasmtime.Module] = {}


def _compiled(path: Path) -> tuple[wasmtime.Engine, wasmtime.Module]:
    """Return `(engine, module)` for an artifact, compiling and caching on first
    use. Exposed cache lets the benchmark measure cold compile vs warm reuse."""
    import wasmtime

    global _ENGINE
    if _ENGINE is None:
        _ENGINE = wasmtime.Engine()
    key = str(path)
    module = _MODULE_CACHE.get(key)
    if module is None:
        module = wasmtime.Module.from_file(_ENGINE, key)
        _MODULE_CACHE[key] = module
    return _ENGINE, module


def available() -> bool:
    """True if the sandbox tier can run here (the `wasmtime` package is present).

    Building the `.wasm` artifacts needs a Rust toolchain, but running them only
    needs wasmtime and the committed artifacts."""
    from importlib.util import find_spec

    return find_spec("wasmtime") is not None


def wasm_path(name: str) -> Path:
    """Path to a built module artifact, e.g. `wasm_path('node_parse_message')`."""
    return WASM_DIR / f"{name}.wasm"


def cap_imports(module_name: str) -> list[str]:
    """The capability host-function names a module imports (import module `cap`).

    This is the module's declared capability surface at the WASM level: the
    functions it will call to exercise external authority. A node cannot import a
    `cap` function that is not here, and the host refuses to instantiate it if it
    imports one the caller did not grant. WASI imports (powerless under the empty
    context) are excluded — see `wasi_imports`."""
    _engine, module = _compiled(wasm_path(module_name))
    return sorted(imp.name for imp in module.imports if imp.module == "cap" and imp.name)


def wasi_imports(module_name: str) -> list[str]:
    """The WASI functions a module imports. A `wasm32-wasip1` module links these
    through the standard library, but under the empty WASI context they carry no
    authority — the ambient-escape tests demonstrate this at runtime. Confinement
    is enforced by the empty context, not by the absence of these imports."""
    _engine, module = _compiled(wasm_path(module_name))
    return sorted(imp.name for imp in module.imports if imp.module != "cap" and imp.name)


def _to_signed_i64(v: int) -> int:
    v &= _MASK64
    return v - (1 << 64) if v >= (1 << 63) else v


def _pack(ptr: int, length: int) -> int:
    return _to_signed_i64(((ptr & _MASK32) << 32) | (length & _MASK32))


def _unpack(v: int) -> tuple[int, int]:
    v &= _MASK64
    return (v >> 32) & _MASK32, v & _MASK32


class Sandbox:
    """A single instantiated node module, confined to an empty WASI context plus
    its declared capability imports.

    `caps` maps a host-function name (e.g. `cap_infer`) to a `str -> str`
    transform. Only the names a module actually imports need be provided; extra
    entries are ignored, and a *missing* one that the module imports is a
    `SandboxError` at construction time."""

    def __init__(self, module_name: str, caps: Mapping[str, Callable[[str], str]] | None = None):
        if not available():
            raise SandboxError(
                "sandbox tier needs the wasmtime package — install it with "
                "`uv sync --group poc`, or run the node on the host tier"
            )
        import wasmtime

        self.module_name = module_name
        self.crossings = 0
        self._caps = dict(caps or {})

        path = wasm_path(module_name)
        if not path.exists():
            raise SandboxError(f"missing wasm artifact {path.name!r}; run `make wasm` to build it")

        self._engine, self._module = _compiled(path)
        self._store = wasmtime.Store(self._engine)
        # Empty WASI context: no argv, no env, no preopens, no stdio. Nothing is
        # inherited from the host process. This is the "no ambient authority" line.
        self._store.set_wasi(wasmtime.WasiConfig())

        linker = wasmtime.Linker(self._engine)
        linker.define_wasi()

        i32 = wasmtime.ValType.i32()
        i64 = wasmtime.ValType.i64()
        cap_type = wasmtime.FuncType([i32, i32], [i64])
        for name, fn in self._caps.items():
            linker.define(
                self._store, "cap", name, wasmtime.Func(self._store, cap_type, self._bind(fn))
            )

        try:
            self._instance = linker.instantiate(self._store, self._module)
        except Exception as e:  # wasmtime raises on an unsatisfied import
            raise SandboxError(
                f"{module_name!r} could not be instantiated — it imports a capability "
                f"it was not granted: {e}"
            ) from e

        exports = self._instance.exports(self._store)
        self._memory = cast("wasmtime.Memory", exports["memory"])
        self._alloc = cast("wasmtime.Func", exports["alloc"])
        self._exports = exports

    # ── ABI marshalling ────────────────────────────────────────────

    def _read(self, ptr: int, length: int) -> str:
        data = self._memory.read(self._store, ptr, ptr + length)
        return bytes(data).decode("utf-8")

    def _write(self, s: str) -> int:
        """Place a string in module memory (via the module's own `alloc`) and
        return the packed `(ptr, len)` the ABI expects."""
        raw = s.encode("utf-8")
        ptr = self._alloc(self._store, len(raw))
        self._memory.write(self._store, raw, ptr)
        return _pack(ptr, len(raw))

    def _bind(self, fn: Callable[[str], str]):
        """Wrap a `str -> str` capability into a host function callback. Every
        invocation is one counted capability-boundary crossing."""

        def callback(ptr: int, length: int) -> int:
            self.crossings += 1
            args = self._read(ptr, length)
            return self._write(fn(args))

        return callback

    # ── Invocation ─────────────────────────────────────────────────

    def call_run(self, payload: str) -> str:
        """Marshal `payload` into module memory, call the module's `run`, and
        return the decoded result."""
        raw = payload.encode("utf-8")
        ptr = self._alloc(self._store, len(raw))
        self._memory.write(self._store, raw, ptr)
        run = cast("wasmtime.Func", self._exports["run"])
        out_ptr, out_len = _unpack(run(self._store, ptr, len(raw)))
        return self._read(out_ptr, out_len)

    def call_export(self, name: str) -> str:
        """Call a no-argument export that returns a packed `(ptr, len)` string —
        used by the ambient-escape hostile modules (`escape_fs`, …)."""
        fn = cast("wasmtime.Func", self._exports[name])
        out_ptr, out_len = _unpack(fn(self._store))
        return self._read(out_ptr, out_len)
