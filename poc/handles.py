"""Capability handles — the runtime form of the proposal's `with` clauses.

Each handle is an object whose available operations match its declared scope.
This is where "capabilities as declared requirements" becomes concrete: a node
receives handle objects as explicit arguments and has no other way to reach
external authority. The handle's *surface* is the enforcement:

* `InferenceLLM`     (`LLMClient<inference>`)       — model access, NO tool calling.
* `ToolLLM`          (`LLMClient<[tools]>`)         — model access + only its named tools.
* `ReadDBHandle`     (`DBHandle<scope, read>`)      — read only, scoped to one store.
* `ReadWriteDBHandle`(`DBHandle<scope, read-write>`)— read *and* write, scoped to one store.
* `AppendDBHandle`   (`DBHandle<scope, append>`)    — append only, NO read (write-once log).
* `ResponseChannel`  (`ResponseChannel<...>`)       — write-only sink.
* `EventEmitter`     (`EventEmitter<topic>`)        — write-only sink.
* `Clock`            (`Clock`)                      — read the wall clock, nothing else.
* `HTTPClient`       (`HTTPClient<[host, ...]>`)    — outbound HTTP, allowlisted hosts only.
* `Notifier`         (`Notifier<channel>`)          — write-only notification sink.

The three `DBHandle` surfaces make the mode lattice concrete: `read-write` covers both `read` and
`append`, while `read` and `append` are mutually incomparable — neither handle's operations are a
superset of the other's (a reader cannot append; an appender cannot read).

Fidelity: this is host-discipline enforcement. `InferenceLLM` *has no* tool
method, so a node holding one cannot call a tool — but Python cannot stop a
malicious node from reaching around the object model entirely (e.g. `import os`).
Unforgeable confinement is the job of the WASM/WASI tier (a later change).
"""

from __future__ import annotations

import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from urllib.parse import urlsplit

from type_parser import TApp, TList, TName, TString, parse_type

from .llm import LLMBackend, LLMRequest
from .values import DeliveryConfirmation


class CapabilityError(RuntimeError):
    """Raised when code attempts to exercise authority a handle does not grant —
    e.g. calling a tool outside an `LLMClient`'s allowlist."""


class RevokedCapabilityError(RuntimeError):
    """Raised when code exercises a capability instance that has been revoked at
    runtime. The loud-failure sibling of `CapabilityError`: an out-of-scope tool
    call was never granted; a revoked handle *was* granted and then withdrawn."""


# ── LLM handles ────────────────────────────────────────────────────


@dataclass
class InferenceLLM:
    """`LLMClient<inference>` — model access without tool calling.

    There is deliberately no `call_tool` / tool-offering method. A node holding
    this handle can be *influenced* by adversarial input (its classification may
    be wrong) but has no mechanism to *act* on it."""

    backend: LLMBackend

    def infer(self, *, system: str, prompt: str, task: str) -> str:
        # offered_tools is forced empty: the model is never even told tools exist.
        resp = self.backend.generate(
            LLMRequest(system=system, prompt=prompt, offered_tools=(), task=task)
        )
        return resp.text


@dataclass
class ToolLLM:
    """`LLMClient<[tools]>` — model access plus exactly the named tools.

    The model is only offered tools in `allowed_tools`; if it nonetheless
    requests a tool outside that set, the handle raises `CapabilityError`. Tool
    implementations are supplied per call by the node (which owns the authority,
    e.g. a `DBHandle`, that the tool draws on)."""

    backend: LLMBackend
    allowed_tools: frozenset[str]
    _MAX_ROUNDS: int = field(default=3, compare=False)

    def respond(
        self,
        *,
        system: str,
        prompt: str,
        tools: Mapping[str, Callable[..., str]] | None = None,
    ) -> str:
        tools = tools or {}
        offered = tuple(sorted(self.allowed_tools))
        convo = prompt
        for _ in range(self._MAX_ROUNDS):
            resp = self.backend.generate(
                LLMRequest(system=system, prompt=convo, offered_tools=offered, task="respond")
            )
            if not resp.tool_calls:
                return resp.text
            results = []
            for call in resp.tool_calls:
                if call.name not in self.allowed_tools:
                    raise CapabilityError(
                        f"node attempted tool {call.name!r} outside its "
                        f"LLMClient scope {sorted(self.allowed_tools)}"
                    )
                impl = tools.get(call.name)
                if impl is None:
                    raise CapabilityError(
                        f"tool {call.name!r} is in scope but no implementation was provided"
                    )
                results.append(f"[TOOL RESULT {call.name}] {impl(**call.arguments)}")
            convo = prompt + "\n\n" + "\n".join(results)
        return resp.text


# ── Data / sink handles ────────────────────────────────────────────


