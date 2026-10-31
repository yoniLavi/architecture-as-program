"""Minimal type-expression parser for signal-graph type annotations.

This is the surface-level type syntax the proposal's canonical graph
JSONs use (examples like `Untrusted<RawMessage>`,
`DBHandle<'knowledge-base', read>`, `LLMClient<[respond, lookup]>`,
`ok: ModeratedQuery | violation: PolicyViolation`). The parser produces
a small AST used by the graph validator to check edge type-compatibility
and trust propagation.

Grammar (informal):

    type        := variant ('|' variant)*
    variant     := (IDENT ':')? application
    application := atom ('<' type (',' type)* '>')?
    atom        := IDENT | STRING | list
    list        := '[' (type (',' type)*)? ']'
    STRING      := "'" [^']* "'"
    IDENT       := [A-Za-z_] [A-Za-z0-9_-]*

Hyphens inside identifiers are allowed so tokens like `read-write`
parse as a single name, matching the usage in the graph JSONs.

The parser is stdlib-only so it can be consumed by the pre-commit
validator without external dependencies.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from enum import IntEnum
from typing import Union

# ── AST ────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class TName:
    name: str


@dataclass(frozen=True)
class TString:
    value: str


@dataclass(frozen=True)
class TList:
    items: tuple[Type, ...]


@dataclass(frozen=True)
class TApp:
    head: str
    args: tuple[Type, ...]


@dataclass(frozen=True)
class TVariant:
    role: str | None
    inner: Type


@dataclass(frozen=True)
class TSum:
    variants: tuple[TVariant, ...]


Type = Union[TName, TString, TList, TApp, TVariant, TSum]


# ── Lexer ──────────────────────────────────────────────────────────


class ParseError(Exception):
    pass


_TOKEN_RE = re.compile(
    r"""
    (?P<WS>\s+)                                 |
    (?P<LT>\<)                                  |
    (?P<GT>\>)                                  |
    (?P<LBRACKET>\[)                            |
    (?P<RBRACKET>\])                            |
    (?P<COMMA>,)                                |
    (?P<COLON>:)                                |
    (?P<PIPE>\|)                                |
    (?P<STRING>'[^']*')                         |
    (?P<IDENT>[A-Za-z_][A-Za-z0-9_-]*)          |
    (?P<UNCLOSED>'[^']*$)                       |
    (?P<ERROR>.)
    """,
    re.VERBOSE,
)


def _tokenize(src: str) -> list[tuple[str, str, int]]:
    tokens: list[tuple[str, str, int]] = []
    for m in _TOKEN_RE.finditer(src):
        kind = m.lastgroup
        if kind is None or kind == "WS":
            continue
        value = m.group(kind)
        if kind == "UNCLOSED":
            raise ParseError(f"Unterminated string literal at position {m.start()} in {src!r}")
        if kind == "ERROR":
            raise ParseError(f"Unexpected character {value!r} at position {m.start()} in {src!r}")
        tokens.append((kind, value, m.start()))
    tokens.append(("EOF", "", len(src)))
    return tokens


# ── Parser ─────────────────────────────────────────────────────────


class _Parser:
    def __init__(self, tokens: list[tuple[str, str, int]], src: str):
        self.tokens = tokens
        self.src = src
        self.i = 0

    def _peek(self, offset: int = 0) -> tuple[str, str, int]:
        return self.tokens[self.i + offset]

    def _consume(self, expected: str | None = None) -> tuple[str, str, int]:
        tok = self.tokens[self.i]
        if expected and tok[0] != expected:
            raise ParseError(
                f"Expected {expected}, got {tok[0]} ({tok[1]!r}) at {tok[2]} in {self.src!r}"
            )
        self.i += 1
        return tok

    def parse_type(self) -> Type:
        first = self._parse_variant()
        if self._peek()[0] != "PIPE":
            # Single term: if unlabelled, return the inner type; otherwise
            # it is a degenerate sum with one variant.
            if first.role is None:
                return first.inner
            return TSum((first,))
        variants = [first]
        while self._peek()[0] == "PIPE":
            self._consume("PIPE")
            variants.append(self._parse_variant())
        # A role names a port, and a port must name one variant: a repeated role
        # lets every variant sharing it leave on that port while the edge check,
        # resolving the role, sees only the first — an adversarial review routed
        # raw untrusted input to the tool-capable node through the second.
        roles = [v.role for v in variants if v.role]
        duplicated = sorted({r for r in roles if roles.count(r) > 1})
        if duplicated:
            raise ParseError(
                f"duplicate variant role(s) {duplicated} in {self.src!r}; "
                f"a port must name one variant"
            )
        # A sum is labelled throughout or not at all. An unlabelled variant in a
        # labelled sum has no port to leave on, and the unported edge that could
        # carry it is refused, so variant completeness never saw it and the runtime
        # dropped it — adversarial review swallowed a policy violation this way.
        unlabelled = [v for v in variants if not v.role]
        if roles and unlabelled:
            raise ParseError(
                f"sum mixes labelled and unlabelled variants in {self.src!r}; "
                f"a variant without a role has no port to leave on"
            )
        return TSum(tuple(variants))

    def _parse_variant(self) -> TVariant:
        if self._peek()[0] == "IDENT" and self._peek(1)[0] == "COLON":
            role = self._consume("IDENT")[1]
            self._consume("COLON")
            inner = self._parse_application()
            return TVariant(role, inner)
        return TVariant(None, self._parse_application())

    def _parse_application(self) -> Type:
        atom = self._parse_atom()
        if self._peek()[0] != "LT":
            return atom
        if not isinstance(atom, TName):
            raise ParseError(
                f"Only named types can take generic arguments, got {atom!r} in {self.src!r}"
            )
        self._consume("LT")
        args: list[Type] = [self.parse_type()]
        while self._peek()[0] == "COMMA":
            self._consume("COMMA")
            args.append(self.parse_type())
        self._consume("GT")
        return TApp(atom.name, tuple(args))

    def _parse_atom(self) -> Type:
        tok = self._peek()
        if tok[0] == "STRING":
            self._consume("STRING")
            return TString(tok[1][1:-1])  # strip surrounding quotes
        if tok[0] == "LBRACKET":
            self._consume("LBRACKET")
            items: list[Type] = []
            if self._peek()[0] != "RBRACKET":
                items.append(self.parse_type())
                while self._peek()[0] == "COMMA":
                    self._consume("COMMA")
                    items.append(self.parse_type())
            self._consume("RBRACKET")
            return TList(tuple(items))
        if tok[0] == "IDENT":
            self._consume("IDENT")
            return TName(tok[1])
        raise ParseError(f"Unexpected token {tok[0]} ({tok[1]!r}) at {tok[2]} in {self.src!r}")


def parse_type(src: str) -> Type:
    """Parse a type expression, returning the AST. Raises ParseError
    if the expression is not well-formed."""
    if not src or not src.strip():
        raise ParseError("Empty type expression")
    tokens = _tokenize(src)
    parser = _Parser(tokens, src)
    result = parser.parse_type()
    if parser._peek()[0] != "EOF":
        trailing = parser._peek()
        raise ParseError(f"Unexpected trailing token {trailing[1]!r} at {trailing[2]} in {src!r}")
    return result


# ── AST utilities ──────────────────────────────────────────────────


def is_untrusted(t: Type) -> bool:
    """True if `t` is an `Untrusted<_>` application at the top level."""
    return isinstance(t, TApp) and t.head == "Untrusted"


def contains_untrusted(t: Type) -> bool:
    """True if `t`, or any variant within it if it is a sum, is wrapped
    in `Untrusted<_>` at the top level of that branch."""
    if is_untrusted(t):
        return True
    if isinstance(t, TSum):
        return any(contains_untrusted(v.inner) for v in t.variants)
    return False


# ── Trust lattice ──────────────────────────────────────────────────
#
# A two-point security-label lattice in the Jif lineage
# @myers_decentralized_1997:
#
#       UNTRUSTED  ⊑  TRUSTED
#
# ordered so that TRUSTED is the top. Trust may be *forgotten* freely
# (a trusted value can stand where an untrusted one is wanted) but
# never *manufactured*: `Untrusted<T>` does not inhabit `T`. The one
# sanctioned upward move — raising UNTRUSTED to TRUSTED — is an
# explicit discharge, permitted only at a node declared as a
# discharger (see graph_validator).
#
# The order is deliberately abstract behind `trust_level`,
# `trust_meet`, and `trust_flows_to` so that a later graded lattice
# (e.g. `Untrusted ⊑ Sanitised ⊑ Trusted`) or a full Jif-style
# decentralised-label model can replace the two-point set without
# touching the wiring check. Only these three functions know the
# lattice shape.


class Trust(IntEnum):
    """A trust level. The integer value is the lattice height, so the
    natural `<`/`<=`/`max`/`min` operations coincide with the lattice
    order and meet/join. Do not rely on the specific integers outside
    this module; go through the helpers below."""

    UNTRUSTED = 0
    TRUSTED = 1


def trust_level(t: Type) -> Trust:
    """The trust level of a type. A type wrapped in `Untrusted<_>` at
    the top level — or a sum with any `Untrusted<_>` variant — sits at
    UNTRUSTED; everything else is TRUSTED. This reuses
    `contains_untrusted`, so a partially-untrusted sum is conservatively
    treated as untrusted (the least-trusted variant taints the whole)."""
    return Trust.UNTRUSTED if contains_untrusted(t) else Trust.TRUSTED


# The capability kinds: the type heads that name authority rather than data. Kept
# here, stdlib-only, so the validator can tell a capability from data without
# importing the runtime; `poc/sandbox/interfaces.py` maps the same set onto WIT
# interfaces, and a test holds the two equal.
CAPABILITY_HEADS = frozenset(
    {
        "LLMClient",
        "DBHandle",
        "ResponseChannel",
        "EventEmitter",
        "Clock",
        "HTTPClient",
        "Notifier",
        "StateHandle",
        # The banking kinds (Paper 4's AgentDojo harness). A bank tool's authority
        # is coarser than banking's threats, so each narrows on its arguments.
        "Payments",
        "ScheduledPayments",
        "UserProfile",
        "Credentials",
    }
)

# `Credentials` is a kind no graph may be granted: it exists so that changing the
# password has a capability to name, and a grant of it is a validator rejection.
NEVER_GRANTED = frozenset({"Credentials"})


def contains_capability(t: Type) -> bool:
    """True if a capability type appears anywhere in `t` — at the top, under a
    type constructor, or in any variant. Capabilities are provisioned through
    `with` clauses, never carried as data, so a data position holding one is
    reference passing along an edge: exactly the delegation the graph gives up."""
    if isinstance(t, TName):
        return t.name in CAPABILITY_HEADS
    if isinstance(t, TApp):
        return t.head in CAPABILITY_HEADS or any(contains_capability(a) for a in t.args)
    if isinstance(t, TSum):
        return any(contains_capability(v.inner) for v in t.variants)
    if isinstance(t, TVariant):
        return contains_capability(t.inner)
    if isinstance(t, TList):
        return any(contains_capability(i) for i in t.items)
    return False


def deep_trust_level(t: Type) -> Trust:
    """The trust level of a type counting `Untrusted<_>` *anywhere* inside
    it — under a type constructor such as `List<Untrusted<X>>`, or in any
    variant of a sum — not only at the top. A value that carries untrusted
    content somewhere is untrusted as a whole for the purpose of a node
    body's flow: consuming it and emitting a clean output is laundering."""

    def _contains(u: Type) -> bool:
        if is_untrusted(u):
            return True
        if isinstance(u, TApp):
            return any(_contains(a) for a in u.args)
        if isinstance(u, TSum):
            return any(_contains(v.inner) for v in u.variants)
        if isinstance(u, TVariant):
            return _contains(u.inner)
        if isinstance(u, TList):
            return any(_contains(i) for i in u.items)
        return False

    return Trust.UNTRUSTED if _contains(t) else Trust.TRUSTED


