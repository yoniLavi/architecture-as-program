"""A deliberately small contract language for node signatures.

Behavioural contracts are what the model needs to make a generated node body
*checkable* rather than merely runnable: without them, "this implementation
satisfies its specification" reduces to "its tests passed", which is a weaker and
differently-shaped claim. This module is the minimum that closes that gap.

The size is the design. Three shipped systems set the weight class:

* **Racket's contracts** contribute *blame* — the load-bearing idea. A failed
  precondition is not the same kind of event as a failed postcondition: the first
  says the caller supplied something it should not have, the second says the
  implementation is wrong. Reporting which is which is most of the value, because
  it points at the thing to fix.
* **Clojure's `spec/fdef`** contributes the shape: predicates attached to a
  signature, usable both as a runtime guard and as a generator for test inputs.
* **`icontract-hypothesis`** contributes the reason to keep the vocabulary closed:
  a precondition drawn from a small, enumerable language can be *derived into* a
  property-based-test strategy, so one contract is written once and used twice.
  (That derivation is not built here — see the roadmap — but the vocabulary is
  chosen so that it stays possible.)

What is deliberately absent: quantifiers, recursion, arithmetic beyond `len`, and
any escape to Python. That ceiling is what makes this a *contract* rather than a
refinement type. It cannot express "the output length is a function of the input
length", and it is not supposed to; a language that could would need a solver, and
the project's stated bar is modest tooling. The cost is real and is stated in the
paper rather than hidden here.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Blame: which side a violation indicts. A contract that says only "something is
# wrong" is much less useful than one that says which of the two parties to a
# node's boundary broke the agreement.
BLAME_CALLER = "caller"  # a precondition failed: the wiring supplied a bad input
BLAME_IMPLEMENTATION = "implementation"  # a postcondition failed: the body is wrong


class ContractError(ValueError):
    """A contract could not be parsed, or refers to a field that does not resolve.

    Raised at validation or assembly time — never mid-run — because an
    unevaluatable contract is a mistake in the graph, not a property of the data."""


@dataclass(frozen=True)
class ContractViolation(Exception):
    """A contract that evaluated cleanly and came out false.

    Carries the blame so a reader is told which side broke the agreement, not
    merely that it broke."""

    node: str
    kind: str  # "requires" | "ensures"
    predicate: str
    blame: str

    def __str__(self) -> str:
        subject = "input" if self.kind == "requires" else "output"
        return (
            f"node {self.node!r} violated its {self.kind} contract on the {subject}: "
            f"{self.predicate!r} (blame: {self.blame})"
        )


_COMPARATORS = {
    "==": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
    ">=": lambda a, b: a >= b,
    "<=": lambda a, b: a <= b,
    ">": lambda a, b: a > b,
    "<": lambda a, b: a < b,
}

_PATH = r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*"
_OPS = "|".join(re.escape(op) for op in sorted(_COMPARATORS, key=len, reverse=True))

# The whole grammar, as four closed forms. Keeping it expressible as four regexes
# is not laziness — it is the enforcement mechanism for the vocabulary ceiling
# above. A fifth form is a deliberate decision, not an incremental edit.
_RE_LEN = re.compile(rf"^len\(\s*({_PATH})\s*\)\s*({_OPS})\s*(-?\d+)$")
_RE_IN = re.compile(rf"^({_PATH})\s+in\s+\[(.*)\]$")
_RE_PRESENT = re.compile(rf"^present\(\s*({_PATH})\s*\)$")
_RE_CMP = re.compile(rf"^({_PATH})\s*({_OPS})\s*(.+)$")

_MISSING = object()


def _literal(text: str) -> object:
    """A literal in the closed vocabulary: quoted string, integer, or boolean."""
    text = text.strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in "'\"":
        return text[1:-1]
    if text in ("true", "false"):
        return text == "true"
    try:
        return int(text)
    except ValueError as exc:
        raise ContractError(
            f"not a literal in the contract vocabulary: {text!r} "
            f"(expected a quoted string, an integer, or true/false)"
        ) from exc


def _resolve(value: object, path: str) -> object:
    """Follow a dotted field path, returning a sentinel rather than raising when it
    does not resolve — `present(...)` needs to distinguish absent from falsy."""
    current = value
    for part in path.split("."):
        if isinstance(current, dict):
            if part not in current:
                return _MISSING
            current = current[part]
        else:
            if not hasattr(current, part):
                return _MISSING
            current = getattr(current, part)
    return current


@dataclass(frozen=True)
class Predicate:
    """One parsed predicate, retaining its source text so a violation can quote the
    contract as the author wrote it rather than a reconstruction."""

    source: str
    paths: tuple[str, ...]
    _eval: object  # callable(value) -> bool; typed loosely to keep the dataclass frozen

    def holds(self, value: object) -> bool:
        return bool(self._eval(value))  # type: ignore[operator]


def parse(source: str) -> Predicate:
    """Parse one predicate, or raise `ContractError`.

    Order matters: `len(x) > 0` must be tried before the bare comparison form, or
    the path matcher would swallow `len`."""
    text = source.strip()
    if not text:
        raise ContractError("empty predicate")

    if m := _RE_LEN.match(text):
        path, op, rhs = m.group(1), m.group(2), int(m.group(3))
        cmp = _COMPARATORS[op]

        def check_len(value: object, path=path, cmp=cmp, rhs=rhs) -> bool:
            target = _resolve(value, path)
            if target is _MISSING or not hasattr(target, "__len__"):
                return False
            return cmp(len(target), rhs)  # type: ignore[arg-type]

        return Predicate(text, (path,), check_len)

    if m := _RE_IN.match(text):
        path, items = m.group(1), m.group(2)
        allowed = tuple(_literal(part) for part in items.split(",") if part.strip())

        def check_in(value: object, path=path, allowed=allowed) -> bool:
            return _resolve(value, path) in allowed

        return Predicate(text, (path,), check_in)

    if m := _RE_PRESENT.match(text):
        path = m.group(1)

        def check_present(value: object, path=path) -> bool:
            return _resolve(value, path) is not _MISSING

        return Predicate(text, (path,), check_present)

    if m := _RE_CMP.match(text):
        path, op, rhs_text = m.group(1), m.group(2), m.group(3)
        cmp, rhs = _COMPARATORS[op], _literal(rhs_text)

        def check_cmp(value: object, path=path, cmp=cmp, rhs=rhs) -> bool:
            target = _resolve(value, path)
            if target is _MISSING:
                return False
            try:
                return cmp(target, rhs)
            except TypeError:
                return False

        return Predicate(text, (path,), check_cmp)

    raise ContractError(
        f"predicate outside the contract vocabulary: {source!r}. "
        f"Permitted forms: `path <op> literal`, `path in [a, b]`, `present(path)`, "
        f"`len(path) <op> integer`"
    )


def parse_all(sources: object, *, what: str) -> tuple[Predicate, ...]:
    """Parse a node's `requires` or `ensures` list."""
    if sources is None:
        return ()
    if not isinstance(sources, list) or not all(isinstance(s, str) for s in sources):
        raise ContractError(f"`{what}` must be a list of predicate strings")
    return tuple(parse(s) for s in sources)


def check(predicates: tuple[Predicate, ...], value: object, *, node: str, kind: str) -> None:
    """Evaluate a node's contract, raising on the first violation.

    Blame follows the kind: a `requires` failure indicts whatever supplied the
    input, an `ensures` failure indicts the node body."""
    blame = BLAME_CALLER if kind == "requires" else BLAME_IMPLEMENTATION
    for predicate in predicates:
        if not predicate.holds(value):
            raise ContractViolation(node=node, kind=kind, predicate=predicate.source, blame=blame)


def unresolvable_paths(predicates: tuple[Predicate, ...], sample: object) -> list[str]:
    """Paths that do not resolve against a representative value.

    Used at assembly, where the value classes are in hand, to reject a contract
    that could never be evaluated — the graph validator cannot do this, having no
    field schema for a declared type name."""
    missing = []
    for predicate in predicates:
        for path in predicate.paths:
            if _resolve(sample, path) is _MISSING:
                missing.append(path)
    return missing
