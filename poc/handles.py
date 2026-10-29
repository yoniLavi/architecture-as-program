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
* `ReadStateHandle`  (`StateHandle<name, read>`)    — look up a key in one named store.
* `ReadWriteStateHandle` (`StateHandle<name, read-write>`) — read and change it.

The three `DBHandle` surfaces make the mode lattice concrete: `read-write` covers both `read` and
`append`, while `read` and `append` are mutually incomparable — neither handle's operations are a
superset of the other's (a reader cannot append; an appender cannot read).

Fidelity: this is host-discipline enforcement. `InferenceLLM` *has no* tool
method, so a node holding one cannot call a tool — but Python cannot stop a
malicious node from reaching around the object model entirely (e.g. `import os`).
Unforgeable confinement is the job of the WASM/WASI tier (a later change).
"""

from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
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


class RedirectRefused(CapabilityError):
    """A permitted fetch whose *server* answered with a redirect to a host outside
    the allowlist. The hop is never followed. A `CapabilityError`, because the
    allowlist is what refused it — and its own class, because the reach was the
    remote server's rather than the node's (see `HTTPClient.fetch`)."""


class FetchError(RuntimeError):
    """A permitted fetch that failed: a timeout, a refused connection, an HTTP
    error status, or a response over the size cap. Not a `CapabilityError` — the
    node was entitled to ask, and the world said no."""


@dataclass(frozen=True)
class FetchResult:
    """The outcome of `HTTPClient.fetch`: a body, or the reason there is none.
    Mirrors the `fetch-result` variant of the `http-client` WIT interface."""

    ok: bool
    body: str = ""
    error: str = ""


# Bounds on a live fetch. A feed is text; five mebibytes is far more than any
# feed worth reading, and far less than a response that could exhaust the host.
HTTP_MAX_BYTES = 5 * 1024 * 1024
HTTP_TIMEOUT_S = 15.0
HTTP_USER_AGENT = "architecture-as-program-feed-triage/0.1"


@dataclass
class HTTPClient:
    """`HTTPClient<[host, ...]>` — outbound HTTP scoped to an allowlist of hosts.

    The first capability whose scope is a *set* rather than a mode or a name. The
    allowlist is enforced at the handle: a request whose host is outside it raises
    `CapabilityError`, exactly as `ToolLLM` refuses an out-of-scope tool — the
    node holds the operation, the handle holds the scope.

    Two modes. By default `_responses` is a canned url → body mapping seeded like
    `stores`, and no network I/O happens: every test and the build run this way.
    With `live=True` the handle performs a real GET, bounded four ways — the
    allowlist, a response size cap, a timeout, and a redirect policy that applies
    the same allowlist check to every hop, so an allowlisted host cannot bounce the
    request somewhere the graph never named.

    Two operations over the one scope. `get` returns the body and raises on any
    failure. `fetch` returns transport failures as values (`FetchResult`), so a node
    reading several feeds survives one of them being down — but a request *the
    node makes* outside the allowlist raises from both: that is not a failed fetch,
    it is a node reaching for authority it was not granted, and it must not be
    collectable as an error string. A *redirect* off the allowlist is refused in
    both, and never followed; `fetch` reports it as that feed's failure, since the
    reach was the server's."""

    allowlist: frozenset[str]
    _responses: Mapping[str, str] = field(default_factory=dict)
    live: bool = False
    max_bytes: int = HTTP_MAX_BYTES
    timeout: float = HTTP_TIMEOUT_S

    def _check(self, url: str) -> None:
        # Refuse what parsers disagree on before reading the host: a backslash is a
        # path separator to a WHATWG client and userinfo to `urlsplit`, so
        # `https://evil.example\@feeds.example.com/` passed here and would reach
        # `evil.example` (round L, 30 September 2026). Only http(s) is HTTP, and a
        # hostname is case-insensitive.
        parts = urlsplit(url)
        host = parts.hostname
        if "\\" in url or parts.scheme not in ("http", "https") or parts.username is not None:
            host = None
        allowed = {h.lower() for h in self.allowlist}
        if host is None or host not in allowed:
            raise CapabilityError(
                f"node attempted HTTP to host {host!r} outside its "
                f"allowlist {sorted(self.allowlist)}"
            )

    def get(self, url: str) -> str:
        self._check(url)
        if not self.live:
            return self._responses.get(url, "")
        return self._live_get(url)

    def fetch(self, url: str) -> FetchResult:
        self._check(url)
        if not self.live:
            if url not in self._responses:
                return FetchResult(ok=False, error="no response")
            return FetchResult(ok=True, body=self._responses[url])
        try:
            return FetchResult(ok=True, body=self._live_get(url))
        except FetchError as e:
            return FetchResult(ok=False, error=str(e))
        except RedirectRefused as e:
            # Refused either way — no request is made to the off-list host. What
            # differs is who is told. The *node* asked for an allowlisted URL; it
            # was the remote server that pointed elsewhere, so here it is that
            # feed's failure, not the node's overreach. (Raising would let any
            # one allowlisted host fail the whole run by answering with a
            # redirect.) `get`, which has no failure value, still raises.
            return FetchResult(ok=False, error=str(e))

    def _live_get(self, url: str) -> str:
        check = self._check

        class _AllowlistedRedirects(urllib.request.HTTPRedirectHandler):
            """Apply the handle's own check to every redirect target, so an
            allowlisted host cannot bounce a request to one the graph never
            named. The hop is refused before any request is made to it."""

            def redirect_request(self, req, fp, code, msg, headers, newurl):
                try:
                    check(newurl)
                except CapabilityError as e:
                    raise RedirectRefused(f"redirect refused: {e}") from e
                return super().redirect_request(req, fp, code, msg, headers, newurl)

        opener = urllib.request.build_opener(_AllowlistedRedirects)
        request = urllib.request.Request(url, headers={"User-Agent": HTTP_USER_AGENT})
        try:
            with opener.open(request, timeout=self.timeout) as response:
                declared = response.headers.get("Content-Length")
                if declared is not None and declared.isdigit() and int(declared) > self.max_bytes:
                    raise FetchError(
                        f"response from {url} declares {declared} bytes, over the "
                        f"{self.max_bytes}-byte cap"
                    )
                # One byte past the cap is enough to know the cap was exceeded, and
                # nothing read so far is returned: a truncated feed is not a feed.
                raw = response.read(self.max_bytes + 1)
                if len(raw) > self.max_bytes:
                    raise FetchError(f"response from {url} exceeds the {self.max_bytes}-byte cap")
                charset = response.headers.get_content_charset() or "utf-8"
        except urllib.error.HTTPError as e:
            raise FetchError(f"{url}: HTTP {e.code}") from e
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            raise FetchError(f"{url}: {getattr(e, 'reason', e)}") from e
        try:
            return raw.decode(charset, errors="replace")
        except LookupError:
            return raw.decode("utf-8", errors="replace")