def output_variant_levels(t: Type) -> list[Trust]:
    """The deep trust level of each thing a node may emit: one level per
    variant of a sum, or the single level of any other type. A node emits
    one variant at a time, and each variant leaves on its own port, so each
    must satisfy the lattice on its own — a sum with one `Untrusted<_>`
    variant does not license its other variants to leave trusted."""
    if isinstance(t, TSum):
        return [deep_trust_level(v.inner) for v in t.variants]
    return [deep_trust_level(t)]


def trust_meet(levels: Iterable[Trust]) -> Trust:
    """The lattice meet (greatest lower bound) of some levels — the
    *least* trusted among them, TRUSTED for the empty set (the meet
    over nothing is the lattice top). This is the effective trust a
    node's body may claim to have received: if any input is untrusted,
    the combined input is untrusted."""
    result = Trust.TRUSTED
    for lvl in levels:
        if lvl < result:
            result = lvl
    return result


def trust_flows_to(provided: Trust, required: Trust) -> bool:
    """True if a value at trust level `provided` may satisfy a position
    that requires level `required`, with **no upward coercion**: trust
    can be forgotten but never manufactured. Equivalent to
    `required ⊑ provided` — the requirement must not exceed what is
    supplied. This single predicate governs both edges (source output →
    target input) and node bodies (input meet → output); trust
    laundering is exactly its violation without a declared discharge."""
    return required <= provided


