"""Paper 2's figures must not move while the feed-triage work lands beside them.

Paper 2 typesets every figure in its Evaluation section from `dist/evaluation.json`.
The feed-triage service and the generation experiment add capability kinds, graphs,
components and corpus cases to the same repository, and any of them could shift a
count the paper interpolates without touching the paper's source. This test holds
the data the paper reads to its value when that work began (9 October 2026).

What is pinned: every key of the evaluation data that is a property of the code.
What is not: the wall-clock timings and the description of the machine that took
them, which differ from run to run and are guarded by the overhead band instead
(`MEASURED` below names them, so the split is a list rather than a judgement).

The pin is removed, or re-seeded, deliberately: when Paper 2 is revised (version
1.1), regenerate `tests/paper2_evaluation_pin.json` and say so in the commit. A
change that needs it re-seeded before then has moved a published claim.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from poc.evaluate import run, serialise
from poc.sandbox import available

PIN_PATH = Path(__file__).parent / "paper2_evaluation_pin.json"

# Measurements, not properties: excluded from the pin, checked by the band.
MEASURED = frozenset(
    {
        "compilation_ms",
        "instantiation_ms",
        "crossing_ms",
        "crossing_us",
        "parse_invocation_ms",
        "generate_invocation_ms",
        "projected_overhead",
        "crossing_magnitude",
    }
)
UNPINNED_SECTIONS = frozenset({"environment"})

pytestmark = pytest.mark.skipif(not available(), reason="needs wasmtime (the `poc` group)")


@pytest.fixture(scope="module")
def payload() -> dict:
    return json.loads(serialise(run()))


def test_every_property_paper_2_reads_holds_its_pinned_value(payload):
    pin = json.loads(PIN_PATH.read_text())
    moved = [
        f"{section}.{key}"
        for section, keys in pin.items()
        for key, value in keys.items()
        if payload[section].get(key) != value
    ]
    assert not moved, (
        f"evaluation data Paper 2 typesets from has moved: {moved}. The feed-triage "
        f"evidence belongs in dist/evaluation-feed.json; re-seed this pin only for a "
        f"deliberate Paper 2 revision."
    )


def test_the_pin_covers_every_key_that_is_not_a_measurement(payload):
    """A key added to the evaluation data without a pin would be free to drift."""
    pin = json.loads(PIN_PATH.read_text())
    assert set(payload) - UNPINNED_SECTIONS == set(pin)
    for section, keys in pin.items():
        assert set(payload[section]) - MEASURED == set(keys), section