@dataclass
class Notifier:
    """`Notifier<channel>` — write-only sink for notifications to one channel.
    Structurally a sibling of `EventEmitter`: the outbound side of the feed-triage
    toy, and the simplest of the three I/O kinds.

    `_publish`, where the world binds one, is what a notification *does* beyond
    being recorded: the feed-triage service binds it to the local digest writer
    (`poc/digest.py`), so `Notifier<'digest'>` is a dated file on this machine and
    nothing that leaves it. Without one the handle only records, which is what
    every test not about publishing wants."""

    channel: str
    sent: list[str] = field(default_factory=list)
    _publish: Callable[[str], None] | None = None

    def notify(self, message: str) -> None:
        self.sent.append(message)
        if self._publish is not None:
            self._publish(message)


# ── Node-local state ───────────────────────────────────────────────


class StateStore:
    """One named key → string store, host-side: the thing a `StateHandle` is a
    handle *to*.

    Backed by a single JSON file when given a path, and by a dict otherwise (the
    default for tests). Every `put` and `delete` rewrites the file through a
    temporary sibling and an atomic rename, so a reader — or a restart — sees the
    old contents or the new, never half of either. That is durability enough for
    one process; two drivers at once are refused by the driver's lock file, not
    handled here."""

    def __init__(self, name: str, path: Path | None = None):
        self.name = name
        self._path = path
        self._data: dict[str, str] = {}
        if path is not None and path.exists():
            loaded = json.loads(path.read_text())
            if not isinstance(loaded, dict):
                raise ValueError(f"state store {name!r} at {path} is not a JSON object")
            self._data = {str(k): str(v) for k, v in loaded.items()}

    def get(self, key: str) -> str | None:
        return self._data.get(key)

    def put(self, key: str, value: str) -> None:
        self._data[key] = value
        self._flush()

    def delete(self, key: str) -> None:
        if self._data.pop(key, None) is not None:
            self._flush()

    def keys(self) -> list[str]:
        """For the host (the driver's report, tests). No handle exposes it: a node
        can ask about a key it knows, not enumerate the store."""
        return sorted(self._data)

    def _flush(self) -> None:
        if self._path is None:
            return
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_name(self._path.name + ".tmp")
        tmp.write_text(json.dumps(self._data, indent=1, sort_keys=True) + "\n")
        os.replace(tmp, self._path)


@dataclass
class ReadStateHandle:
    """`StateHandle<'name', read>` — look a key up in one named store. There is
    no `put`, so a node holding this cannot change what the next run will see."""

    name: str
    _store: StateStore

    def get(self, key: str) -> str | None:
        return self._store.get(key)


@dataclass
class ReadWriteStateHandle:
    """`StateHandle<'name', read-write>` — read and change one named store.

    State is a capability, not a language construct: there is no stateful
    combinator and no feedback edge in the graph. A node that remembers across
    runs says so in its `with` clause, names the store, and says whether it may
    write — which is what lets a reader see, from the graph alone, that the only
    node able to mark a feed item as seen is the last one."""

    name: str
    _store: StateStore

    def get(self, key: str) -> str | None:
        return self._store.get(key)

    def put(self, key: str, value: str) -> None:
        self._store.put(key, value)

    def delete(self, key: str) -> None:
        self._store.delete(key)