def strip_trust(t: Type) -> Type:
    """Remove a top-level `Untrusted<_>` wrapper, exposing the carried
    data shape; other types are returned unchanged. Used to separate a
    type's *data compatibility* (which must match by shape) from its
    *trust level* (which is compared under the lattice), so that the
    two obligations are checked independently rather than smeared into
    one equality test."""
    if is_untrusted(t):
        assert isinstance(t, TApp)  # narrowed by is_untrusted
        # `Untrusted<T>` carries exactly one argument; be defensive if
        # a malformed `Untrusted<A, B>` slips through and just return
        # the whole node so the shape comparison stays conservative.
        if len(t.args) == 1:
            return t.args[0]
    return t


def sum_variant_type(t: Type, role: str) -> Type | None:
    """Return the type associated with `role` in a sum type, or None
    if `t` is not a sum or does not contain that role."""
    if isinstance(t, TSum):
        for v in t.variants:
            if v.role == role:
                return v.inner
    return None


def sum_roles(t: Type) -> list[str]:
    """Return the list of role names in a sum type, or an empty list."""
    if isinstance(t, TSum):
        return [v.role for v in t.variants if v.role]
    return []


def unparse(t: Type) -> str:
    """Render an AST back to its concrete surface syntax. Inverse of
    `parse_type` on well-formed inputs."""
    if isinstance(t, TName):
        return t.name
    if isinstance(t, TString):
        return f"'{t.value}'"
    if isinstance(t, TList):
        return "[" + ", ".join(unparse(x) for x in t.items) + "]"
    if isinstance(t, TApp):
        return f"{t.head}<{', '.join(unparse(x) for x in t.args)}>"
    if isinstance(t, TVariant):
        prefix = f"{t.role}: " if t.role else ""
        return prefix + unparse(t.inner)
    if isinstance(t, TSum):
        return " | ".join(unparse(v) for v in t.variants)
    # Exhaustive over the Type union; this branch is unreachable at
    # runtime and exists only as a defensive default.
    return repr(t)


