"""Attenuation at the routing point: a routed handle narrowed to the child's type.

A parent may route a sub-graph a handle wider than the one the sub-graph declares.
The cross-graph validator accepts that as capability narrowing
(`type_parser.is_assignable`): a superset allowlist or tool set, a mode that covers
the declared one, a payee set and cap that cover the declared ones. Until this
module existed the runtime then routed the parent's handle whole, so narrowing was
checked and not enforced. Now `_route_handles` passes every routed handle through
`attenuate`, and the child receives a **facade** limited to its declared type.

Three properties, each tested in `tests/test_poc_attenuation.py`:

* **The facade holds the parent's handle as routed, never what is behind it.** If
  that handle is a caretaker, every operation goes through the caretaker, so a
  revocation at the parent severs the child's narrowed view, and a rotation
  re-points it. Nothing is copied: the child reads the store the parent writes.
* **Its surface is the declared type's, and nothing else.** A `read` facade over a
  `read-write` handle has `read` and `scope`; it has no `write`, and no field
  through which the store behind it can be reached. A facade has no `__getattr__`,
  so nothing the facade does not define falls through.
* **A scope enforced inside an operation is passed down, not re-implemented.** An
  LLM's tool set governs a loop (which tools are offered, which calls are allowed),
  an HTTP allowlist governs every redirect hop, and a payee set may be read from
  the bank. A facade cannot check those from outside. It passes its scope to the
  handle as `within`, and the handle enforces its own scope and each bound in
  `within`. A bound only narrows, and a nested facade adds its own, so narrowing
  composes across any number of boundaries.

Not changed: on the host tier this is host-discipline enforcement, as every handle
is. A hostile Python body can still reach around the object model (the facade's
slots, or `import os`). On the confined tier the facade is what the host adapter
calls, behind the component's WIT imports.

A handle routed at exactly its declared type passes through untouched.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from decimal import Decimal
from typing import Any

from type_parser import (
    PaymentsScope,
    TApp,
    TName,
    TString,
    Type,
    is_assignable,
    parse_type,
    payments_scope,
    profile_fields,
    scheduled_scope,
)

from .handles import CapabilityError, InferenceLLM, _http_hosts, _llm_tools


class AttenuationError(RuntimeError):
    """A routed type is not a narrowing of the provided one, or no facade exists
    for the pair. The validator refuses both before anything runs; this keeps the
    routing point from minting authority if it were ever bypassed."""


# ── The facades ─────────────────────────────────────────────────────


class _Facade:
    """Base of every facade: one slot holding the routed handle as routed. No
    `__getattr__`, so the surface is exactly what a subclass defines."""

    __slots__ = ("_inner",)

    def __init__(self, inner: object):
        object.__setattr__(self, "_inner", inner)

    def __setattr__(self, name: str, value: object) -> None:
        raise AttributeError(f"{type(self).__name__} is read-only")

    def __repr__(self) -> str:
        return f"<{type(self).__name__}>"


class InferenceFacade(_Facade):
    """`LLMClient<inference>` over a tool-scoped client: the model, no tools. The
    validator refuses this routing (a tool client in an inference slot is out of
    the sink rule's sight); the facade exists so attenuation is total over
    `is_assignable`."""

    __slots__ = ()

    @property
    def backend(self) -> Any:
        return self._inner.backend  # type: ignore[attr-defined]

    def infer(self, *, system: str, prompt: str, task: str) -> str:
        return InferenceLLM(self._inner.backend).infer(  # type: ignore[attr-defined]
            system=system, prompt=prompt, task=task
        )


class ToolFacade(_Facade):
    """`LLMClient<[tools]>` over a client holding more tools."""

    __slots__ = ("_tools",)

    def __init__(self, inner: object, tools: frozenset[str]):
        super().__init__(inner)
        object.__setattr__(self, "_tools", tools)

    @property
    def allowed_tools(self) -> frozenset[str]:
        return self._tools

    @property
    def backend(self) -> Any:
        # The confined adapter calls the backend directly and offers
        # `allowed_tools`, which is this facade's; the component's imports bound
        # what it can act on.
        return self._inner.backend  # type: ignore[attr-defined]

    def respond(
        self,
        *,
        system: str,
        prompt: str,
        tools: Mapping[str, Callable[..., str]] | None = None,
        within: tuple[frozenset[str], ...] = (),
    ) -> str:
        return self._inner.respond(  # type: ignore[attr-defined]
            system=system, prompt=prompt, tools=tools, within=(self._tools, *within)
        )


class AllowlistFacade(_Facade):
    """`HTTPClient<[hosts]>` over a client allowed more hosts. The bound reaches
    every redirect hop, because the handle applies it there."""

    __slots__ = ("_hosts",)

    def __init__(self, inner: object, hosts: frozenset[str]):
        super().__init__(inner)
        object.__setattr__(self, "_hosts", hosts)

    @property
    def allowlist(self) -> frozenset[str]:
        return self._hosts

    def get(self, url: str, *, within: tuple[frozenset[str], ...] = ()) -> str:
        return self._inner.get(url, within=(self._hosts, *within))  # type: ignore[attr-defined]

    def fetch(self, url: str, *, within: tuple[frozenset[str], ...] = ()) -> Any:
        return self._inner.fetch(url, within=(self._hosts, *within))  # type: ignore[attr-defined]


class ReadDBFacade(_Facade):
    """`DBHandle<scope, read>` over `read-write`: `read`, no `write`."""

    __slots__ = ()

    @property
    def scope(self) -> str:
        return self._inner.scope  # type: ignore[attr-defined]

    def read(self, key: str) -> list[str]:
        return self._inner.read(key)  # type: ignore[attr-defined]


class AppendDBFacade(_Facade):
    """`DBHandle<scope, append>` over `read-write`: `append`, no `read`. The record
    goes through the handle's own `append`, which `read-write` has because the mode
    lattice says it covers `append`."""

    __slots__ = ()

    @property
    def scope(self) -> str:
        return self._inner.scope  # type: ignore[attr-defined]

    def append(self, record: str) -> None:
        self._inner.append(record)  # type: ignore[attr-defined]


class ReadStateFacade(_Facade):
    """`StateHandle<'name', read>` over `read-write`: `get`, no `put` or `delete`."""

    __slots__ = ()

    @property
    def name(self) -> str:
        return self._inner.name  # type: ignore[attr-defined]

    def get(self, key: str) -> str | None:
        return self._inner.get(key)  # type: ignore[attr-defined]


class _ScopedFacade(_Facade):
    """A facade carrying a parsed banking scope, which it passes down as `within`."""

    __slots__ = ("_scope",)

    def __init__(self, inner: object, scope: Any):
        super().__init__(inner)
        object.__setattr__(self, "_scope", scope)

    @property
    def scope(self) -> Any:
        return self._scope


class PaymentsFacade(_ScopedFacade):
    """`Payments<[payees], cap>` over a wider payee set or cap."""

    __slots__ = ()

    def send(
        self, recipient: str, amount: float, subject: str, date: str, *, within: tuple = ()
    ) -> Any:
        return self._inner.send(  # type: ignore[attr-defined]
            recipient, amount, subject, date, within=(self._scope, *within)
        )


class RecurringPaymentsFacade(_ScopedFacade):
    """`Payments<[payees], cap, recurring>` over a wider one."""

    __slots__ = ()

    def schedule(
        self,
        recipient: str,
        amount: float,
        subject: str,
        date: str,
        recurring: bool,
        *,
        within: tuple = (),
    ) -> Any:
        return self._inner.schedule(  # type: ignore[attr-defined]
            recipient, amount, subject, date, recurring, within=(self._scope, *within)
        )


class ScheduledFacade(_ScopedFacade):
    """`ScheduledPayments<[orders], [fields]>` over more orders or fields."""

    __slots__ = ()

    def update(self, id: int, *, within: tuple = (), **changes: Any) -> Any:
        return self._inner.update(id, within=(self._scope, *within), **changes)  # type: ignore[attr-defined]


class ProfileFacade(_Facade):
    """`UserProfile<[fields]>` over more fields."""

    __slots__ = ("_fields",)

    def __init__(self, inner: object, fields: frozenset[str]):
        super().__init__(inner)
        object.__setattr__(self, "_fields", fields)

    @property
    def fields(self) -> frozenset[str]:
        return self._fields

    def update(self, *, within: tuple = (), **changes: Any) -> Any:
        return self._inner.update(within=(self._fields, *within), **changes)  # type: ignore[attr-defined]


# ── A grant bound to run-time values (value-bound grants) ───────────
#
# A node's `bind` narrows a `Payments` grant it holds to values its own inputs
# carry: a payee, an amount, a number of uses. The runtime resolves the paths when
# the node activates, and wraps the handle it routed in a `BoundPaymentsFacade`.
# The bound is a `PaymentsScope` passed down as `within`, so the handle checks it
# exactly as it checks a routing-point facade's; the static type stays the upper
# bound, because the handle still checks its own scope. The bound amount is a cap
# (design D4): a payment may not exceed it. The facade sits outermost, so it
# composes with any routing-point narrowing beneath it.


class BindError(RuntimeError):
    """A bind's value is not one a bound scope can hold."""


def bound_scope(static: Any, payee: object = None, amount: object = None) -> Any:
    """`static` (a `PaymentsScope`) narrowed to `payee` and `amount` where given.
    With no payee bound, the static payees are kept; with no amount, the static cap.
    Both are values from a node's input, so their types are checked here too."""
    literal, dynamic, cap = static.literal, static.dynamic, static.cap
    if payee is not None:
        if not isinstance(payee, str) or not payee:
            raise BindError(f"a bound payee must be a non-empty string, not {payee!r}")
        literal, dynamic = frozenset({payee}), frozenset()
    if amount is not None:
        if isinstance(amount, bool) or not isinstance(amount, int | float) or amount <= 0:
            raise BindError(f"a bound amount must be a positive number, not {amount!r}")
        cap = Decimal(str(amount))
    return PaymentsScope(literal, dynamic, cap, static.recurring)


class _BoundFacade(_ScopedFacade):
    """A `Payments` handle bound for one activation: the bound scope passed down as
    `within`, and `uses` payments at most. Only a call that returns spends a use: a
    call refused by a scope (`CapabilityError`), by the bank (`BankError`) or failing
    any other way spends none."""

    __slots__ = ("_left",)

    def __init__(self, inner: object, scope: Any, uses: int):
        super().__init__(inner, scope)
        if isinstance(uses, bool) or not isinstance(uses, int) or uses < 1:
            raise BindError(f"`uses` must be a positive integer, not {uses!r}")
        object.__setattr__(self, "_left", [uses])

    @property
    def uses_left(self) -> int:
        return self._left[0]  # type: ignore[attr-defined]

    def _spend(self, call: Callable[[], Any]) -> Any:
        if self._left[0] < 1:  # type: ignore[attr-defined]
            raise CapabilityError("the bound grant is spent: no uses are left")
        result = call()
        self._left[0] -= 1  # type: ignore[attr-defined]
        return result


class BoundPaymentsFacade(_BoundFacade):
    """`Payments<…>` bound: `send` only."""

    __slots__ = ()

    def send(
        self, recipient: str, amount: float, subject: str, date: str, *, within: tuple = ()
    ) -> Any:
        return self._spend(
            lambda: self._inner.send(  # type: ignore[attr-defined]
                recipient, amount, subject, date, within=(self._scope, *within)
            )
        )


class BoundRecurringPaymentsFacade(_BoundFacade):
    """`Payments<…, recurring>` bound: `schedule` only."""

    __slots__ = ()

    def schedule(
        self,
        recipient: str,
        amount: float,
        subject: str,
        date: str,
        recurring: bool,
        *,
        within: tuple = (),
    ) -> Any:
        return self._spend(
            lambda: self._inner.schedule(  # type: ignore[attr-defined]
                recipient, amount, subject, date, recurring, within=(self._scope, *within)
            )
        )


def resolve_path(inputs: tuple, path: str) -> object:
    """The value `path` (`inN.field...`) names in a node's data inputs. Raises
    `BindError` where it does not resolve: a bind never falls back to the static
    bound."""
    from graph_validator import BIND_PATH

    m = BIND_PATH.fullmatch(path) if isinstance(path, str) else None
    if m is None:
        raise BindError(f"{path!r} is not a path of the form inN.field")
    index = int(m.group(1))
    if index >= len(inputs):
        raise BindError(f"{path!r} names input {index}, but the node has {len(inputs)}")
    value = inputs[index]
    for part in filter(None, m.group(2).split(".")):
        if not isinstance(value, Mapping) or part not in value:
            raise BindError(f"{path!r} does not resolve: no field {part!r}")
        value = value[part]
    return value


def bind_from(handle: object, grant: str, spec: Mapping[str, Any], inputs: tuple) -> object:
    """`handle` bound by `spec` (a node's bind on `grant`), its paths resolved
    against `inputs`, one activation's data values."""
    values = {f: resolve_path(inputs, spec[f]) for f in ("payee", "amount") if f in spec}
    return bind(handle, grant, uses=spec.get("uses"), **values)  # type: ignore[arg-type]


def bind(handle: object, grant: str, payee: object = None, amount: object = None,
         uses: int = 1) -> _BoundFacade:  # fmt: skip
    """`handle`, held as `grant`, bound to `payee`, `amount` and `uses`."""
    scope = payments_scope(parse_type(grant))
    if scope is None:
        raise BindError(f"{grant!r} is not a bindable grant")
    cls = BoundRecurringPaymentsFacade if scope.recurring else BoundPaymentsFacade
    return cls(handle, bound_scope(scope, payee, amount), uses)


# ── Choosing a facade ───────────────────────────────────────────────


def _mode(t: TApp) -> str:
    arg = t.args[1] if len(t.args) == 2 else None
    return arg.name if isinstance(arg, TName) else ""


def attenuate(handle: object, provided: str, expected: str) -> object:
    """`handle`, provisioned for `provided`, as the child declaring `expected`
    may hold it. Returns `handle` itself when the two types are equal."""
    pa: Type = parse_type(provided)
    ea: Type = parse_type(expected)
    if pa == ea:
        return handle
    if not is_assignable(pa, ea):
        raise AttenuationError(f"{provided!r} → {expected!r} is not a narrowing")
    facade = _facade(handle, ea)
    if facade is None:
        raise AttenuationError(f"no facade narrows {provided!r} to {expected!r}")
    return facade


def _facade(handle: object, ea: Type) -> object | None:
    if not isinstance(ea, TApp):
        return None
    head = ea.head
    if head == "LLMClient":
        tools = _llm_tools(ea)
        if tools is None:
            return None
        return InferenceFacade(handle) if not tools else ToolFacade(handle, tools)
    if head == "HTTPClient":
        hosts = _http_hosts(ea)
        return None if hosts is None else AllowlistFacade(handle, hosts)
    if head == "DBHandle" and isinstance(ea.args[0], TString):
        return {"read": ReadDBFacade, "append": AppendDBFacade}.get(_mode(ea), _none)(handle)
    if head == "StateHandle" and _mode(ea) == "read":
        return ReadStateFacade(handle)
    if head == "Payments":
        scope = payments_scope(ea)
        if scope is None:
            return None
        return (RecurringPaymentsFacade if scope.recurring else PaymentsFacade)(handle, scope)
    if head == "ScheduledPayments":
        sched = scheduled_scope(ea)
        return None if sched is None else ScheduledFacade(handle, sched)
    if head == "UserProfile":
        fields = profile_fields(ea)
        return None if fields is None else ProfileFacade(handle, fields)
    return None


def _none(_handle: object) -> None:
    return None