# ── The world: what outward-facing handles are bound to ────────────


_STORE_NAME = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")


@dataclass
class World:
    """What the handles that reach outside the process are bound to.

    A capability *type* says what a node may do (`HTTPClient<['feeds.example.com']>`,
    `StateHandle<'seen', read>`); it does not say whether the fetch is real or where
    the store's file lives. Those are deployment facts, and they are collected here
    so that `assemble` takes one argument for them. The default binds nothing real:
    canned HTTP, in-memory stores, notifiers that only record — the world every test
    runs in. The driver (`poc/serve.py`) binds the real one, rooted at `var/`."""

    # url → canned body, for the default (non-live) HTTP mode.
    web: Mapping[str, str] = field(default_factory=dict)
    live_http: bool = False
    # Directory holding one `<name>.json` per state store; None keeps them in memory.
    state_dir: Path | None = None
    # channel name → what a notification on it does, beyond being recorded.
    publishers: Mapping[str, Callable[[str], None]] = field(default_factory=dict)
    # Injected time, so a run is reproducible. None reads the real clock.
    clock: Callable[[], WallTime] | None = None
    # The bank the banking kinds act on (`poc/bank.py`), and that a bank-scoped
    # `DBHandle<scope, read>` reads. None binds no bank, and a banking kind is refused.
    bank: Any = None
    _stores: dict[str, StateStore] = field(default_factory=dict, repr=False)

    def store(self, name: str) -> StateStore:
        """The one store of that name. Two handles over `'seen'` — a reader's and a
        writer's — share it, which is what makes them handles to the same state."""
        if not _STORE_NAME.match(name):
            # The name comes from a type string and becomes a filename.
            raise ValueError(
                f"state store name {name!r} must be lowercase letters, digits and hyphens"
            )
        if name not in self._stores:
            path = None if self.state_dir is None else self.state_dir / f"{name}.json"
            self._stores[name] = StateStore(name, path)
        return self._stores[name]


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
    world: World | None = None,
):
    """Construct the capability handle named by a graph parameter/`with` type.

    `stores` maps a database scope name (e.g. 'knowledge-base') to its contents;
    `web` maps a URL to its canned response body. `world` binds the handles that
    reach outside the process (live HTTP, file-backed state, a publishing
    notifier); without one nothing real is bound. Raises ValueError for capability
    shapes the PoC does not model."""
    ast = parse_type(cap_type)
    world = world if world is not None else World(web=dict(web or {}))

    if isinstance(ast, TName) and ast.name == "Clock":
        return Clock(_source=world.clock)
    if isinstance(ast, TName) and ast.name == "Credentials":
        raise ValueError("Credentials is never granted: no handle exists for it")

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
        if world.bank is not None and mode_name == "read":
            from .bank import BankReadHandle, is_bank_scope

            if is_bank_scope(scope):
                return BankReadHandle(scope, world.bank)
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
        return HTTPClient(allowlist=hosts, _responses=dict(world.web), live=world.live_http)

    if ast.head == "Notifier":
        channel = _scope_label(ast)
        return Notifier(channel=channel, _publish=world.publishers.get(channel))

    if ast.head == "StateHandle":
        if len(ast.args) != 2 or not isinstance(ast.args[0], TString):
            raise ValueError(f"unrecognised StateHandle shape: {cap_type!r}")
        mode = ast.args[1].name if isinstance(ast.args[1], TName) else ""
        store = world.store(ast.args[0].value)
        if mode == "read":
            return ReadStateHandle(store.name, store)
        if mode == "read-write":
            return ReadWriteStateHandle(store.name, store)
        raise ValueError(
            f"unrecognised StateHandle mode {mode!r} in {cap_type!r}; modes are read, read-write"
        )

    if ast.head in ("Payments", "ScheduledPayments", "UserProfile"):
        return _provision_banking(cap_type, ast, world)

    raise ValueError(f"unknown capability kind: {cap_type!r}")


def _provision_banking(cap_type: str, ast: TApp, world: World) -> object:
    """A banking handle over the world's bank, its scope parsed by the same
    function the validator's narrowing rule reads. `Credentials` never reaches
    here: it is a bare name, refused above as no capability this runtime grants."""
    from type_parser import payments_scope, profile_fields, scheduled_scope

    from .bank import (
        PaymentsHandle,
        RecurringPaymentsHandle,
        ScheduledPaymentsHandle,
        UserProfileHandle,
    )

    if world.bank is None:
        raise ValueError(f"{cap_type!r} needs a bank, and this world binds none")
    if ast.head == "Payments":
        scope = payments_scope(ast)
        if scope is not None:
            cls = RecurringPaymentsHandle if scope.recurring else PaymentsHandle
            return cls(scope, world.bank)
    elif ast.head == "ScheduledPayments":
        sched = scheduled_scope(ast)
        if sched is not None:
            return ScheduledPaymentsHandle(sched, world.bank)
    else:
        fields = profile_fields(ast)
        if fields is not None:
            return UserProfileHandle(fields, world.bank)
    raise ValueError(f"unrecognised {ast.head} shape: {cap_type!r}")


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
