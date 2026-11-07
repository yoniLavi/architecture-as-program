"""Paper 3's figures must not move once it is stamped (task 6.4 of `add-paper-3`).

Paper 3 typesets every figure from two artifacts: `dist/generation.json`, rendered
from the committed trial records, and `dist/evaluation-feed.json`, from the feed
service's harness. Later work (Paper 4, the vertical slice) lands in the same
repository, and could shift a count Paper 3 interpolates without touching its source.
This test holds the data Paper 3 reads to its value at the DOI stamp (7 November 2026),
as `test_paper2_figures_pinned.py` does for Paper 2.

What is pinned is the projection `paper3_view` below: the subtrees the paper reads. A
second test reads the paper's source and fails if it reaches a key outside them, so a
new interpolation cannot escape the pin. The feed harness's measured timings are not
read by Paper 3, so nothing here is a measurement.

Re-seed only for a deliberate Paper 3 revision, and say so in the commit:

    uv run --group poc python tests/test_paper3_figures_pinned.py --reseed
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from poc.generation import report  # noqa: E402

PIN_PATH = Path(__file__).parent / "paper3_figures_pin.json"
PAPER = REPO / "papers" / "03-generation" / "proposal.typ"

# The subtrees Paper 3 reads, as (artifact, key, subkey or None for the whole value).
GEN_ROOTS = {
    "max_iterations": None,
    "control": None,
    "groups": ("pilot", "toy"),
    "registered": None,
    "differential": ("by_source",),
    "display": None,
}
FEED_ROOTS = {
    "graphs": None,
    "hostile": ("cases",),
    "corpus": ("cases",),
    "operations": ("runs",),
    "recording": ("ticks", "interval_hours"),
    "live_corpus": ("model", "tier", "cases"),
}
# What a feed case contributes: its name and the fields the paper filters on.
HOSTILE_FIELDS = ("name", "verdict")
CORPUS_FIELDS = ("name", "validator_accepts", "expected")
LIVE_FACTS = ("hostile_in_must_read", "overview_is_attackers", "attacker_text_in_digest")


def generation_payload() -> dict:
    design = json.loads(report.REGISTRATION_PATH.read_text())
    return report.summarise(json.loads(report.RESULTS_PATH.read_text()), design)


def feed_payload() -> dict:
    from poc.evaluate_feed import run, serialise

    return serialise(run())


def _take(data: dict, roots: dict) -> dict:
    out = {}
    for key, subkeys in roots.items():
        out[key] = data[key] if subkeys is None else {s: data[key][s] for s in subkeys}
    return out


def paper3_view(gen: dict, feed: dict) -> dict:
    view_feed = _take(feed, FEED_ROOTS)
    view_feed["hostile"]["cases"] = [
        {f: c[f] for f in HOSTILE_FIELDS} for c in feed["hostile"]["cases"]
    ]
    view_feed["corpus"]["cases"] = [
        {f: c[f] for f in CORPUS_FIELDS} for c in feed["corpus"]["cases"]
    ]
    view_feed["live_corpus"]["cases"] = [
        {
            "name": c["name"],
            "verdict": c["verdict"],
            "facts": {f: c["facts"][f] for f in LIVE_FACTS},
        }
        for c in feed["live_corpus"]["cases"]
    ]
    view_gen = _take(gen, GEN_ROOTS)
    view_gen["groups"] = {g: {"nodes": gen["groups"][g]["nodes"]} for g in GEN_ROOTS["groups"]}
    return {"generation": view_gen, "evaluation-feed": view_feed}


def _needs_wasmtime():
    from poc.sandbox import available

    return pytest.mark.skipif(not available(), reason="needs wasmtime (the `poc` group)")


@_needs_wasmtime()
def test_every_figure_paper_3_reads_holds_its_pinned_value():
    pin = json.loads(PIN_PATH.read_text())
    now = json.loads(json.dumps(paper3_view(generation_payload(), feed_payload())))
    moved = [
        f"{artifact}.{key}"
        for artifact, keys in pin.items()
        for key, value in keys.items()
        if now[artifact].get(key) != value
    ]
    assert not moved, (
        f"data Paper 3 typesets from has moved: {moved}. Paper 3 is stamped; re-seed this "
        f"pin only for a deliberate Paper 3 revision."
    )


def test_the_generation_half_holds_without_wasmtime():
    """The generation artifact is stdlib-only, so this half of the pin runs everywhere."""
    pin = json.loads(PIN_PATH.read_text())["generation"]
    now = json.loads(json.dumps(paper3_view(generation_payload(), _feed_stub())["generation"]))
    assert now == pin


def _feed_stub() -> dict:
    """Enough of the feed artifact's shape for `paper3_view`, when only the
    generation half is wanted."""
    return {
        "graphs": None,
        "hostile": {"cases": []},
        "corpus": {"cases": []},
        "operations": {"runs": None},
        "recording": {"ticks": None, "interval_hours": None},
        "live_corpus": {"model": None, "tier": None, "cases": []},
    }


# How the paper's source names each artifact: `gen` and `feed` directly, and three
# aliases bound in its preamble.
_ALIASES = {
    "gen": ("generation", ()),
    "feed": ("evaluation-feed", ()),
    "reg": ("generation", ("registered",)),
    "gd": ("generation", ("display",)),
    "g": ("evaluation-feed", ("graphs",)),
    "live": ("evaluation-feed", ("live_corpus",)),
}
_BINDINGS = {(artifact, prefix) for artifact, prefix in _ALIASES.values() if prefix}
_ACCESS = re.compile(r"(?<![\w.-])(gen|feed|reg|gd|g|live)((?:\.[a-z_]+)+)")


def test_the_paper_reads_nothing_outside_the_pin():
    """A new interpolation outside the pinned subtrees would be free to drift."""
    # Comments are not interpolations (one names a key the paper must never read).
    source = re.sub(r"//[^\n]*", "", PAPER.read_text().replace("https://", ""))
    roots = {"generation": GEN_ROOTS, "evaluation-feed": FEED_ROOTS}
    escaped = []
    for name, chain in _ACCESS.findall(source):
        artifact, prefix = _ALIASES[name]
        path = list(prefix) + chain.strip(".").split(".")
        if (artifact, tuple(path)) in _BINDINGS:
            continue  # the preamble binding an alias, which is checked where it is used
        key = path[0]
        if key not in roots[artifact]:
            escaped.append(f"{name}{chain}")
            continue
        subkeys = roots[artifact][key]
        if subkeys is not None and (len(path) < 2 or path[1] not in subkeys):
            escaped.append(f"{name}{chain}")
    assert not escaped, f"Paper 3 reads keys the pin does not hold: {sorted(set(escaped))}"


if __name__ == "__main__":
    if sys.argv[1:] != ["--reseed"]:
        raise SystemExit("usage: test_paper3_figures_pinned.py --reseed")
    PIN_PATH.write_text(
        json.dumps(paper3_view(generation_payload(), feed_payload()), indent=1, sort_keys=True)
        + "\n"
    )
    print(f"Wrote {PIN_PATH.relative_to(REPO)}")
