"""Validator for signal-graph JSON definitions.

Four layers of check:

  1. Structural. Required fields present with correct JSON types
     (informal mirror of graphs/schema.json).
  2. Intra-graph. Declared capabilities are used; declared boundary
     data inputs are consumed; edges reference existing nodes; sum-
     type variant ports exist; layout references only known nodes.
  3. Type-aware. Edge type compatibility with sum-type variant
     resolution, and trust propagation — every node that consumes an
     `Untrusted<_>` input and emits a non-`Untrusted` output must
     declare `discharges_trust: true`, making the discharge point
     explicit.
  4. Cross-graph. If a node's name matches another graph's `name`,
     its input list must equal that graph's parameter list. Catches
     sub-graph signature mismatches.

Designed to be stdlib-only so the pre-commit hook stays portable.
The validator is imported by tests and wrapped by
scripts/validate-graphs.py for CLI use.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable
from pathlib import Path

from type_parser import (
    ParseError,
    Type,
    contains_untrusted,
    is_assignable,
    parse_type,
    sum_roles,
    sum_variant_type,
    unparse,
)

_NAME_RE = re.compile(r"^[A-Z][A-Za-z0-9]*$")


# ── Per-graph validation ───────────────────────────────────────────


def _validate_structure(graph: dict, path: Path, errors: list[str]) -> bool:
    """Minimal structural check. Returns True if the graph is valid
    enough to proceed to semantic checks."""
    ok = True
    for field in ("name", "parameters", "capabilities", "nodes", "data_edges"):
        if field not in graph:
            errors.append(f"{path.name}: missing required field: {field}")
            ok = False
    if not ok:
        return False

    if not isinstance(graph["name"], str) or not _NAME_RE.match(graph["name"]):
        errors.append(f"{path.name}: `name` must be PascalCase, got: {graph['name']!r}")
        ok = False
    for f in ("parameters", "capabilities"):
        v = graph[f]
        if not isinstance(v, list) or not all(isinstance(s, str) and s for s in v):
            errors.append(f"{path.name}: `{f}` must be a list of non-empty strings")
            ok = False
    if not isinstance(graph["nodes"], list) or not graph["nodes"]:
        errors.append(f"{path.name}: `nodes` must be a non-empty list")
        ok = False
    if not isinstance(graph["data_edges"], list):
        errors.append(f"{path.name}: `data_edges` must be a list")
        ok = False
    return ok


def _data_inputs(node: dict, caps: list[str]) -> list[str]:
    """Non-capability inputs of a node, in declaration order."""
    return [inp for inp in node["inputs"] if inp not in caps]


def _try_parse(src: str, label: str, path: Path, errors: list[str]) -> Type | None:
    try:
        return parse_type(src)
    except ParseError as e:
        errors.append(f"{path.name}: cannot parse {label}: {e}")
        return None


def _validate_semantic(graph: dict, path: Path, errors: list[str]) -> dict[str, dict]:
    params = graph["parameters"]
    caps = graph["capabilities"]
    nodes = graph["nodes"]
    edges = graph["data_edges"]

    # Every capability must be declared as a parameter.
    for c in caps:
        if c not in params:
            errors.append(f"{path.name}: capability {c!r} not listed in parameters")

    # Nodes: shape + uniqueness.
    node_map: dict[str, dict] = {}
    for n in nodes:
        if not isinstance(n, dict):
            errors.append(f"{path.name}: node must be an object, got: {n!r}")
            continue
        missing = [f for f in ("name", "inputs", "output") if f not in n]
        if missing:
            errors.append(f"{path.name}: node missing fields {missing}: {n}")
            continue
        nname = n["name"]
        if not isinstance(nname, str) or not _NAME_RE.match(nname):
            errors.append(f"{path.name}: node name must be PascalCase: {nname!r}")
            continue
        if nname in node_map:
            errors.append(f"{path.name}: duplicate node name: {nname!r}")
            continue
        if not isinstance(n["inputs"], list) or not all(
            isinstance(s, str) and s for s in n["inputs"]
        ):
            errors.append(
                f"{path.name}: node {nname!r} `inputs` must be a list of non-empty strings"
            )
            continue
        if not isinstance(n["output"], str) or not n["output"]:
            errors.append(f"{path.name}: node {nname!r} `output` must be a non-empty string")
            continue
        if "discharges_trust" in n and not isinstance(n["discharges_trust"], bool):
            errors.append(f"{path.name}: node {nname!r} `discharges_trust` must be boolean")
            continue
        node_map[nname] = n

    # Every declared capability must be used by at least one node.
    used_caps: set[str] = set()
    for n in node_map.values():
        for inp in n["inputs"]:
            if inp in caps:
                used_caps.add(inp)
    for c in caps:
        if c not in used_caps:
            errors.append(f"{path.name}: capability {c!r} declared but never used in any node")

    # Every non-capability parameter must be consumed by at least one node.
    data_params = [p for p in params if p not in caps]
    consumed: set[str] = set()
    for n in node_map.values():
        for inp in n["inputs"]:
            if inp in data_params:
                consumed.add(inp)
    for p in data_params:
        if p not in consumed:
            errors.append(f"{path.name}: boundary data input {p!r} declared but never consumed")

    _validate_edges(path, node_map, caps, edges, errors)
    _validate_trust_propagation(path, node_map, caps, errors)
    _validate_layout(path, node_map, graph.get("layout", {}), errors)

    return node_map


def _validate_edges(
    path: Path,
    node_map: dict[str, dict],
    caps: list[str],
    edges: list[dict],
    errors: list[str],
) -> None:
    # Track, per source node, which output-variant roles (and the
    # whole unported output) have at least one consumer. Used for
    # the variant-completeness check below.
    consumed_ports: dict[str, set[str]] = {n: set() for n in node_map}
    consumed_whole: set[str] = set()

    for e in edges:
        if not isinstance(e, dict) or "from" not in e or "to" not in e:
            errors.append(f"{path.name}: edge must be an object with `from` and `to`: {e!r}")
            continue
        fr = e["from"]
        to = e["to"]
        if "." in fr:
            from_node, port = fr.rsplit(".", 1)
        else:
            from_node, port = fr, None

        if from_node not in node_map:
            errors.append(f"{path.name}: edge `from` references unknown node: {fr!r}")
            continue
        if to not in node_map:
            errors.append(f"{path.name}: edge `to` references unknown node: {to!r}")
            continue

        src_node = node_map[from_node]
        tgt_node = node_map[to]

        src_output_ast = _try_parse(
            src_node["output"], f"output of node {from_node!r}", path, errors
        )
        if src_output_ast is None:
            continue

        # Variant resolution.
        if port is not None:
            variants = sum_roles(src_output_ast)
            if not variants:
                errors.append(
                    f"{path.name}: edge {fr!r}→{to!r} addresses a port but "
                    f"{from_node!r}'s output is not a sum type: "
                    f"{unparse(src_output_ast)!r}"
                )
                continue
            if port not in variants:
                errors.append(
                    f"{path.name}: edge {fr!r}→{to!r} addresses unknown port "
                    f"{port!r}; available variants: {variants}"
                )
                continue
            src_ast = sum_variant_type(src_output_ast, port)
            if src_ast is None:
                continue  # shouldn't happen given the check above
            consumed_ports[from_node].add(port)
        else:
            src_ast = src_output_ast
            consumed_whole.add(from_node)

        # Target data-input resolution.
        tgt_data = _data_inputs(tgt_node, caps)
        if len(tgt_data) == 0:
            errors.append(f"{path.name}: edge {fr!r}→{to!r}: target node {to!r} has no data inputs")
            continue
        if len(tgt_data) > 1:
            errors.append(
                f"{path.name}: edge {fr!r}→{to!r}: target node {to!r} has multiple "
                f"data inputs ({tgt_data}); multi-input disambiguation is a "
                f"Phase 1 language-design question (see Technical Note A)"
            )
            continue

        tgt_ast = _try_parse(tgt_data[0], f"input of node {to!r}", path, errors)
        if tgt_ast is None:
            continue

        if src_ast != tgt_ast:
            errors.append(
                f"{path.name}: edge {fr!r}→{to!r}: type mismatch.\n"
                f"      source emits: {unparse(src_ast)}\n"
                f"      target wants: {unparse(tgt_ast)}"
            )

    # Variant-completeness sweep: for every sum-typed output, every
    # declared variant must have at least one consuming edge, unless
    # the whole output is consumed unported (which covers all
    # variants at once).
    for name, n in node_map.items():
        output_ast = _try_parse(n["output"], f"output of node {name!r}", path, errors)
        if output_ast is None:
            continue
        variants = sum_roles(output_ast)
        if not variants or name in consumed_whole:
            continue
        unconsumed = [v for v in variants if v not in consumed_ports[name]]
        for role in unconsumed:
            errors.append(
                f"{path.name}: node {name!r} declares output variant "
                f"{role!r} but no edge consumes it; the variant is dead "
                f"code at the graph level."
            )


def _validate_trust_propagation(
    path: Path,
    node_map: dict[str, dict],
    caps: list[str],
    errors: list[str],
) -> None:
    for n in node_map.values():
        input_asts: list[Type] = []
        for inp in _data_inputs(n, caps):
            ast = _try_parse(inp, f"input of node {n['name']!r}", path, errors)
            if ast is not None:
                input_asts.append(ast)

        output_ast = _try_parse(n["output"], f"output of node {n['name']!r}", path, errors)
        if output_ast is None:
            continue

        has_untrusted_in = any(contains_untrusted(t) for t in input_asts)
        has_untrusted_out = contains_untrusted(output_ast)
        discharges = bool(n.get("discharges_trust", False))

        if has_untrusted_in and not has_untrusted_out and not discharges:
            errors.append(
                f"{path.name}: node {n['name']!r} consumes an `Untrusted<_>` "
                f"input but emits a non-`Untrusted` output without "
                f'`"discharges_trust": true`. Trust discharge must be '
                f"marked explicitly."
            )
        if discharges and not has_untrusted_in:
            errors.append(
                f"{path.name}: node {n['name']!r} declares "
                f"`discharges_trust: true` but has no `Untrusted<_>` input; "
                f"the annotation is unused."
            )


def _validate_layout(
    path: Path,
    node_map: dict[str, dict],
    layout: dict,
    errors: list[str],
) -> None:
    if not isinstance(layout, dict):
        return
    for pn in layout.get("positions", {}):
        if pn not in node_map:
            errors.append(f"{path.name}: layout.positions references unknown node: {pn!r}")
    for zname, z in layout.get("zones", {}).items():
        if not isinstance(z, dict):
            continue
        for zn in z.get("nodes", []):
            if zn not in node_map:
                errors.append(f"{path.name}: layout.zones.{zname} references unknown node: {zn!r}")


# ── Cross-graph check ──────────────────────────────────────────────


def _validate_cross_graph(
    graphs: dict[str, dict],
    graphs_path: dict[str, Path],
    errors: list[str],
) -> None:
    """A node whose name matches another graph's `name` is a sub-graph
    reference. Its input list must satisfy that graph's parameter list
    position-by-position: data inputs must match by equality; capability
    inputs may be provided with at least the authority the sub-graph
    declares (capability narrowing — see `type_parser.is_assignable`)."""
    for gname, g in graphs.items():
        path = graphs_path[gname]
        for n in g["nodes"]:
            ref = n["name"]
            if ref not in graphs or ref == gname:
                continue
            target = graphs[ref]
            provided = n["inputs"]
            expected = target["parameters"]
            target_caps = set(target["capabilities"])

            if len(provided) != len(expected):
                errors.append(
                    f"{path.name}: node {ref!r} is used as a sub-graph but "
                    f"has arity {len(provided)} vs target's {len(expected)}.\n"
                    f"      node inputs:    {provided}\n"
                    f"      target params:  {expected}"
                )
                continue

            mismatches: list[str] = []
            for i, (p, e) in enumerate(zip(provided, expected, strict=True)):
                if p == e:
                    continue
                # Different strings: capability positions may still
                # satisfy via narrowing; data positions must match.
                is_capability_position = e in target_caps
                if not is_capability_position:
                    mismatches.append(
                        f"position {i}: data type {p!r} does not match expected {e!r}"
                    )
                    continue
                try:
                    pa = parse_type(p)
                    ea = parse_type(e)
                except ParseError as pe:
                    mismatches.append(f"position {i}: cannot parse types ({pe})")
                    continue
                if not is_assignable(pa, ea):
                    mismatches.append(
                        f"position {i}: provided capability {p!r} is not "
                        f"assignable to expected {e!r} under the subtyping "
                        f"rules"
                    )

            if mismatches:
                bullet = "\n      - ".join(mismatches)
                errors.append(
                    f"{path.name}: node {ref!r} is used as a sub-graph but "
                    f"its inputs do not satisfy that graph's parameters:\n"
                    f"      - {bullet}"
                )


# ── Public entry point ─────────────────────────────────────────────


def validate_files(files: Iterable[Path]) -> list[str]:
    """Validate a set of graph JSON files. Returns a list of error
    messages; the list is empty iff every graph is valid."""
    errors: list[str] = []
    graphs: dict[str, dict] = {}
    graphs_path: dict[str, Path] = {}

    for f in files:
        try:
            graph = json.loads(f.read_text())
        except json.JSONDecodeError as e:
            errors.append(f"{f.name}: invalid JSON: {e}")
            continue

        if not _validate_structure(graph, f, errors):
            continue

        _validate_semantic(graph, f, errors)
        graphs[graph["name"]] = graph
        graphs_path[graph["name"]] = f

    _validate_cross_graph(graphs, graphs_path, errors)
    return errors