# ── Capability subtyping ───────────────────────────────────────────
#
# A narrow slice of structural subtyping, intentionally applied only
# at cross-graph composition boundaries (the PoC validator uses
# strict equality everywhere else). The rules capture the
# principle-of-least-authority intuition that a parent may provide
# a handle with at least the authority the sub-graph declares.


def _llm_tool_set(app: TApp) -> frozenset[str] | None:
    """Normalise an `LLMClient<...>` argument to the set of tools
    it grants. `LLMClient<inference>` is treated as the empty set.
    Returns None if the shape is not a recognised LLMClient form."""
    if len(app.args) != 1:
        return None
    arg = app.args[0]
    if isinstance(arg, TName) and arg.name == "inference":
        return frozenset()
    if isinstance(arg, TList):
        names: set[str] = set()
        for item in arg.items:
            if not isinstance(item, TName):
                return None
            names.add(item.name)
        return frozenset(names)
    return None


# DBHandle mode lattice (read-write is top; read and append are
# incomparable middle elements).
_DB_MODE_COVERS: dict[str, frozenset[str]] = {
    "read-write": frozenset({"read-write", "read", "append"}),
    "read": frozenset({"read"}),
    "append": frozenset({"append"}),
}


# StateHandle modes: a chain, `read-write` over `read`. There is no `append`:
# a store a node may add to but not read back is a log, which `DBHandle` models.
_STATE_MODE_COVERS: dict[str, frozenset[str]] = {
    "read-write": frozenset({"read-write", "read"}),
    "read": frozenset({"read"}),
}


