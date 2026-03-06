#!/usr/bin/env python3
"""Post-process pandoc markdown output for Google Docs compatibility.

Removes pandoc-specific extensions that don't render in plain markdown:
- Heading anchor attributes {#sec:xxx}
- Span attributes {align="center"}
- Fenced div wrappers (:::) around bibliography entries
- CSL class annotations on div fences
"""

import re
import sys


def clean(text: str) -> str:
    # Remove heading anchors: ## Title {#sec:foo} → ## Title
    text = re.sub(r" \{#[^}]+\}$", "", text, flags=re.MULTILINE)

    # Clean title line: [ **Title** Date ]{align="center"} → **Title**\n\nDate
    text = re.sub(
        r"^\[ \*\*(.+?)\*\* (.+?) \]\{align=\"center\"\}$",
        r"**\1**\n\n\2",
        text,
        flags=re.MULTILINE,
    )

    # Remove fenced div openers/closers and their class annotations
    text = re.sub(r"^:{3,}.*$", "", text, flags=re.MULTILINE)

    # Normalize Unicode spaces (em space, hair space, etc.) to regular spaces
    text = re.sub(r"[\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200a\u200b\u205f]+", " ", text)

    # Collapse multiple spaces to single (but preserve line-leading spaces)
    text = re.sub(r"(?<! ) {2,}", " ", text)


    # Clean escaped brackets from IEEE citations: \[1\] → [1]
    text = re.sub(r"\\\[(\d+(?:,\s*\d+)*)\\\]", r"[\1]", text)

    # Clean CSL bibliography markup:
    # [[1] ]{.csl-left-margin}[Text]{.csl-right-inline} → [1] Text
    text = re.sub(
        r"\[(\[\d+\]\s*)\]\{\.csl-left-margin\}\[(.+?)\]\{\.csl-right-inline\}",
        r"\1\2",
        text,
    )

    # Collapse runs of 3+ blank lines into 2
    text = re.sub(r"\n{4,}", "\n\n\n", text)

    return text.strip() + "\n"


def main() -> int:
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <file.md>", file=sys.stderr)
        return 1

    path = sys.argv[1]
    with open(path) as f:
        text = f.read()

    with open(path, "w") as f:
        f.write(clean(text))

    return 0


if __name__ == "__main__":
    sys.exit(main())