@dataclass
class ReadDBHandle:
    """`DBHandle<scope, read>` — read-only access to a single named store. There
    is no `write` method, so a node holding this cannot mutate the store."""

    scope: str
    _data: Mapping[str, list[str]]

    def read(self, key: str) -> list[str]:
        return list(self._data.get(key, []))


@dataclass
class ReadWriteDBHandle:
    """`DBHandle<scope, read-write>` — read *and* write a single named store.

    Owns a private copy of its store slice (see `provision`), so writes through
    this handle stay local to one assembly and never leak back into the shared
    `stores` mapping or another graph's view. `write` appends a record to the
    list at `key`, and `read` returns it — enough to make a write-then-read
    observable without modelling transactions or deletion."""

    scope: str
    _data: dict[str, list[str]]

    def read(self, key: str) -> list[str]:
        return list(self._data.get(key, []))

    def write(self, key: str, value: str) -> None:
        self._data.setdefault(key, []).append(value)


@dataclass
class AppendDBHandle:
    """`DBHandle<scope, append>` — append-only access to a write-once log.

    Deliberately has no `read`: a node that can append to an audit store must not
    thereby be able to read it back. This is the least-authority sibling of
    `ReadDBHandle` (which has no `write`), and it makes the `read`/`append`
    incomparability of the mode lattice concrete at the surface. `appended`
    exposes the log for inspection by the host/tests, not through a capability
    operation the node holds."""

    scope: str
    appended: list[str] = field(default_factory=list)

    def append(self, record: str) -> None:
        self.appended.append(record)


@dataclass
class ResponseChannel:
    """`ResponseChannel<session>` — write-only sink for replies to one session."""

    session_id: str
    sent: list[str] = field(default_factory=list)

    def send(self, text: str) -> DeliveryConfirmation:
        self.sent.append(text)
        return DeliveryConfirmation(session_id=self.session_id, delivered=True)


@dataclass
class EventEmitter:
    """`EventEmitter<topic>` — write-only sink for emitting events to one topic."""

    topic: str
    emitted: list[str] = field(default_factory=list)

    def emit(self, event: str) -> None:
        self.emitted.append(event)


# ── I/O handles (clock, outbound HTTP, notification) ───────────────


@dataclass(frozen=True)
class WallTime:
    """A wall-clock reading: seconds plus nanoseconds since the epoch. Mirrors the
    `datetime` record of `wasi:clocks/wall-clock`, which is the interface the
    confined tier grants for the same capability."""

    seconds: int
    nanoseconds: int


