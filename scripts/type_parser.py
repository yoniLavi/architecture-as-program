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
from dataclasses import dataclass
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
    items: tuple["Type", ...]


@dataclass(frozen=True)
class TApp:
    head: str
    args: tuple["Type", ...]


@dataclass(frozen=True)
class TVariant:
    role: str | None
    inner: "Type"


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
            raise ParseError(
                f"Unterminated string literal at position {m.start()} in {src!r}"
            )
        if kind == "ERROR":
            raise ParseError(
                f"Unexpected character {value!r} at position {m.start()} in {src!r}"
            )
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
        return TSum(tuple(variants))

    def _parse_variant(self) -> TVariant:
        if (
            self._peek()[0] == "IDENT"
            and self._peek(1)[0] == "COLON"
        ):
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
        raise ParseError(
            f"Unexpected token {tok[0]} ({tok[1]!r}) at {tok[2]} in {self.src!r}"
        )


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
        raise ParseError(
            f"Unexpected trailing token {trailing[1]!r} at {trailing[2]} in {src!r}"
        )
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
    return False
