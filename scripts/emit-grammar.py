#!/usr/bin/env python3
"""Emit a Markdown grammar card for the signal-graph type language.

The output (`dist/grammar.md`) is a self-contained reference that
stays in sync with scripts/type_parser.py: each worked example is
produced by actually parsing and unparsing the expression, and the
subtyping examples are asserted against `is_assignable` at build
time, so the card fails loudly if the implementation drifts.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

from type_parser import (  # noqa: E402
    TApp,
    TList,
    TName,
    TString,
    TSum,
    TVariant,
    is_assignable,
    parse_type,
    unparse,
)

GRAMMAR = """\
type        := variant ( '|' variant )*
variant     := ( IDENT ':' )? application
application := atom ( '<' type ( ',' type )* '>' )?
atom        := IDENT | STRING | list
list        := '[' ( type ( ',' type )* )? ']'
STRING      := "'" [^']* "'"
IDENT       := [A-Za-z_] [A-Za-z0-9_-]*
"""


def _render_ast(ast: Any, indent: int = 0) -> str:
    pad = "  " * indent
    if isinstance(ast, TName):
        return f"{pad}TName({ast.name!r})"
    if isinstance(ast, TString):
        return f"{pad}TString({ast.value!r})"
    if isinstance(ast, TList):
        if not ast.items:
            return f"{pad}TList([])"
        parts = [f"{pad}TList(["]
        for item in ast.items:
            parts.append(_render_ast(item, indent + 1) + ",")
        parts.append(f"{pad}])")
        return "\n".join(parts)
    if isinstance(ast, TApp):
        parts = [f"{pad}TApp({ast.head!r},"]
        for arg in ast.args:
            parts.append(_render_ast(arg, indent + 1) + ",")
        parts.append(f"{pad})")
        return "\n".join(parts)
    if isinstance(ast, TVariant):
        inner = _render_ast(ast.inner, indent + 1)
        return f"{pad}TVariant(role={ast.role!r},\n{inner})"
    if isinstance(ast, TSum):
        parts = [f"{pad}TSum(["]
        for v in ast.variants:
            parts.append(_render_ast(v, indent + 1) + ",")
        parts.append(f"{pad}])")
        return "\n".join(parts)
    return f"{pad}{ast!r}"


def _gather_canonical_types(root: Path) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for graph_path in sorted((root / "graphs").glob("*.json")):
        if graph_path.name == "schema.json":
            continue
        data = json.loads(graph_path.read_text())
        for param in data.get("parameters", []):
            if param not in seen:
                seen.add(param)
                ordered.append(param)
        for node in data.get("nodes", []):
            for inp in node.get("inputs", []):
                if inp not in seen:
                    seen.add(inp)
                    ordered.append(inp)
            out = node.get("output", "")
            if out and out not in seen:
                seen.add(out)
                ordered.append(out)
    return ordered


def _subtype_line(actual: str, target: str, expected: bool) -> str:
    ok = is_assignable(parse_type(actual), parse_type(target))
    assert ok == expected, (
        f"Grammar card and validator disagree: "
        f"is_assignable({actual!r}, {target!r}) was {ok}, "
        f"card expected {expected}."
    )
    mark = "✓" if ok else "✗"
    return f"- {mark} `{actual}` assignable to `{target}`"


def render_card(canonical_types: list[str]) -> str:
    lines: list[str] = []
    lines.append("# Signal-graph type language — grammar card")
    lines.append("")
    lines.append(
        "This file is a build artifact emitted by "
        "`scripts/emit-grammar.py` from `scripts/type_parser.py`. "
        "It documents the surface syntax and subtyping rules the "
        "proof-of-concept validator accepts for type expressions in "
        "the canonical graph JSONs. Worked examples are produced by "
        "actually parsing and unparsing each expression; subtype "
        "examples are asserted against `is_assignable` at card-build "
        "time, so the card fails loudly if the validator drifts."
    )
    lines.append("")

    lines.append("## Grammar")
    lines.append("")
    lines.append("```ebnf")
    lines.append(GRAMMAR.rstrip())
    lines.append("```")
    lines.append("")
    lines.append(
        "Hyphens are permitted inside identifiers so tokens like "
        "`read-write` parse as a single name, matching the usage in "
        "the canonical graph JSONs. Whitespace between tokens is "
        "insignificant."
    )
    lines.append("")

    lines.append("## Worked examples")
    lines.append("")
    lines.append(
        "Each type expression drawn from the canonical graphs is "
        "shown with the AST the parser produces. `unparse` reproduces "
        "the surface form from the AST; the roundtrip is asserted at "
        "build time."
    )
    lines.append("")
    for t in canonical_types:
        ast = parse_type(t)
        roundtrip = unparse(ast)
        assert roundtrip == t, f"Parser does not roundtrip: {t!r} -> {roundtrip!r}"
        lines.append(f"### `{t}`")
        lines.append("")
        lines.append("```")
        lines.append(_render_ast(ast))
        lines.append("```")
        lines.append("")

    lines.append("## Subtyping (capability narrowing)")
    lines.append("")
    lines.append(
        "The validator uses strict type-equality for data flow at "
        "edges. At cross-graph composition boundaries — where a parent "
        "graph provides capability handles to a node that refers to "
        "another graph — capability positions admit structural "
        "subtyping: a parent may supply a handle with at least the "
        "authority the sub-graph declares. All other positions "
        "continue to require exact equality."
    )
    lines.append("")

    lines.append("### `LLMClient`")
    lines.append("")
    lines.append(
        "An `LLMClient<[tools]>` handle with tool set *S₁* is "
        "assignable to one with tool set *S₂* iff *S₂ ⊆ S₁* — the "
        "provided handle offers at least every tool the target "
        "requires. `LLMClient<inference>` is the empty-tool-set form "
        "(no tools beyond inference)."
    )
    lines.append("")
    for actual, target, expected in [
        ("LLMClient<[lookup, respond]>", "LLMClient<[lookup]>", True),
        ("LLMClient<[lookup]>", "LLMClient<[lookup, respond]>", False),
        ("LLMClient<[lookup]>", "LLMClient<inference>", True),
        ("LLMClient<inference>", "LLMClient<[lookup]>", False),
        ("LLMClient<inference>", "LLMClient<inference>", True),
    ]:
        lines.append(_subtype_line(actual, target, expected))
    lines.append("")

    lines.append("### `DBHandle`")
    lines.append("")
    lines.append(
        "Scopes must match exactly. The provided mode must cover the "
        "target mode under the lattice `read-write ⊇ {read, append}`; "
        "`read` and `append` are incomparable."
    )
    lines.append("")
    for actual, target, expected in [
        ("DBHandle<'kb', read-write>", "DBHandle<'kb', read>", True),
        ("DBHandle<'kb', read-write>", "DBHandle<'kb', append>", True),
        ("DBHandle<'kb', read>", "DBHandle<'kb', read-write>", False),
        ("DBHandle<'kb', read>", "DBHandle<'kb', append>", False),
        ("DBHandle<'kb', append>", "DBHandle<'kb', read>", False),
        ("DBHandle<'kb', read>", "DBHandle<'other', read>", False),
    ]:
        lines.append(_subtype_line(actual, target, expected))
    lines.append("")

    lines.append("## Trust propagation")
    lines.append("")
    lines.append(
        "A node whose data inputs contain an `Untrusted<_>` "
        "application and whose output is not wrapped in `Untrusted<_>` "
        'must declare `"discharges_trust": true` in its JSON '
        "definition. The converse is also checked: a "
        "`discharges_trust: true` annotation without an `Untrusted<_>` "
        "input is rejected as stale. Trust discharge is therefore "
        "always visible at the graph level; the `Untrusted<T>` ≰ `T` "
        "rule is enforced structurally rather than by a coercion "
        "lattice (see the demonstrator paper's research agenda for the "
        "coercion-problem discussion)."
    )
    lines.append("")

    lines.append("## Variant-completeness")
    lines.append("")
    lines.append(
        "For every node whose output is a sum type `role₁: T₁ | role₂: "
        "T₂ | …`, the validator requires at least one consuming edge "
        "per role (addressed as `Node.role`), unless the whole output "
        "is consumed by an unported edge. Dead variants are flagged "
        "so that branch coverage is visible at the graph level rather "
        "than hidden in implementation code."
    )
    lines.append("")

    return "\n".join(lines) + "\n"


def main() -> int:
    root = _HERE.parent
    types = _gather_canonical_types(root)
    card = render_card(types)
    out_dir = root / "dist"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / "grammar.md"
    out_path.write_text(card)
    print(f"Wrote {out_path.relative_to(root)} ({len(card)} bytes).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