def _http_allowlist(app: TApp) -> frozenset[str] | None:
    """Normalise an `HTTPClient<[...]>` argument to its permitted host set.
    The scope must be a non-empty list of string-literal hosts; returns None
    for any other shape. The first capability scope that is a *set* rather
    than a mode or a name, which is why its narrowing rule below is plain
    set inclusion."""
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


# ── The banking kinds' scopes ──────────────────────────────────────
#
# Each scope is parsed once, here, so the validator's narrowing rule, the
# host-side handle's check at the crossing, and the WIT mapping all read the same
# thing. A shape none of them can read is None, and is refused by all three.

# Payee sets read from the environment rather than written in the type. `any` is
# the unnarrowed form, there so that a payee known only from a document (a bill)
# is expressible at all; a reviewer should treat it as the widest grant it is.
DYNAMIC_PAYEES = frozenset({"any", "inbound-senders"})
SCHEDULED_FIELDS = frozenset({"recipient", "amount", "subject", "date", "recurring"})
PROFILE_FIELDS = frozenset({"first_name", "last_name", "street", "city"})


@dataclass(frozen=True)
class PaymentsScope:
    """`Payments<[payees], cap>`, or `Payments<[payees], cap, recurring>`.

    `literal` holds payees named in the type (an IBAN, or a name such as
    'Spotify'); `dynamic` holds the environment-read sets of `DYNAMIC_PAYEES`.
    `cap` is the most one payment may move, None for `uncapped`. `recurring`
    selects the other mode: scheduling a standing order rather than sending once.
    The two modes are incomparable, as `DBHandle`'s `read` and `append` are."""

    literal: frozenset[str]
    dynamic: frozenset[str]
    cap: Decimal | None
    recurring: bool

    def covers(self, other: PaymentsScope) -> bool:
        """True if this scope grants everything `other` does."""
        if self.recurring != other.recurring:
            return False
        if self.cap is not None and (other.cap is None or other.cap > self.cap):
            return False
        if "any" in self.dynamic:
            return True
        return other.dynamic <= self.dynamic and other.literal <= self.literal


@dataclass(frozen=True)
class ScheduledScope:
    """`ScheduledPayments<[orders], [fields]>`: which standing orders, by subject
    (compared case-insensitively), and which of their fields, may change."""

    orders: frozenset[str]
    fields: frozenset[str]

    def covers(self, other: ScheduledScope) -> bool:
        return other.orders <= self.orders and other.fields <= self.fields


def _string_set(arg: Type) -> frozenset[str] | None:
    if not isinstance(arg, TList) or not arg.items:
        return None
    if not all(isinstance(i, TString) for i in arg.items):
        return None
    return frozenset(i.value for i in arg.items)  # type: ignore[union-attr]


def _name_set(arg: Type, allowed: frozenset[str]) -> frozenset[str] | None:
    if not isinstance(arg, TList) or not arg.items:
        return None
    names = [i.name for i in arg.items if isinstance(i, TName)]
    if len(names) != len(arg.items) or not set(names) <= allowed:
        return None
    return frozenset(names)


def payments_scope(t: Type) -> PaymentsScope | None:
    """The scope of a `Payments<...>` type, or None if the shape is not one."""
    if not isinstance(t, TApp) or t.head != "Payments" or len(t.args) not in (2, 3):
        return None
    payees, cap_arg = t.args[0], t.args[1]
    if not isinstance(payees, TList) or not payees.items:
        return None
    literal: set[str] = set()
    dynamic: set[str] = set()
    for item in payees.items:
        # A quoted dynamic-set name ('any') would be a literal payee of that name,
        # able to pay almost no one while reading as the widest grant. Refused, so
        # the spelling can only mean the set (found by Paper 4's registered run).
        if isinstance(item, TString) and item.value in DYNAMIC_PAYEES:
            return None
        if isinstance(item, TString) and item.value:
            literal.add(item.value)
        elif isinstance(item, TName) and item.name in DYNAMIC_PAYEES:
            dynamic.add(item.name)
        else:
            return None
    if isinstance(cap_arg, TName) and cap_arg.name == "uncapped":
        cap = None
    elif isinstance(cap_arg, TString):
        try:
            cap = Decimal(cap_arg.value)
        except InvalidOperation:
            return None
        if not cap.is_finite() or cap <= 0:
            return None
    else:
        return None
    recurring = False
    if len(t.args) == 3:
        mode = t.args[2]
        if not (isinstance(mode, TName) and mode.name == "recurring"):
            return None
        recurring = True
    return PaymentsScope(frozenset(literal), frozenset(dynamic), cap, recurring)


