#!/usr/bin/env python3
"""Validate signal-graph JSON definitions in graphs/.

Three layers of check:
  1. Structural: required fields present, correct types.
  2. Intra-graph: every edge references an existing node, every
     port is a declared variant of its source's output, every
     declared capability is used, layout references only existing
     nodes.
  3. Cross-graph: if a node's name matches another graph's `name`,
     the node's input list must equal that graph's parameter list.
     This is the check that catches sub-graph signature mismatches.

Exits non-zero if any graph has errors. Informal schema lives in
graphs/schema.json for documentation and IDE use; this script does
not consume it (stdlib-only, to keep the pre-commit hook robust).
"""

import json
import re
import sys
from pathlib import Path


NAME_RE = re.compile(r"^[A-Z][A-Za-z0-9]*$")
ERRORS: list[str] = []


def err(path: Path, msg: str) -> None:
    ERRORS.append(f"{path.name}: {msg}")


def parse_variants(output: str) -> list[str]:
    """Parse 'role1: Type1 | role2: Type2' into ['role1', 'role2']."""
    variants = []
    for part in output.split("|"):
        part = part.strip()
        if ":" in part:
            role = part.split(":", 1)[0].strip()
            if role:
                variants.append(role)
    return variants


def validate_structure(graph: dict, path: Path) -> bool:
    """Minimal structural check. Returns True if structure is valid
    enough to proceed to semantic checks."""
    ok = True
    for field in ["name", "parameters", "capabilities", "nodes", "data_edges"]:
        if field not in graph:
            err(path, f"missing required field: {field}")
            ok = False
    if not ok:
        return False

    if not isinstance(graph["name"], str) or not NAME_RE.match(graph["name"]):
        err(path, f"`name` must be PascalCase, got: {graph['name']!r}")
        ok = False
    for f in ["parameters", "capabilities"]:
        v = graph[f]
        if not isinstance(v, list) or not all(isinstance(s, str) and s for s in v):
            err(path, f"`{f}` must be a list of non-empty strings")
            ok = False
    if not isinstance(graph["nodes"], list) or not graph["nodes"]:
        err(path, "`nodes` must be a non-empty list")
        ok = False
    if not isinstance(graph["data_edges"], list):
        err(path, "`data_edges` must be a list")
        ok = False
    return ok


def validate_semantic(graph: dict, path: Path) -> dict[str, dict]:
    """Intra-graph checks. Returns node_map (possibly empty if
    structural errors prevent building it)."""
    params = graph["parameters"]
    caps = graph["capabilities"]
    nodes = graph["nodes"]
    edges = graph["data_edges"]

    # Every capability must be declared as a parameter.
    for c in caps:
        if c not in params:
            err(path, f"capability {c!r} not listed in parameters")

    # Nodes: shape + uniqueness.
    node_map: dict[str, dict] = {}
    for n in nodes:
        if not isinstance(n, dict):
            err(path, f"node must be an object, got: {n!r}")
            continue
        for field in ["name", "inputs", "output"]:
            if field not in n:
                err(path, f"node missing `{field}`: {n}")
                return {}
        nname = n["name"]
        if not isinstance(nname, str) or not NAME_RE.match(nname):
            err(path, f"node name must be PascalCase: {nname!r}")
            continue
        if nname in node_map:
            err(path, f"duplicate node name: {nname!r}")
            continue
        if not isinstance(n["inputs"], list) or not all(
            isinstance(s, str) and s for s in n["inputs"]
        ):
            err(path, f"node {nname!r} `inputs` must be a list of non-empty strings")
            continue
        if not isinstance(n["output"], str) or not n["output"]:
            err(path, f"node {nname!r} `output` must be a non-empty string")
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
            err(path, f"capability {c!r} declared but never used in any node")

    # Every non-capability parameter (data input at the boundary) must
    # be consumed by at least one node.
    data_params = [p for p in params if p not in caps]
    consumed: set[str] = set()
    for n in node_map.values():
        for inp in n["inputs"]:
            if inp in data_params:
                consumed.add(inp)
    for p in data_params:
        if p not in consumed:
            err(path, f"boundary data input {p!r} declared but never consumed")

    # Edges: from/to must reference existing nodes; ports must be valid.
    for e in edges:
        if not isinstance(e, dict) or "from" not in e or "to" not in e:
            err(path, f"edge must be an object with `from` and `to`: {e!r}")
            continue
        fr = e["from"]
        to = e["to"]
        from_node, port = (fr.rsplit(".", 1) + [None])[:2] if "." in fr else (fr, None)

        if from_node not in node_map:
            err(path, f"edge `from` references unknown node: {fr!r}")
            continue
        if to not in node_map:
            err(path, f"edge `to` references unknown node: {to!r}")
            continue

        src_output = node_map[from_node]["output"]
        src_variants = parse_variants(src_output)
        if port is not None:
            if not src_variants:
                err(
                    path,
                    f"edge {fr!r}→{to!r} addresses a port on a node whose "
                    f"output is not a sum type: {src_output!r}",
                )
            elif port not in src_variants:
                err(
                    path,
                    f"edge {fr!r}→{to!r} addresses unknown port {port!r}; "
                    f"variants are: {src_variants}",
                )

    # Layout sanity: positions and zones reference only known nodes.
    layout = graph.get("layout", {})
    if isinstance(layout, dict):
        for pn in layout.get("positions", {}):
            if pn not in node_map:
                err(path, f"layout.positions references unknown node: {pn!r}")
        for zname, z in layout.get("zones", {}).items():
            if not isinstance(z, dict):
                continue
            for zn in z.get("nodes", []):
                if zn not in node_map:
                    err(
                        path,
                        f"layout.zones.{zname} references unknown node: {zn!r}",
                    )

    return node_map


def validate_cross_graph(
    graphs: dict[str, dict], graphs_path: dict[str, Path]
) -> None:
    """If a node's name matches another graph's name, the node's
    input list must equal that graph's parameter list — this is
    what makes the sub-graph signature reusable at the composition
    site."""
    for gname, g in graphs.items():
        path = graphs_path[gname]
        for n in g["nodes"]:
            ref = n["name"]
            if ref in graphs and ref != gname:
                target = graphs[ref]
                if list(n["inputs"]) != list(target["parameters"]):
                    err(
                        path,
                        f"node {ref!r} is used as a sub-graph but its inputs "
                        f"do not match that graph's parameters.\n"
                        f"      node inputs:    {n['inputs']}\n"
                        f"      target params:  {target['parameters']}",
                    )


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    graph_dir = root / "graphs"
    files = sorted(
        p for p in graph_dir.glob("*.json") if p.name != "schema.json"
    )

    if not files:
        print("No graph JSON files found.")
        return 0

    graphs: dict[str, dict] = {}
    graphs_path: dict[str, Path] = {}

    for f in files:
        try:
            graph = json.loads(f.read_text())
        except json.JSONDecodeError as e:
            err(f, f"invalid JSON: {e}")
            continue

        if not validate_structure(graph, f):
            continue

        validate_semantic(graph, f)
        graphs[graph["name"]] = graph
        graphs_path[graph["name"]] = f

    validate_cross_graph(graphs, graphs_path)

    if ERRORS:
        print("Graph validation failed:", file=sys.stderr)
        for e in ERRORS:
            print(f"  {e}", file=sys.stderr)
        return 1

    print(f"Validated {len(files)} graph file(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
