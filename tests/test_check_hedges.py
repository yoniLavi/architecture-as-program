"""Tests for the hedge guard (scripts/check-hedges.py).

The point of these tests is the *failure* path. A guard that only ever passes is
indistinguishable from no guard, and worse than none, because a reader and an
editor both stop looking. So most of what is asserted here is that the check
goes red: when a hedge is deleted, when a pinned claim is rewritten, when a
hedged claim migrates to another section, and when a pin is itself edited down
until it no longer quotes any qualification.
"""

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


def _load():
    spec = importlib.util.spec_from_file_location(
        "check_hedges", ROOT / "scripts" / "check-hedges.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


check_hedges = _load()


@pytest.fixture
def sources():
    """The real corpus sources the pins are seeded against."""
    return {
        paper: (ROOT / paper).read_text(encoding="utf-8")
        for paper in {pin[0] for pin in check_hedges.PINS}
    }


def pin(name):
    """Select a pin by its id.

    Deliberately not by index: pins are grouped by the section they cover, so
    seeding a new one shifts the list, and a positional test would then mutate a
    pin other than the one it names.
    """
    return next(p for p in check_hedges.PINS if p[2] == name)


def test_pins_hold_against_the_current_corpus(sources):
    assert check_hedges.find_violations(sources) == []


def test_every_pin_contains_its_own_hedge():
    """A pin that quotes a claim with no qualification left in it is vacuous."""
    assert check_hedges.malformed_pins() == []


def test_a_pin_whose_hedge_is_absent_from_its_fragment_is_rejected():
    bad = (("paper.typ", "sec:x", "vacuous", "would", "A node acquires nothing."),)
    assert check_hedges.malformed_pins(bad) == [
        "vacuous: hedge 'would' is not present in its own pinned fragment"
    ]


def test_deleting_a_hedge_fails_the_check(sources):
    """The failure this guard exists for: a shortened passage drops a hedge."""
    paper, _section, name, hedge, fragment = pin("privilege/tier-split")
    flat = check_hedges.normalise(fragment)
    mutated = dict(sources)
    mutated[paper] = check_hedges.normalise(sources[paper]).replace(
        flat, flat.replace(hedge, "", 1)
    )
    assert mutated[paper] != check_hedges.normalise(sources[paper]), (
        "the mutation must actually change the source"
    )

    violations = check_hedges.find_violations(mutated)
    assert any(v.startswith(name) for v in violations)


def test_every_pin_fails_when_its_own_hedge_is_removed(sources):
    """Not just the first pin: every one of them is load-bearing."""
    for paper, _section, name, hedge, fragment in check_hedges.PINS:
        flat = check_hedges.normalise(fragment)
        mutated = dict(sources)
        mutated[paper] = check_hedges.normalise(sources[paper]).replace(
            flat, flat.replace(hedge, "", 1)
        )
        violations = check_hedges.find_violations(
            mutated, pins=[(paper, _section, name, hedge, fragment)]
        )
        assert violations, f"removing {hedge!r} from {name} did not fail the check"


def test_rewriting_a_pinned_claim_fails_even_if_a_hedge_word_survives(sources):
    """The naive-grep failure mode: hedge vocabulary retained, claim rephrased.

    A check that counted hedge words in the section would stay green here. This
    one does not, because the claim and its qualification are pinned together.
    """
    paper, _section, name, _hedge, fragment = pin("privilege/no-acquisition")
    mutated = dict(sources)
    mutated[paper] = sources[paper].replace(
        check_hedges.normalise(fragment),
        "A node does not acquire capabilities it was not given, as one would expect",
    )
    violations = check_hedges.find_violations(mutated)
    assert any(v.startswith(name) for v in violations)


def test_a_fragment_that_moves_to_another_section_fails_and_says_so():
    """Migration is a change of altitude, and worth re-reading rather than passing."""
    fragment = "A node would not acquire capabilities it was not given"
    pins = [("p.typ", "sec:security", "moved", "would not acquire", fragment)]
    moved = f"== Security <sec:security>\n\nNothing here.\n\n== Later <sec:later>\n\n{fragment}.\n"
    violations = check_hedges.find_violations({"p.typ": moved}, pins)
    assert len(violations) == 1
    assert "elsewhere in the paper" in violations[0]


def test_a_deleted_fragment_is_distinguished_from_a_moved_one():
    fragment = "A node would not acquire capabilities it was not given"
    pins = [("p.typ", "sec:security", "gone", "would not acquire", fragment)]
    violations = check_hedges.find_violations(
        {"p.typ": "== Security <sec:security>\n\nA node does not acquire capabilities.\n"}, pins
    )
    assert len(violations) == 1
    assert "nowhere in the paper" in violations[0]


def test_a_missing_section_is_reported_rather_than_passed():
    pins = [("p.typ", "sec:gone", "orphan", "would", "would not acquire")]
    violations = check_hedges.find_violations({"p.typ": "= Something <sec:other>\n\ntext\n"}, pins)
    assert violations == ["orphan: p.typ has no section <sec:gone>"]


def test_a_missing_paper_is_reported_rather_than_passed():
    pins = [("gone.typ", "sec:x", "orphan", "would", "would not acquire")]
    assert check_hedges.find_violations({}, pins) == ["orphan: gone.typ not found"]


def test_fragments_match_across_line_breaks():
    """Typst sources wrap; a pin must not depend on where a line happens to end."""
    source = "== S <sec:s>\n\nA node would not\nacquire capabilities.\n"
    pins = [("p.typ", "sec:s", "wrapped", "would not", "A node would not acquire capabilities.")]
    assert check_hedges.find_violations({"p.typ": source}, pins) == []


def test_the_seeded_pins_cover_the_design_section_of_paper_2():
    """The guard is seeded where AGENTS.md says the hedging discipline fails."""
    sections = {pin[1] for pin in check_hedges.PINS}
    assert "sec:security" in sections
    assert all(pin[0] == "papers/02-demonstrator/proposal.typ" for pin in check_hedges.PINS)


def test_tier_restricted_properties_are_pinned_on_both_paragraphs(sources):
    """A confined-tier-only property that reads as universal is an overclaim.

    Both §2.5 paragraphs that carry one are pinned, so neither can lose its tier
    restriction while the other keeps it.
    """
    tier_pins = [p for p in check_hedges.PINS if "only as an object discipline" in p[3]]
    assert len(tier_pins) >= 2
    assert {p[2] for p in tier_pins} == {"privilege/tier-split", "supply-chain/tier-split"}