def scheduled_scope(t: Type) -> ScheduledScope | None:
    """The scope of a `ScheduledPayments<[orders], [fields]>` type, or None."""
    if not isinstance(t, TApp) or t.head != "ScheduledPayments" or len(t.args) != 2:
        return None
    orders = _string_set(t.args[0])
    fields = _name_set(t.args[1], SCHEDULED_FIELDS)
    if orders is None or fields is None:
        return None
    return ScheduledScope(frozenset(o.lower() for o in orders), fields)


def profile_fields(t: Type) -> frozenset[str] | None:
    """The fields a `UserProfile<[fields]>` type may change, or None."""
    if not isinstance(t, TApp) or t.head != "UserProfile" or len(t.args) != 1:
        return None
    return _name_set(t.args[0], PROFILE_FIELDS)


def is_assignable(actual: Type, target: Type) -> bool:
    """True if a value of type `actual` can stand in where `target`
    is expected, under the PoC's capability-narrowing rules.

    Equality implies assignability (reflexivity). Beyond that:
    * `LLMClient<[tools]>`: actual must carry a *superset* of the
      tools the target requires. `LLMClient<inference>` is the
      empty-tool-set form.
    * `DBHandle<scope, mode>`: scopes must match exactly; the
      actual mode must cover the target mode under the lattice
      `read-write ⊇ {read, append}`.
    * `StateHandle<'name', mode>`: store names must match exactly;
      `read-write` covers `read`.
    * Trust markers are not handled here — `Untrusted<T>` is never
      assignable to `T` (trust discharge is enforced separately).
    * All other types: strict equality only."""
    if actual == target:
        return True
    if not isinstance(actual, TApp) or not isinstance(target, TApp):
        return False
    if actual.head != target.head:
        return False
    if actual.head == "LLMClient":
        atools = _llm_tool_set(actual)
        ttools = _llm_tool_set(target)
        if atools is None or ttools is None:
            return False
        return ttools.issubset(atools)
    if actual.head == "HTTPClient":
        # A parent may route a handle whose allowlist is a superset of what the
        # sub-graph declares, never a subset: composition must not grant a child
        # reach the parent's own handle does not have.
        ahosts = _http_allowlist(actual)
        thosts = _http_allowlist(target)
        if ahosts is None or thosts is None:
            return False
        return thosts.issubset(ahosts)
    if actual.head == "DBHandle":
        if len(actual.args) != 2 or len(target.args) != 2:
            return False
        if actual.args[0] != target.args[0]:
            return False
        amode = actual.args[1]
        tmode = target.args[1]
        if not isinstance(amode, TName) or not isinstance(tmode, TName):
            return False
        covered = _DB_MODE_COVERS.get(amode.name)
        if covered is None:
            return amode.name == tmode.name
        return tmode.name in covered
    if actual.head == "StateHandle":
        # Node-local state narrows as a `DBHandle` does, over a two-mode order:
        # the store names must match exactly, and `read-write` may stand in where
        # `read` is declared, never the reverse.
        if len(actual.args) != 2 or len(target.args) != 2:
            return False
        if actual.args[0] != target.args[0]:
            return False
        amode = actual.args[1]
        tmode = target.args[1]
        if not isinstance(amode, TName) or not isinstance(tmode, TName):
            return False
        return tmode.name in _STATE_MODE_COVERS.get(amode.name, frozenset())
    if actual.head == "Payments":
        # Set inclusion on payees and cap ≤ cap, as for an HTTP allowlist: a parent
        # may route a wider handle, never a narrower one. Checked, not enforced: the
        # child receives the parent's handle whole (Paper 2 §7.6).
        ascope, tscope = payments_scope(actual), payments_scope(target)
        return ascope is not None and tscope is not None and ascope.covers(tscope)
    if actual.head == "ScheduledPayments":
        asched, tsched = scheduled_scope(actual), scheduled_scope(target)
        return asched is not None and tsched is not None and asched.covers(tsched)
    if actual.head == "UserProfile":
        afields, tfields = profile_fields(actual), profile_fields(target)
        return afields is not None and tfields is not None and tfields <= afields
    return False
