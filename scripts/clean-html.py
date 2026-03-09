#!/usr/bin/env python3
"""Post-process pandoc HTML output.

- Removes the pandoc-generated title block header (duplicate of in-body title)
- Fixes image paths: dist/diagrams/foo.svg → diagrams/foo.svg
- Copies diagram SVGs alongside the HTML
"""

import re
import sys


def clean(text: str) -> str:
    # Remove pandoc's title-block header (title, author, date) — the body has its own
    text = re.sub(
        r"<header id=\"title-block-header\">.*?</header>",
        "",
        text,
        flags=re.DOTALL,
    )

    # Fix image paths: dist/diagrams/foo.svg → diagrams/foo.svg (HTML lives in dist/)
    text = re.sub(r'src="dist/', 'src="', text)

    return text


def main() -> int:
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <file.html>", file=sys.stderr)
        return 1

    path = sys.argv[1]
    with open(path) as f:
        text = f.read()

    with open(path, "w") as f:
        f.write(clean(text))

    return 0


if __name__ == "__main__":
    sys.exit(main())
