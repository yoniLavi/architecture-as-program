#!/usr/bin/env python3
"""Check that restructuring an OpenSpec spec dropped no normative sentence.

    check-spec-restructure.py BEFORE AFTER

Used by `openspec/changes/update-openspec-to-2`, which moves the text of long
requirements into scenarios (or into a new requirement beside them) without
changing what any requirement says. Every sentence of BEFORE that contains SHALL
or MUST must appear, word for word, somewhere in AFTER. Whitespace, line breaks,
a list marker, a scenario keyword (`**WHEN**`, `**THEN**`, `**AND**`) and a
final full stop are ignored, so a sentence may move from a requirement's body
into a scenario's THEN line. Anything else is a rewording, and fails.

What it cannot see, stated in the change's design (decision 3): a sentence
moved under a scenario whose WHEN narrows it; two sentences whose order carried
meaning; and a non-normative sentence that bounded a normative one. Those rest
on reading the diff.

Stdlib only. Exit 0 when nothing is missing, 1 otherwise.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

NORMATIVE = re.compile(r"\b(SHALL|MUST)\b")
KEYWORD = re.compile(r"^\*\*(WHEN|THEN|AND|GIVEN)\*\*\s+")
LIST_MARKER = re.compile(r"^(?:[-*+]|\d+[.)])\s+")
# A sentence ends at '.', '?' or '!' followed by space and the start of a new one.
SENTENCE_END = re.compile(r"(?<=[.?!])\s+(?=[A-Z`*(\"'])")


def units(text: str) -> list[str]:
    """Paragraphs and list items, each joined onto one line.

    Headings end a unit and are not units themselves: a requirement's name is
    not one of its sentences.
    """
    out: list[str] = []
    current: list[str] = []

    def flush() -> None:
        if current:
            out.append(" ".join(current))
            current.clear()

    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            flush()
            continue
        if LIST_MARKER.match(line):
            flush()
            line = LIST_MARKER.sub("", line, count=1)
        current.append(line)
    flush()
    return out


def normalise(sentence: str) -> str:
    sentence = KEYWORD.sub("", sentence.strip())
    sentence = re.sub(r"\s+", " ", sentence)
    return sentence.rstrip(".").strip()


def sentences(text: str) -> list[str]:
    found = []
    for unit in units(text):
        unit = KEYWORD.sub("", unit)
        for part in SENTENCE_END.split(unit):
            part = normalise(part)
            if part:
                found.append(part)
    return found


def normative(text: str) -> list[str]:
    return [s for s in sentences(text) if NORMATIVE.search(s)]


def missing(before: str, after: str) -> list[str]:
    """Normative sentences of `before` that are not in `after`, in order."""
    present = set(sentences(after))
    # A sentence may also have been split across a unit boundary that the
    # restructuring introduced; matching against the flattened text catches
    # the verbatim case without accepting a rewording.
    flat = re.sub(r"\s+", " ", " ".join(normalise(u) for u in units(after)))
    return [s for s in normative(before) if s not in present and s not in flat]


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("usage: check-spec-restructure.py BEFORE AFTER", file=sys.stderr)
        return 2
    before = Path(argv[1]).read_text(encoding="utf-8")
    after = Path(argv[2]).read_text(encoding="utf-8")
    lost = missing(before, after)
    total = len(normative(before))
    if lost:
        print(f"{len(lost)} of {total} normative sentences missing from {argv[2]}:")
        for s in lost:
            print(f"  - {s}")
        return 1
    print(f"ok: all {total} normative sentences of {argv[1]} are present in {argv[2]}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
