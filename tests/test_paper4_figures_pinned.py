"""Paper 4's figures must not move under it (task 3.3 of `add-paper-4`).

Paper 4 typesets every figure from three artifacts: `dist/architect.json`, the
banking subtrees of `dist/agentdojo-banking.json`, and the `post_hoc` block of
`dist/slice.json`. Each is rendered from committed records, and later work in the
same repository could shift a count the paper interpolates without touching its
source. This test holds the data Paper 4 reads to a pinned value, as
`test_paper3_figures_pinned.py` does for Paper 3.

What is pinned is `paper4_view` below: the whole of the architect artifact, which the
paper reads through many aliases, and the named subtrees of the other two. A second
test reads the paper's source and fails if it reaches a banking or slice key outside
them, so a new interpolation cannot escape the pin.

Seeded while Paper 4 is in draft (16 November 2026). Re-seed for a deliberate change
to the evidence or the keys the paper reads, and say so in the commit; once Paper 4 is
stamped, only for a deliberate revision:

    uv run python tests/test_paper4_figures_pinned.py --reseed
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from poc.agentdojo import report as banking  # noqa: E402
from poc.architect import report as architect  # noqa: E402
from poc.slice import report as slice_report  # noqa: E402

PIN_PATH = Path(__file__).parent / "paper4_figures_pin.json"
PAPER = REPO / "papers" / "04-architect" / "proposal.typ"

# The subtrees Paper 4 reads from the two artifacts it does not read whole.
BANKING_ROOTS = ("suite", "attack", "goals", "any_payment_goals", "baseline")
SLICE_ROOTS = ("post_hoc",)


def paper4_view() -> dict:
    bank = banking.build()
    sl = slice_report.build()
    return {
        "architect": architect.build(),
        "agentdojo-banking": {k: bank[k] for k in BANKING_ROOTS},
        "slice": {k: sl[k] for k in SLICE_ROOTS},
    }


def test_every_figure_paper_4_reads_holds_its_pinned_value():
    pin = json.loads(PIN_PATH.read_text())
    now = json.loads(json.dumps(paper4_view()))
    moved = [
        f"{artifact}.{key}"
        for artifact, keys in pin.items()
        for key, value in keys.items()
        if now[artifact].get(key) != value
    ]
    assert not moved, (
        f"data Paper 4 typesets from has moved: {moved}. Re-seed this pin only for a "
        f"deliberate change, and say so in the commit."
    )


# The paper binds `bank` and `slice` to the two partly read artifacts, and reads the
# slice only through `ph`, bound to `slice.post_hoc`.
_ACCESS = re.compile(r"(?<![\w./-])(bank|slice)\.([a-z_]+)")


def test_the_paper_reads_nothing_outside_the_pin():
    """A new interpolation outside the pinned subtrees would be free to drift."""
    source = re.sub(r"//[^\n]*", "", PAPER.read_text().replace("https://", ""))
    roots = {"bank": BANKING_ROOTS, "slice": SLICE_ROOTS}
    escaped = sorted(
        {f"{name}.{key}" for name, key in _ACCESS.findall(source) if key not in roots[name]}
    )
    assert not escaped, f"Paper 4 reads keys the pin does not hold: {escaped}"


def test_the_escape_check_sees_both_artifacts():
    """The regex must find the paper's reads, or the check above passes vacuously."""
    found = {name for name, _ in _ACCESS.findall(PAPER.read_text())}
    assert found == {"bank", "slice"}


if __name__ == "__main__":
    if sys.argv[1:] != ["--reseed"]:
        raise SystemExit("usage: test_paper4_figures_pinned.py --reseed")
    PIN_PATH.write_text(json.dumps(paper4_view(), indent=1, sort_keys=True) + "\n")
    print(f"Wrote {PIN_PATH.relative_to(REPO)}")
