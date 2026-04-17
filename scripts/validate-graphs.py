#!/usr/bin/env python3
"""CLI wrapper around graph_validator.validate_files.

Usage:
    python3 scripts/validate-graphs.py                 # validate graphs/
    python3 scripts/validate-graphs.py path/to/*.json  # validate explicit files

Exits non-zero if any graph has errors.
"""

import sys
from pathlib import Path


_HERE = Path(__file__).resolve().parent
# Put scripts/ on sys.path so graph_validator can import type_parser
# when this wrapper is invoked directly.
sys.path.insert(0, str(_HERE))

from graph_validator import validate_files  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)

    if argv:
        files = [Path(a) for a in argv]
    else:
        root = _HERE.parent
        graph_dir = root / "graphs"
        files = sorted(
            p for p in graph_dir.glob("*.json") if p.name != "schema.json"
        )

    if not files:
        print("No graph JSON files found.")
        return 0

    errors = validate_files(files)
    if errors:
        print("Graph validation failed:", file=sys.stderr)
        for e in errors:
            print(f"  {e}", file=sys.stderr)
        return 1

    print(f"Validated {len(files)} graph file(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
