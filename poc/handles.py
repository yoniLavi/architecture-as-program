"""Capability handles — the runtime form of the proposal's `with` clauses.

Each handle is an object whose available operations match its declared scope.
This is where "capabilities as declared requirements" becomes concrete: a node
receives handle objects as explicit arguments and has no other way to reach
external authority. The handle's *surface* is the enforcement:

* `InferenceLLM`  (`LLMClient<inference>`)   — model access, NO tool calling.
* `ToolLLM`       (`LLMClient<[tools]>`)     — model access + only its named tools.
* `ReadDBHandle`  (`DBHandle<scope, read>`)  — read only, scoped to one store.
* `ResponseChannel`(`ResponseChannel<...>`)  — write-only sink.
* `EventEmitter`  (`EventEmitter<topic>`)    — write-only sink.

Fidelity: this is host-discipline enforcement. `InferenceLLM` *has no* tool
method, so a node holding one cannot call a tool — but Python cannot stop a
malicious node from reaching around the object model entirely (e.g. `import os`).
Unforgeable confinement is the job of the WASM/WASI tier (a later change).
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field

from type_parser import TApp, TList, TName, TString, parse_type

from .llm import LLMBackend, LLMRequest
from .values import DeliveryConfirmation


class CapabilityError(RuntimeError):
    """Raised when code attempts to exercise authority a handle does not grant —
    e.g. calling a tool outside an `LLMClient`'s allowlist."""


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
):
    """Construct the capability handle named by a graph parameter/`with` type.

    `stores` maps a database scope name (e.g. 'knowledge-base') to its contents.
    Raises ValueError for capability shapes the PoC does not model."""
    ast = parse_type(cap_type)
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
        if mode_name != "read":
            # The security vertical only needs read; widening modes are a
            # straightforward extension but out of scope for this slice.
            raise ValueError(f"PoC models only read-mode DBHandle, got: {cap_type!r}")
        return ReadDBHandle(scope, dict(stores.get(scope, {})))

    if ast.head == "ResponseChannel":
        scope = _scope_label(ast)
        return ResponseChannel(session_id=scope)

    if ast.head == "EventEmitter":
        scope = _scope_label(ast)
        return EventEmitter(topic=scope)

    raise ValueError(f"unknown capability kind: {cap_type!r}")


def _scope_label(app: TApp) -> str:
    if not app.args:
        return ""
    arg = app.args[0]
    if isinstance(arg, TString):
        return arg.value
    if isinstance(arg, TName):
        return arg.name
    return ""
