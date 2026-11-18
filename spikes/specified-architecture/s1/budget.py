"""S1: budgets as capability scopes. A spike, imported by no build step.

Three parts, kept apart because they are different claims (design D5):

* **Narrowing.** A budget is a trailing scope argument on a handle's type, in a form
  the existing parser already accepts: `LLMClient<inference, Calls<'5'>>`,
  `StateHandle<'seen', read-write, Bytes<'5242880'>>`,
  `HTTPClient<['a.example'], Requests<'50'>>`. `is_assignable` here strips the
  budget arguments, asks `type_parser.is_assignable` about the rest unchanged, and
  then compares budgets: an absent budget is unbounded, so a parent may route an
  unbudgeted or larger-budget handle to a child declaring a smaller one, never the
  reverse.
* **Metering.** Narrowing alone is unsound for budgets, because a budget is spent
  and a set scope is not: two children may each declare `Calls<'5'>` under a
  parent's `Calls<'5'>` and both pass. So every budget is a `Meter`, and a child's
  meter is *beneath* its parent's (KeyKOS meters): a charge is checked against the
  meter and every ancestor before it lands, all or nothing. The parent's total
  therefore holds at run time, however many children it has.
* **Totals** are a static analysis over the graph's shape, and are not here.

Exhaustion is `BudgetExhausted`, which is deliberately *not* a `CapabilityError`:
the node held the authority and used it up, which is a different event from
reaching for authority it was never granted, and a reader (or a model being
told why its code failed) must be able to tell them apart.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from type_parser import TApp, TString, Type, parse_type
from type_parser import is_assignable as _base_assignable

from poc.llm import LLMRequest, LLMResponse

# The budget kinds a handle may carry, and what each counts.
BUDGET_KINDS: dict[str, str] = {
    "Calls": "calls through the handle (counted before each call)",
    "Tokens": "output tokens the backend reports (counted after each call)",
    "Requests": "network requests (counted before each request)",
    "Bytes": "bytes written to storage (counted before each write)",
}


class BudgetError(ValueError):
    """A budget is malformed: unknown kind, non-integer or non-positive amount, a
    kind given twice, or a token budget over a backend that reports no tokens."""


class BudgetExhausted(RuntimeError):
    """A budget was spent. Not a capability error: the authority was granted."""

    def __init__(self, kind: str, limit: int, spent: int, meter: str):
        self.kind, self.limit, self.spent, self.meter = kind, limit, spent, meter
        super().__init__(
            f"budget exhausted: {kind} at meter {meter!r} has spent {spent} of {limit}"
        )


# ── Narrowing ───────────────────────────────────────────────────────


def _budget_arg(arg: Type) -> tuple[str, int] | None:
    if isinstance(arg, TApp) and arg.head in BUDGET_KINDS:
        if len(arg.args) != 1 or not isinstance(arg.args[0], TString):
            raise BudgetError(f"{arg.head} takes one quoted integer")
        text = arg.args[0].value
        if not text.isdigit() or int(text) <= 0:
            raise BudgetError(f"{arg.head}<{text!r}> is not a positive integer")
        return arg.head, int(text)
    return None


def split(t: Type | str) -> tuple[Type, dict[str, int]]:
    """A handle type without its budget arguments, and the budgets. Budget
    arguments must trail the type's own arguments."""
    if isinstance(t, str):
        t = parse_type(t)
    if not isinstance(t, TApp):
        return t, {}
    budgets: dict[str, int] = {}
    args = list(t.args)
    while args:
        b = _budget_arg(args[-1])
        if b is None:
            break
        if b[0] in budgets:
            raise BudgetError(f"{b[0]} given twice")
        budgets[b[0]] = b[1]
        args.pop()
    for a in args:
        if _budget_arg(a) is not None:
            raise BudgetError("budget arguments must trail the type's own arguments")
    return TApp(t.head, tuple(args)), budgets


def is_assignable(actual: Type | str, target: Type | str) -> bool:
    """`actual` (what the parent routes) may stand in for `target` (what the child
    declares): the base types narrow as before, and every budget the actual carries
    is covered by one the target carries at most as large."""
    abase, abud = split(actual)
    tbase, tbud = split(target)
    if not _base_assignable(abase, tbase):
        return False
    # Where the parent's handle is bounded, a child claiming no bound, or a larger
    # one, would be claiming authority the parent does not have.
    return all(kind in tbud and tbud[kind] <= limit for kind, limit in abud.items())


# ── Metering ────────────────────────────────────────────────────────


