#!/usr/bin/env python3
"""Check for unused .bib entries not cited in any .typ file.

Note: Missing/broken citations are already caught by `typst compile`.
This script catches the reverse: bib entries that exist but are never used.
"""

import re
import sys
from pathlib import Path


def extract_bib_keys(bib_path: Path) -> set[str]:
    """Extract all entry keys from a .bib file."""
    content = bib_path.read_text()
    return set(re.findall(r"@\w+\{([\w-]+),", content))


def extract_typ_citations(typ_path: Path) -> set[str]:
    """Extract all citation keys referenced in a .typ file."""
    content = typ_path.read_text()
    citations = set()
    # @citation_key (bare syntax)
    for match in re.finditer(r"(?<![#\\])@([\w:.-]+[\w])", content):
        key = match.group(1)
        if ":" not in key:
            citations.add(key)
    # #cite(<key>) syntax
    for match in re.finditer(r"#cite\(<([\w-]+)>", content):
        citations.add(match.group(1))
    return citations


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    bib_files = list(root.glob("*.bib"))
    typ_files = list(root.glob("*.typ"))

    if not bib_files or not typ_files:
        return 0

    all_bib_keys: set[str] = set()
    for bib in bib_files:
        all_bib_keys |= extract_bib_keys(bib)

    all_citations: set[str] = set()
    for typ in typ_files:
        all_citations |= extract_typ_citations(typ)

    unused = all_bib_keys - all_citations
    if unused:
        print("WARNING: Bib entries not cited in any .typ file:")
        for key in sorted(unused):
            print(f"  @{key}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
