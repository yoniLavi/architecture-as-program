"""S2: does a producer's `ensures` imply its consumer's `requires`? Stdlib-only.

The contract vocabulary (`poc/contracts.py`) has four atom forms, each over one
dotted path and one literal: `len(p) op n`, `p op lit`, `p in [..]`, `present(p)`.
No atom relates two paths, and there are no quantifiers and no arithmetic. So
implication between a conjunction of atoms (the producer's `ensures`) and one atom
(a conjunct of the consumer's `requires`) splits by path, and each path is a small
problem over one value:

* **lengths** — an integer interval `[lo, hi]` (lengths are ≥ 0) minus a finite set
  of excluded points;
* **values** — either a finite candidate set (from `==` or `in`), filtered by every
  other atom on the path, or, for numbers, a real interval minus excluded points.

**Semantics are the evaluator's, not a logic's.** Every atom is false when its path
does not resolve (`check_len`, `check_in`, `check_cmp` all return False on a
missing path), so any atom on `p.q` implies `present(p.q)` and `present(p)`. A
comparison between incomparable types is false, not an error. Python's `True == 1`
holds in the evaluator, so it holds here too.

**Numbers are reasoned over the reals.** The vocabulary does not know whether a
field is an int or a float, so `x > 0` does not imply `x >= 1` here. That is sound
(anything implied over the reals is implied over the integers) and incomplete; a
verdict that might differ over the integers is flagged.

Verdicts, per (edge, requires atom):
* `discharged` — every value satisfying the producer's `ensures` satisfies it;
* `contradicted` — no value satisfying the producer's `ensures` satisfies it: the
  wiring fails on every run in which the producer keeps its contract;
* `not-implied` — some values do, some do not: the run-time check stays;
* `no-guarantee` — the producer's `ensures` says nothing about the atom's path;
* `vacuous` — the producer's own `ensures` is unsatisfiable on the path, so its body
  can never keep it (a bug in the producer's contract, reported, not discharged);
* `undecided` — a case this procedure does not handle (reported, never guessed).
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field

from poc.contracts import _OPS, _PATH, _literal

_RE_LEN = re.compile(rf"^len\(\s*({_PATH})\s*\)\s*({_OPS})\s*(-?\d+)$")
_RE_IN = re.compile(rf"^({_PATH})\s+in\s+\[(.*)\]$")
_RE_PRESENT = re.compile(rf"^present\(\s*({_PATH})\s*\)$")
_RE_CMP = re.compile(rf"^({_PATH})\s*({_OPS})\s*(.+)$")


@dataclass(frozen=True)
class Atom:
    kind: str  # "len" | "cmp" | "in" | "present"
    path: str
    op: str = ""
    value: object = None  # literal, or tuple of literals for "in"
    source: str = ""


def atom(source: str) -> Atom:
    """Parse one predicate, in the same order and with the same regexes as
    `poc.contracts.parse` (which keeps its atoms opaque)."""
    text = source.strip()
    if m := _RE_LEN.match(text):
        return Atom("len", m.group(1), m.group(2), int(m.group(3)), text)
    if m := _RE_IN.match(text):
        items = tuple(_literal(p) for p in m.group(2).split(",") if p.strip())
        return Atom("in", m.group(1), "in", items, text)
    if m := _RE_PRESENT.match(text):
        return Atom("present", m.group(1), source=text)
    if m := _RE_CMP.match(text):
        return Atom("cmp", m.group(1), m.group(2), _literal(m.group(3)), text)
    raise ValueError(f"outside the contract vocabulary: {source!r}")


def rebase(a: Atom, prefix: str) -> Atom | None:
    """`a` with `prefix.` stripped from its path, or None if it is not under it
    (a join's `requires` reads `in1.date`; the edge into position 1 carries `date`)."""
    if a.path.startswith(prefix + "."):
        return Atom(a.kind, a.path[len(prefix) + 1 :], a.op, a.value, a.source)
    return None


# ── One path's feasible set ─────────────────────────────────────────


def _num(v: object) -> bool:
    return isinstance(v, int | float) and not (isinstance(v, float) and math.isnan(v))


@dataclass
class Interval:
    """A set of reals: [lo, hi] with open/closed ends, minus excluded points."""

    lo: float = -math.inf
    lo_open: bool = True
    hi: float = math.inf
    hi_open: bool = True
    excluded: set = field(default_factory=set)

    def meet(self, op: str, n: float) -> None:
        if op in (">", ">="):
            if n > self.lo or (n == self.lo and op == ">"):
                self.lo, self.lo_open = n, op == ">"
        elif op in ("<", "<="):
            if n < self.hi or (n == self.hi and op == "<"):
                self.hi, self.hi_open = n, op == "<"
        elif op == "==":
            self.meet(">=", n)
            self.meet("<=", n)
        elif op == "!=":
            self.excluded.add(n)

    def empty(self, integers: bool) -> bool:
        lo, hi = self.lo, self.hi
        if integers:
            if math.isfinite(lo):
                lo = lo + 1 if self.lo_open and lo == math.floor(lo) else math.ceil(lo)
            if math.isfinite(hi):
                hi = hi - 1 if self.hi_open and hi == math.ceil(hi) else math.floor(hi)
            if lo > hi:
                return True
            if hi - lo < 64:
                return all(int(x) in self.excluded for x in range(int(lo), int(hi) + 1))
            return False
        if lo > hi or (lo == hi and (self.lo_open or self.hi_open)):
            return True
        return lo == hi and lo in self.excluded

    def copy(self) -> Interval:
        return Interval(self.lo, self.lo_open, self.hi, self.hi_open, set(self.excluded))


_NEGATE = {"<": ">=", "<=": ">", ">": "<=", ">=": "<", "==": "!=", "!=": "=="}


def _holds(op: str, a: object, b: object) -> bool:
    try:
        return {
            "==": lambda: a == b,
            "!=": lambda: a != b,
            "<": lambda: a < b,  # type: ignore[operator]
            "<=": lambda: a <= b,  # type: ignore[operator]
            ">": lambda: a > b,  # type: ignore[operator]
            ">=": lambda: a >= b,  # type: ignore[operator]
        }[op]()
    except TypeError:
        return False


@dataclass
class Verdict:
    verdict: str
    reason: str = ""
    integer_caveat: bool = False


def _len_verdict(given: list[Atom], q: Atom) -> Verdict:
    iv = Interval(lo=0, lo_open=False)
    for a in given:
        iv.meet(a.op, a.value)  # type: ignore[arg-type]
    if iv.empty(integers=True):
        return Verdict("vacuous", "the producer's length constraints are unsatisfiable")
    yes, no = iv.copy(), iv.copy()
    yes.meet(q.op, q.value)  # type: ignore[arg-type]
    no.meet(_NEGATE[q.op], q.value)  # type: ignore[arg-type]
    if no.empty(integers=True):
        return Verdict("discharged")
    if yes.empty(integers=True):
        return Verdict("contradicted")
    return Verdict("not-implied")


def _value_candidates(given: list[Atom]) -> list | None:
    """The finite set of values the producer pins a path to (by `==` or `in`),
    filtered by its other atoms on the path; None if it pins none."""
    cands: list | None = None
    for a in given:
        if a.kind == "cmp" and a.op == "==":
            s = [a.value]
        elif a.kind == "in":
            s = list(a.value)  # type: ignore[arg-type]
        else:
            continue
        cands = s if cands is None else [c for c in cands if any(c == x for x in s)]
    if cands is None:
        return None
    return [c for c in cands if all(_holds(a.op, c, a.value) for a in given if a.kind == "cmp")]


def _value_verdict(given: list[Atom], q: Atom) -> Verdict:
    cands = _value_candidates(given)
    if cands is not None:
        if not cands:
            return Verdict("vacuous", "the producer's value constraints are unsatisfiable")
        sat = [_atom_on(q, c) for c in cands]
        if all(sat):
            return Verdict("discharged")
        if not any(sat):
            return Verdict("contradicted")
        return Verdict("not-implied")
    # Otherwise numbers, over the reals.
    nums = [a for a in given if a.kind == "cmp" and _num(a.value)]
    others = [a for a in given if a.kind == "cmp" and not _num(a.value)]
    if others:
        return Verdict("undecided", "a non-numeric ordering or inequality without a pinned set")
    if not nums:
        return Verdict("no-guarantee")
    # Only an ordering forces the value to be a number: `x != 2` holds of 'a' too
    # (found by the evaluator fuzz, `test_every_verdict_agrees_with_the_evaluator`).
    if not any(a.op in ("<", "<=", ">", ">=") for a in nums):
        excluded = {a.value for a in nums}
        if q.kind == "cmp" and q.op == "!=" and q.value in excluded:
            return Verdict("discharged")
        return Verdict("not-implied")
    iv = Interval()
    for a in nums:
        iv.meet(a.op, a.value)  # type: ignore[arg-type]
    if iv.empty(integers=False):
        return Verdict("vacuous", "the producer's numeric constraints are unsatisfiable")
    if q.kind == "in":
        if not any(_num(v) for v in q.value):  # type: ignore[union-attr]
            return Verdict("contradicted")
        # A real interval is inside a finite set only if it is a single point.
        if iv.lo == iv.hi and not (iv.lo_open or iv.hi_open):
            ok = any(iv.lo == v for v in q.value)  # type: ignore[union-attr]
            return Verdict("discharged" if ok else "contradicted")
        return Verdict("not-implied", integer_caveat=True)
    if not _num(q.value):
        return Verdict("contradicted" if q.op != "!=" else "discharged")
    yes, no = iv.copy(), iv.copy()
    yes.meet(q.op, q.value)  # type: ignore[arg-type]
    no.meet(_NEGATE[q.op], q.value)  # type: ignore[arg-type]
    if no.empty(integers=False):
        return Verdict("discharged")
    if yes.empty(integers=False):
        return Verdict("contradicted", integer_caveat=False)
    return Verdict("not-implied", integer_caveat=no.empty(integers=True) or yes.empty(True))


def _tally(sat: list[bool]) -> Verdict:
    """The verdict over a finite set of candidate values."""
    if all(sat):
        return Verdict("discharged")
    return Verdict("contradicted" if not any(sat) else "not-implied")


def _atom_on(q: Atom, v: object) -> bool:
    """`q` on a value its path resolves to, with the evaluator's semantics."""
    if q.kind == "present":
        return True
    if q.kind == "len":
        return hasattr(v, "__len__") and _holds(q.op, len(v), q.value)  # type: ignore[arg-type]
    if q.kind == "in":
        return v in q.value  # type: ignore[operator]
    return _holds(q.op, v, q.value)


def implies(ensures: list[str], requirement: str) -> Verdict:
    """Does the conjunction `ensures` imply the atom `requirement`?"""
    given = [atom(s) for s in ensures]
    q = atom(requirement)
    on_path = [a for a in given if a.path == q.path]
    # Cross-kind facts on one path. A `len` atom holds only of a sized value (a string
    # or a list), and a numeric ordering only of a number, so both together are
    # unsatisfiable; and a pinned finite set can be checked against every atom.
    sized = any(a.kind == "len" for a in on_path)
    ordered = any(a.kind == "cmp" and a.op in ("<", "<=", ">", ">=") and _num(a.value)
                  for a in on_path)  # fmt: skip
    if sized and ordered:
        return Verdict("vacuous", "a sized value cannot also be ordered against a number")
    if sized:
        lengths = Interval(lo=0, lo_open=False)
        for a in on_path:
            if a.kind == "len":
                lengths.meet(a.op, a.value)  # type: ignore[arg-type]
        if lengths.empty(integers=True):
            return Verdict("vacuous", "the producer's length constraints are unsatisfiable")
    cands = _value_candidates([a for a in on_path if a.kind in ("cmp", "in")])
    if cands is not None and q.kind != "present":
        cands = [c for c in cands if all(_atom_on(a, c) for a in on_path)]
        if not cands:
            return Verdict("vacuous", "no pinned value satisfies the producer's contract")
        return _tally([_atom_on(q, c) for c in cands])
    if sized and q.kind in ("cmp", "in"):
        # A string or a list: equal to no number, ordered against none.
        if q.kind == "in":
            if all(_num(v) for v in q.value):  # type: ignore[union-attr]
                return Verdict("contradicted")
        elif _num(q.value):
            return Verdict("discharged" if q.op == "!=" else "contradicted")
    if q.kind == "present":
        # Every atom is false on a missing path, so any atom on the path or below it
        # guarantees the path resolves.
        if any(a.path == q.path or a.path.startswith(q.path + ".") for a in given):
            return Verdict("discharged")
        return Verdict("no-guarantee")
    if q.kind == "len":
        lens = [a for a in on_path if a.kind == "len"]
        if lens:
            return _len_verdict(lens, q)
        # A pinned set of values pins their lengths.
        pinned = [a for a in on_path if a.kind == "in" or (a.kind == "cmp" and a.op == "==")]
        if pinned:
            values = _value_candidates(on_path)
            if values is not None and all(hasattr(v, "__len__") for v in values):
                sat = [_holds(q.op, len(v), q.value) for v in values]  # type: ignore[arg-type]
                if not values:
                    return Verdict("vacuous")
                return Verdict(
                    "discharged" if all(sat) else "contradicted" if not any(sat) else "not-implied"
                )
        return Verdict("no-guarantee")
    vals = [a for a in on_path if a.kind in ("cmp", "in")]
    if not vals:
        return Verdict("no-guarantee")
    return _value_verdict(vals, q)