@dataclass
class Clock:
    """`Clock` — read the current wall-clock time, and nothing else.

    The one capability kind with no scope parameter: the authority it grants has
    no narrower form. `_source` lets tests inject a fixed time; by default the
    handle reads the real clock, since a node that declares `Clock` declares
    exactly the intent to observe the world's time."""

    _source: Callable[[], WallTime] | None = None

    def now(self) -> WallTime:
        if self._source is not None:
            return self._source()
        ns = time.time_ns()
        return WallTime(seconds=ns // 1_000_000_000, nanoseconds=ns % 1_000_000_000)


@dataclass
class HTTPClient:
    """`HTTPClient<[host, ...]>` — outbound HTTP scoped to an allowlist of hosts.

    The first capability whose scope is a *set* rather than a mode or a name. The
    allowlist is enforced at the handle: a request whose host is outside it raises
    `CapabilityError`, exactly as `ToolLLM` refuses an out-of-scope tool — the
    node holds the operation, the handle holds the scope. The PoC performs no live
    network I/O: `_responses` is a canned url → body mapping seeded like `stores`,
    so what is being demonstrated is the authority boundary, not an HTTP stack."""

    allowlist: frozenset[str]
    _responses: Mapping[str, str] = field(default_factory=dict)

    def get(self, url: str) -> str:
        host = urlsplit(url).hostname
        if host is None or host not in self.allowlist:
            raise CapabilityError(
                f"node attempted HTTP to host {host!r} outside its "
                f"allowlist {sorted(self.allowlist)}"
            )
        return self._responses.get(url, "")


@dataclass
class Notifier:
    """`Notifier<channel>` — write-only sink for notifications to one channel.
    Structurally a sibling of `EventEmitter`: the outbound side of the feed-triage
    toy, and the simplest of the three I/O kinds."""

    channel: str
    sent: list[str] = field(default_factory=list)

    def notify(self, message: str) -> None:
        self.sent.append(message)


# ── Provisioning: capability type string → handle instance ─────────


def _llm_tools(app: TApp) -> frozenset[str] | None:
    """Tool set granted by an `LLMClient<...>` type, or None if unrecognised.
    `LLMClient<inference>` → empty set; `LLMClient<[a, b]>` → {a, b}."""
    if app.head != "LLMClient" or len(app.args) != 1:
        return None
    arg = app.args[0]
    if isinstance(arg, TName) and arg.name == "inference":
        return frozenset()
    if isinstance(arg, TList):
        names = {i.name for i in arg.items if isinstance(i, TName)}
        if len(names) != len(arg.items):
            return None
        return frozenset(names)
    return None


def provision(
    cap_type: str,
    *,
    backend: LLMBackend,
    stores: Mapping[str, Mapping[str, list[str]]],
    web: Mapping[str, str] | None = None,
):
    """Construct the capability handle named by a graph parameter/`with` type.

    `stores` maps a database scope name (e.g. 'knowledge-base') to its contents;
    `web` maps a URL to its canned response body (the PoC performs no live network
    I/O). Raises ValueError for capability shapes the PoC does not model."""
    ast = parse_type(cap_type)

    if isinstance(ast, TName) and ast.name == "Clock":
        return Clock()

    if not isinstance(ast, TApp):
        raise ValueError(f"not a capability type: {cap_type!r}")

    if ast.head == "LLMClient":
        tools = _llm_tools(ast)
        if tools is None:
            raise ValueError(f"unrecognised LLMClient shape: {cap_type!r}")
        return InferenceLLM(backend) if not tools else ToolLLM(backend, tools)

    if ast.head == "DBHandle":
        if len(ast.args) != 2 or not isinstance(ast.args[0], TString):
            raise ValueError(f"unrecognised DBHandle shape: {cap_type!r}")
        scope = ast.args[0].value
        mode = ast.args[1]
        mode_name = mode.name if isinstance(mode, TName) else ""
        contents = stores.get(scope, {})
        if mode_name == "read":
            # Read-only: a shallow copy suffices since the handle never mutates.
            return ReadDBHandle(scope, dict(contents))
        if mode_name == "read-write":
            # Writable: deep-copy the list values so writes stay local to this
            # assembly and never leak into the shared `stores` mapping.
            return ReadWriteDBHandle(scope, {k: list(v) for k, v in contents.items()})
        if mode_name == "append":
            # Append-only log; starts empty (audit stores are written, not seeded).
            return AppendDBHandle(scope)
        raise ValueError(
            f"unrecognised DBHandle mode {mode_name!r} in {cap_type!r}; "
            f"modes are read, read-write, append"
        )

    if ast.head == "ResponseChannel":
        scope = _scope_label(ast)
        return ResponseChannel(session_id=scope)

    if ast.head == "EventEmitter":
        scope = _scope_label(ast)
        return EventEmitter(topic=scope)

    if ast.head == "HTTPClient":
        hosts = _http_hosts(ast)
        if hosts is None:
            raise ValueError(
                f"unrecognised HTTPClient shape: {cap_type!r}; the scope is a "
                f"non-empty list of string-literal hosts"
            )
        return HTTPClient(allowlist=hosts, _responses=dict(web or {}))

    if ast.head == "Notifier":
        return Notifier(channel=_scope_label(ast))

    raise ValueError(f"unknown capability kind: {cap_type!r}")


def _http_hosts(app: TApp) -> frozenset[str] | None:
    """The host allowlist of an `HTTPClient<[...]>` type, or None if the shape is
    not a non-empty list of string literals."""
    if len(app.args) != 1:
        return None
    arg = app.args[0]
    if not isinstance(arg, TList) or not arg.items:
        return None
    hosts: set[str] = set()
    for item in arg.items:
        if not isinstance(item, TString):
            return None
        hosts.add(item.value)
    return frozenset(hosts)


def _scope_label(app: TApp) -> str:
    if not app.args:
        return ""
    arg = app.args[0]
    if isinstance(arg, TString):
        return arg.value
    if isinstance(arg, TName):
        return arg.name
    return ""


# ── Runtime revocation and rotation: the ocap caretaker pattern ────
#
# Provisioning binds a capability instance for a whole run. Revocation withdraws
# one instance's authority *mid-run*, and rotation re-points it at a new resource,
# both without touching the graph. The mechanism is Miller's caretaker
# (`@miller_robust_2006`): a node holds a forwarding proxy (the `Caretaker`), and
# *separate* authorities administer it — a `Revoker` severs it, a `Rotator`
# re-points it. Using a capability and administering it are different authorities:
# a node receives only the caretaker, never a revoker or rotator.
#
# One cell, three roles. The caretaker forwards to the cell's *current* target and
# raises if the cell is severed; a Revoker sets `revoked`, a Rotator sets `target`.
# Revocation and rotation are thus two levers on one indirection, not two
# mechanisms — and severed wins (a revoked instance stays revoked after a rotate).


@dataclass
class _Cell:
    """The mutable state a caretaker shares with its revoker/rotator: the current
    forwarding `target` and whether the instance has been severed. Kept in its own
    cell so the authorities never reach into the caretaker (or each other) — the
    caretaker only reads it, a `Revoker` only sets `revoked`, a `Rotator` only sets
    `target`."""

    target: object
    revoked: bool = False


class Caretaker:
    """A severable, re-pointable forwarding proxy for a capability handle.

    Delegates the current target's *entire* surface via `__getattr__`, so a node
    cannot distinguish a caretaker from the bare handle through the capability
    operations (`send` / `read` / `infer` / `respond` / `emit`) — the absence of a
    method is forwarded too (a caretaker over `InferenceLLM` reports no `respond`).
    Once severed, every attribute access raises `RevokedCapabilityError`; after a
    rotation, accesses are served by the new target.

    The caretaker deliberately exposes *no* revoke or rotate operation: those go
    through the paired `Revoker` / `Rotator`, which a node never holds. The checks
    fire at attribute-*fetch* time; because the PoC executor runs nodes
    synchronously, revocation and rotation are well-defined only *between* node
    runs (a node that already fetched a method finishes its own run), which matches
    the design's scope."""

    def __init__(self, cell: _Cell):
        # Set through object.__setattr__ so `_cell` is a real instance attribute
        # (found by normal lookup) and never falls through to __getattr__ below.
        object.__setattr__(self, "_cell", cell)

    def __getattr__(self, name: str):
        # Reached only for attributes the caretaker itself lacks — i.e. everything
        # belonging to the target handle. That is precisely the transparency: the
        # caretaker owns nothing but its one private slot, so all real use routes
        # here and hits the revoked check first, then the *current* target.
        cell = object.__getattribute__(self, "_cell")
        if cell.revoked:
            raise RevokedCapabilityError(
                f"{type(cell.target).__name__} capability was revoked; attempted use of {name!r}"
            )
        return getattr(cell.target, name)


class Revoker:
    """The authority to sever one caretaker — held by the host, never by a node.

    A distinct object from the caretaker it governs (they share only a `_Cell`), so
    revoking is administratively separate from using. Revocation is idempotent:
    severing an already-severed instance is a no-op, and it wins over rotation (a
    revoked instance stays revoked)."""

    def __init__(self, cell: _Cell):
        self._cell = cell

    def revoke(self) -> None:
        self._cell.revoked = True

    @property
    def revoked(self) -> bool:
        return self._cell.revoked


class Rotator:
    """The authority to re-point one caretaker at a new backing handle — held by
    the host, never by a node.

    A distinct object from the caretaker and from any `Revoker` over the same
    instance; they share only the `_Cell`. The replacement must be the *same
    capability kind* as the current target, so the surface the node holds cannot
    change kind underneath it. Rotating a severed instance is allowed but pointless
    — the revoked flag still wins, so use continues to fail."""

    def __init__(self, cell: _Cell):
        self._cell = cell

    def rotate(self, new_handle: object) -> None:
        current = self._cell.target
        if type(new_handle) is not type(current):
            raise CapabilityError(
                f"cannot rotate a {type(current).__name__} capability to a "
                f"{type(new_handle).__name__}; rotation preserves capability kind"
            )
        self._cell.target = new_handle

    @property
    def target(self) -> object:
        return self._cell.target


def manage(
    handle: object, *, revocable: bool = False, rotatable: bool = False
) -> tuple[Caretaker, Revoker | None, Rotator | None]:
    """Wrap a handle in a caretaker and mint the requested host-side authorities.

    Grant revoke and rotate independently (least authority): `revocable=True` mints
    a `Revoker`, `rotatable=True` mints a `Rotator`, both mints both — all over one
    caretaker and one shared cell. A node receives only the caretaker; the minted
    authorities stay with the host. Returns `(caretaker, revoker_or_None,
    rotator_or_None)`."""
    cell = _Cell(target=handle)
    caretaker = Caretaker(cell)
    revoker = Revoker(cell) if revocable else None
    rotator = Rotator(cell) if rotatable else None
    return caretaker, revoker, rotator


def revocable(handle: object) -> tuple[Caretaker, Revoker]:
    """Convenience: wrap a handle so its authority can be withdrawn at runtime.

    Returns a `(caretaker, revoker)` pair. Give the caretaker to the node (it
    forwards to `handle` until severed, then raises `RevokedCapabilityError`) and
    keep the revoker with the host. Thin wrapper over `manage(revocable=True)`."""
    caretaker, revoker, _ = manage(handle, revocable=True)
    assert revoker is not None
    return caretaker, revoker


def rotatable(handle: object) -> tuple[Caretaker, Rotator]:
    """Convenience: wrap a handle so it can be re-pointed at a new resource at
    runtime. Returns a `(caretaker, rotator)` pair. Thin wrapper over
    `manage(rotatable=True)`."""
    caretaker, _, rotator = manage(handle, rotatable=True)
    assert rotator is not None
    return caretaker, rotator
