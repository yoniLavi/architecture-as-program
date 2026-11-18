"""S2's checks. Stdlib-only apart from pytest:

    uv run pytest spikes/specified-architecture/s2 -q

The decision procedure is held to the evaluator it reasons about
(`poc.contracts.parse(...).holds`): for every verdict on a generated case, a search
over concrete values looks for a counterexample. `discharged` must have none;
`contradicted` must have no value satisfying both; `not-implied` should have one
(found, or the search is reported as too weak).
"""

from __future__ import annotations

import itertools
import random

import pytest

from poc.contracts import parse

from .implication import implies
from .run import edges

# ── Constructed cases, including the one that fails by construction ──


@pytest.mark.parametrize(
    "ensures, requires, verdict",
    [
        (["len(q) <= 512"], "len(q) <= 512", "discharged"),
        (["len(q) <= 500"], "len(q) <= 512", "discharged"),
        (["len(q) <= 600"], "len(q) <= 512", "not-implied"),  # fails by construction
        (["len(q) > 600"], "len(q) <= 512", "contradicted"),  # fails by construction
        (["len(q) == 10"], "len(q) >= 1", "discharged"),
        (["len(q) >= 1", "len(q) <= 1"], "len(q) == 1", "discharged"),
        (["len(q) < 0"], "len(q) == 1", "vacuous"),
        (["x >= 0", "x <= 5"], "x <= 5", "discharged"),
        (["x > 0"], "x >= 1", "not-implied"),  # over the reals; true over the integers
        (["x == 3"], "x in [1, 2, 3]", "discharged"),
        (["x in [1, 2]"], "x in [1, 2, 3]", "discharged"),
        (["x in [1, 4]"], "x in [1, 2, 3]", "not-implied"),
        (["x in [4, 5]"], "x in [1, 2, 3]", "contradicted"),
        (["kind in ['a', 'b']", "kind != 'b'"], "kind == 'a'", "discharged"),
        (["flag == true"], "flag == true", "discharged"),
        (["a.b == 1"], "present(a)", "discharged"),
        (["len(a.b) <= 3"], "present(a.b)", "discharged"),
        (["present(a)"], "present(a.b)", "no-guarantee"),
        (["len(y) <= 3"], "len(q) <= 3", "no-guarantee"),
        (["d == 'abcdefghij'"], "len(d) == 10", "discharged"),
        ([], "present(x)", "no-guarantee"),
    ],
)
def test_constructed(ensures, requires, verdict):
    assert implies(ensures, requires).verdict == verdict


# ── Held to the evaluator ───────────────────────────────────────────

# Literals are what the vocabulary admits: integers, booleans, quoted strings (no
# floats). Field *values* may still be floats, so the world below includes them.
_LITS = [0, 1, 2, 3, 5, -1, True, False, "a", "b", ""]
_OPS = ["==", "!=", "<", "<=", ">", ">="]


def _random_atom(rng: random.Random, path: str) -> str:
    form = rng.choice(["len", "cmp", "in", "present"])
    if form == "len":
        return f"len({path}) {rng.choice(_OPS)} {rng.choice([0, 1, 2, 3, 5])}"
    if form == "in":
        items = rng.sample([0, 1, 2, 3, "'a'", "'b'"], rng.randint(1, 3))
        return f"{path} in [{', '.join(map(str, items))}]"
    if form == "present":
        return f"present({path})"
    lit = rng.choice(_LITS)
    if isinstance(lit, str):
        text = f"'{lit}'"
    elif isinstance(lit, bool):
        text = "true" if lit else "false"
    else:
        text = str(lit)
    return f"{path} {rng.choice(_OPS)} {text}"


def _values():
    yield from [-2, -1, -0.5, 0, 0.25, 0.5, 1, 1.5, 2, 3, 4, 5, 6, True, False]
    yield from ["", "a", "b", "ab", "abc", "abcde", "abcdef"]
    yield from [[], [1], [1, 2], [1, 2, 3], [0] * 5, [0] * 6]


def _worlds():
    for v in _values():
        yield {"x": v}
    yield {}


def test_every_verdict_agrees_with_the_evaluator():
    rng = random.Random(20261118)
    counts = {"discharged": 0, "contradicted": 0, "not-implied": 0, "witnessed": 0}
    for _ in range(3000):
        ensures = [_random_atom(rng, "x") for _ in range(rng.randint(1, 3))]
        req = _random_atom(rng, "x")
        v = implies(ensures, req).verdict
        pre = [parse(s) for s in ensures]
        q = parse(req)
        sat_pre = [w for w in _worlds() if all(p.holds(w) for p in pre)]
        if v == "discharged":
            bad = [w for w in sat_pre if not q.holds(w)]
            assert not bad, (ensures, req, bad[:3])
            counts["discharged"] += 1
        elif v == "contradicted":
            assert not [w for w in sat_pre if q.holds(w)], (ensures, req)
            counts["contradicted"] += 1
        elif v == "vacuous":
            assert not sat_pre, (ensures, req)
        elif v == "not-implied":
            counts["not-implied"] += 1
            if any(not q.holds(w) for w in sat_pre):
                counts["witnessed"] += 1
    # Every class occurred, and most not-implied verdicts were witnessed by this
    # small value set (the rest need a value it does not contain, e.g. 0.75).
    assert all(counts[k] > 50 for k in ("discharged", "contradicted", "not-implied"))
    assert counts["witnessed"] / counts["not-implied"] > 0.95, counts


# ── The repository's graphs ─────────────────────────────────────────


def test_feed_triage_join_edge_is_discharged():
    import json
    from pathlib import Path

    g = json.loads((Path(__file__).resolve().parents[3] / "graphs/feed-triage.json").read_text())
    rows = {r["edge"]: r for r in edges(g)}
    assert rows["StartRun -> ComposeDigest[1]"]["verdict"] == "discharged"
    assert "SelectItems -> ComposeDigest[0]" not in rows  # the requires reads input 1 only


def test_nothing_on_the_repository_graphs_is_undecided():
    from .run import _graphs

    for _, g in _graphs():
        assert all(r["verdict"] != "undecided" for r in edges(g))


def test_products_are_small():
    """No exponential blow-up: the check is linear in atoms per path."""
    ens = [f"len(p{i}) <= {i}" for i in range(200)]
    for i, _ in itertools.product(range(200), [0]):
        assert implies(ens, f"len(p{i}) <= {i + 1}").verdict == "discharged"
