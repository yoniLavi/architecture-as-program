#!/usr/bin/env python3
"""Guard the frozen founding-vision paper against silent edits.

Paper 1 (papers/01-vision/) is the founding vision: its *content* is the
repository's state before the executable demonstrator (poc/) existed, dated June
2026. Its value is that it is a stable, dated, historical record; that only holds
if its sources are not quietly rewritten. This check compares each frozen file
against its content at the freeze commit and fails if any has drifted.

The freeze reference moved once. The paper was originally frozen at 59898cc~1
(the last pre-poc commit). In July 2026 it received a single sanctioned
editorial-and-metadata revision for its arXiv preprint — typos, phrasing, and
publication front matter, with no substantive claim changed — after which it was
re-frozen at the published-preprint commit named below. That commit is where the
paper lives under papers/01-vision/, so the frozen paths and the freeze ref are
now the same on both sides of the comparison. See papers/01-vision/ERRATA.md and
the paper-corpus spec for the rule that permits one such revision.

Corrections to a frozen paper are otherwise recorded in its ERRATA.md, never by
editing the frozen text — so any diff here is a mistake, and the build should
fail.

If the freeze commit is unavailable (e.g. a shallow CI checkout with no history),
the check prints a warning and passes, rather than failing a build that simply
cannot see the reference. The pre-commit hook, which runs against a full clone,
is the effective guard.
"""

import subprocess
import sys
from pathlib import Path

# The freeze point: the published-preprint commit of Paper 1 (the one-time
# editorial revision of the June-2026 founding vision, edited to stand alone as a
# self-contained preprint). Before the preprint this was "59898cc~1", the last
# commit before poc/ existed.
FREEZE_REF = "0137aea197604c32bf7c6bfb538cfb1bed3c3d86"

# Frozen files in the corpus. At the published-preprint freeze commit the paper
# already lives under papers/01-vision/, so a file's current path and its path at
# the freeze commit are identical; FROZEN_FILES maps current -> frozen for the
# comparison below, here an identity map over the frozen set.
_FROZEN_PATHS = [
    "papers/01-vision/proposal.typ",
    "papers/01-vision/graphs/customer-support.json",
    "papers/01-vision/graphs/support-platform.json",
    "papers/01-vision/graphs/schema.json",
    "papers/01-vision/diagrams/typed-wiring.typ",
]
FROZEN_FILES = {path: path for path in _FROZEN_PATHS}


def git_show(ref_path: str) -> bytes | None:
    """Return the bytes of ref_path at the freeze commit, or None if unavailable."""
    result = subprocess.run(
        ["git", "show", f"{FREEZE_REF}:{ref_path}"],
        capture_output=True,
    )
    return result.stdout if result.returncode == 0 else None


def main() -> int:
    root = Path(__file__).resolve().parent.parent

    # Probe once: if the freeze commit itself is not present, skip gracefully.
    probe = subprocess.run(
        ["git", "cat-file", "-e", f"{FREEZE_REF}:papers/01-vision/proposal.typ"],
        cwd=root,
        capture_output=True,
    )
    if probe.returncode != 0:
        print(
            f"check-freeze: freeze commit {FREEZE_REF} unavailable "
            "(shallow checkout?); skipping frozen-paper guard.",
            file=sys.stderr,
        )
        return 0

    drifted = []
    for current, frozen in FROZEN_FILES.items():
        current_path = root / current
        if not current_path.exists():
            drifted.append(f"{current}: missing (expected a copy of {frozen}@{FREEZE_REF})")
            continue
        expected = git_show(frozen)
        if expected is None:
            drifted.append(f"{current}: cannot read {frozen}@{FREEZE_REF}")
            continue
        if current_path.read_bytes() != expected:
            drifted.append(f"{current}: differs from {frozen}@{FREEZE_REF}")

    if drifted:
        print("ERROR: frozen paper has drifted from the freeze commit:", file=sys.stderr)
        for d in drifted:
            print(f"  {d}", file=sys.stderr)
        print(
            "\nA frozen paper is errata-only. Record corrections in "
            "papers/01-vision/ERRATA.md; do not edit the frozen sources.",
            file=sys.stderr,
        )
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