@dataclass
class Meter:
    """A set of budgets, beneath an optional parent. Charges are all-or-nothing
    across the chain."""

    name: str
    limits: dict[str, int] = field(default_factory=dict)
    parent: Meter | None = None
    spent: dict[str, int] = field(default_factory=dict)

    def chain(self) -> list[Meter]:
        m: Meter | None = self
        out = []
        while m is not None:
            out.append(m)
            m = m.parent
        return out

    def bounded(self, kind: str) -> bool:
        return any(kind in m.limits for m in self.chain())

    def check(self, kind: str, amount: int = 1) -> None:
        for m in self.chain():
            limit = m.limits.get(kind)
            if limit is not None and m.spent.get(kind, 0) + amount > limit:
                raise BudgetExhausted(kind, limit, m.spent.get(kind, 0), m.name)

    def charge(self, kind: str, amount: int = 1) -> None:
        """Charge before the act: refused, and nothing recorded, if any meter in
        the chain would go over."""
        self.check(kind, amount)
        for m in self.chain():
            m.spent[kind] = m.spent.get(kind, 0) + amount

    def record(self, kind: str, amount: int) -> int:
        """Charge after the act, for a quantity known only afterwards (tokens). It
        cannot be refused, since it has happened; it is recorded, and the next
        `check` refuses. Returns the largest overrun this caused in the chain."""
        over = 0
        for m in self.chain():
            m.spent[kind] = m.spent.get(kind, 0) + amount
            limit = m.limits.get(kind)
            if limit is not None:
                over = max(over, m.spent[kind] - limit)
        return over

    def exhausted(self, kind: str) -> bool:
        return any(
            kind in m.limits and m.spent.get(kind, 0) >= m.limits[kind] for m in self.chain()
        )

    def child(self, name: str, limits: dict[str, int]) -> Meter:
        return Meter(name, dict(limits), self)


def route(parent: Meter, provided: str, expected: str, name: str) -> Meter:
    """The routing point: `expected` must narrow `provided`, and the child gets a
    meter beneath the parent's carrying the child's declared budgets."""
    if not is_assignable(provided, expected):
        raise BudgetError(f"{provided!r} → {expected!r} is not a narrowing")
    return parent.child(name, split(expected)[1])


# ── A metered backend ───────────────────────────────────────────────


class MeteredBackend:
    """An LLM backend under a meter. It wraps the *backend*, not the handle,
    because the confined tier's adapters call `llm.backend.generate` directly
    (`poc/sandbox/nodes.py`); a meter on the handle's methods would not see them.

    `Calls` is charged before each call, so it is exact. `Tokens` can only be
    recorded after a call (no backend here takes a per-call cap), so the bound
    enforced is: no call starts once the budget is spent. A run can therefore
    overrun by at most one call's output, and `overruns` records by how much."""

    def __init__(self, backend: Any, meter: Meter):
        if meter.bounded("Tokens") and not hasattr(backend, "usage"):
            raise BudgetError(
                f"{type(backend).__name__} reports no token usage, so a Tokens budget "
                f"over it could not be enforced"
            )
        self.backend = backend
        self.meter = meter
        self.overruns: list[int] = []

    def generate(self, request: LLMRequest) -> LLMResponse:
        if self.meter.exhausted("Tokens"):
            m = next(m for m in self.meter.chain() if "Tokens" in m.limits and
                     m.spent.get("Tokens", 0) >= m.limits["Tokens"])  # fmt: skip
            raise BudgetExhausted("Tokens", m.limits["Tokens"], m.spent["Tokens"], m.name)
        self.meter.charge("Calls")
        before = len(getattr(self.backend, "usage", []))
        response = self.backend.generate(request)
        usage = getattr(self.backend, "usage", [])
        tokens = sum(int(u.get("output_tokens") or 0) for u in usage[before:])
        over = self.meter.record("Tokens", tokens)
        if over > 0:
            self.overruns.append(over)
        return response

    # A handle that forwards `.calls` and `.usage` keeps reports working.
    @property
    def calls(self) -> list:
        return getattr(self.backend, "calls", [])


class UsageStub:
    """`StubLLM` that also reports usage the way `ClaudeCLIBackend` does (one
    record per call with `output_tokens`), so a Tokens budget can be tested
    without a model. Tokens are the words of the reply."""

    def __init__(self, inner: Any = None, reply_words: int | None = None):
        from poc.llm import StubLLM

        self.inner = inner or StubLLM()
        self.reply_words = reply_words
        self.usage: list[dict] = []

    @property
    def calls(self) -> list:
        return self.inner.calls

    def generate(self, request: LLMRequest) -> LLMResponse:
        r = self.inner.generate(request)
        if self.reply_words is not None:
            r = LLMResponse(text=" ".join(["word"] * self.reply_words), tool_calls=r.tool_calls)
        self.usage.append({"output_tokens": len(r.text.split())})
        return r
