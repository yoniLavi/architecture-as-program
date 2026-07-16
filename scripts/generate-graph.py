#!/usr/bin/env python3
"""Generate pseudocode (.graph) and Fletcher diagram (.typ) from a graph JSON definition.

Usage:
    python3 scripts/generate-graph.py graphs/<name>.json [output-dir]

Outputs (into <output-dir>, default dist/graphs):
    <output-dir>/<name>.graph      — pseudocode for inclusion in proposal
    <output-dir>/<name>.typ        — Fletcher diagram source

The optional output directory lets a frozen paper regenerate its figures into
its own tree (e.g. dist/papers/01-vision/graphs) from its pinned graph JSONs,
so its rendered figures never drift with the shared artifact.
"""

import json
import sys
from pathlib import Path


def load_graph(path):
    with open(path) as f:
        return json.load(f)


def is_capability(input_type, capabilities):
    return input_type in capabilities


def coord(v):
    """Format a coordinate value, avoiding floating-point noise."""
    return int(v) if v == int(v) else round(v, 2)


# ── Pseudocode generation ──────────────────────────────────────────


def generate_pseudocode(g):
    lines = []
    name = g["name"]
    params = g["parameters"]
    nodes = g["nodes"]
    data_edges = g["data_edges"]

    # Graph header with parameter list
    lines.append(f"graph {name}(")
    for i, p in enumerate(params):
        sep = "," if i < len(params) - 1 else ""
        lines.append(f"  {p}{sep}")
    lines.append(") {")

    # Node signatures: data inputs in (...), capabilities in `with`
    caps_set = set(g.get("capabilities", []))

    for node in nodes:
        n = node["name"]
        inputs = node["inputs"]
        output = node["output"]

        data_inputs = [i for i in inputs if i not in caps_set]
        node_caps = [i for i in inputs if i in caps_set]
        identities = node.get("capability_identities", {})

        lines.append(f"  node {n} :")
        if len(data_inputs) <= 2:
            lines.append(f"    ({', '.join(data_inputs)})")
        else:
            lines.append(f"    ({data_inputs[0]},")
            for j in range(1, len(data_inputs)):
                end = ")" if j == len(data_inputs) - 1 else ","
                lines.append(f"     {data_inputs[j]}{end}")
        lines.append(f"    \u2192 {output}")
        if node_caps:
            # A declared capability identity is rendered as `Type @label`, so a
            # distinct instance is visible in the pseudocode and cannot drift from
            # the JSON that generated it.
            rendered_caps = [f"{c} @{identities[c]}" if c in identities else c for c in node_caps]
            lines.append(f"    with {', '.join(rendered_caps)}")
        if node.get("discharges_trust"):
            lines.append("    # discharges trust")
        lines.append("")

    # Data-flow edges only (capability wiring is expressed by `with` clauses)
    lines.append("  // Data flow")
    froms = [e["from"] for e in data_edges]
    pad = max(len(f) for f in froms)
    for e in data_edges:
        lines.append(f"  edge {e['from']:<{pad}} \u2192 {e['to']}")

    lines.append("}")
    return "\n".join(lines)


# ── Fletcher diagram generation ────────────────────────────────────


def esc(s):
    """Escape characters that are special in Typst markup."""
    return s.replace("<", "\\<").replace(">", "\\>").replace("[", "\\[").replace("]", "\\]")


def generate_fletcher(g):
    nodes = g["nodes"]
    caps = g.get("capabilities", g["parameters"])
    data_edges = g["data_edges"]
    layout = g.get("layout", {})
    zones = layout.get("zones", {})
    positions = layout.get("positions", {})
    edge_colors = layout.get("edge_colors", {})
    untrusted_color = layout.get("untrusted_label_color", "#b33")

    node_map = {n["name"]: n for n in nodes}

    L = []

    def emit(s=""):
        L.append(s)

    # Preamble
    emit('#import "@preview/fletcher:0.5.8" as fletcher: diagram, node, edge')
    emit("")
    emit("#set page(width: auto, height: auto, margin: 1.5em)")
    emit('#set text(font: "New Computer Modern", size: 9pt)')
    emit("")
    emit("#let cap(body) = text(size: 7pt, fill: luma(100), body)")
    emit('#let llm-cap(body) = text(size: 7pt, weight: "bold", fill: rgb("#46c"))[#body]')

    # Zone colour definitions
    for zname, z in zones.items():
        emit(f'#let {zname}-color = rgb("{z["color"]}")')
        emit(f'#let {zname}-bg = rgb("{z["background"]}")')
    emit("")

    emit("#diagram(")
    emit("  spacing: (28mm, 15mm),")
    emit("  node-stroke: 0.6pt,")
    emit("  node-inset: 8pt,")
    emit("  edge-stroke: 0.6pt,")
    emit("")

    # ── Trust-zone background regions ──
    for zname, z in zones.items():
        zone_nodes = z["nodes"]
        zone_pos = [positions[n] for n in zone_nodes if n in positions]
        if not zone_pos:
            continue

        min_x = coord(min(p[0] for p in zone_pos) - 0.55)
        min_y = coord(min(p[1] for p in zone_pos) - 0.15)

        coords = [f"({min_x}, {min_y})"] + [
            f"({coord(positions[n][0])}, {coord(positions[n][1])})"
            for n in zone_nodes
            if n in positions
        ]

        emit(f"  // {z['label']} zone")
        emit(f"  node(enclose: ({', '.join(coords)}),")
        emit(f"    stroke: 1pt + {zname}-color,")
        emit(f"    fill: {zname}-bg,")
        emit("    corner-radius: 5pt,")
        emit("    inset: 10pt,")
        emit("    snap: -1,")
        emit(f"    name: <{zname}>),")
        emit("")
        emit(f"  node(({min_x}, {min_y}),")
        emit(f'    text(size: 7pt, weight: "bold", fill: {zname}-color)[{z["label"]}],')
        emit("    stroke: none, inset: 0pt),")
        emit("")

    # ── Nodes ──
    for nd in nodes:
        n = nd["name"]
        pos = positions.get(n, [0, 0])
        node_caps = [i for i in nd["inputs"] if is_capability(i, caps)]
        identities = nd.get("capability_identities", {})

        if node_caps:
            parts = []
            for c in node_caps:
                e = esc(c)
                if c in identities:
                    # `\@` is the Typst escape for a literal @ in markup content.
                    e = f"{e} \\@{esc(identities[c])}"
                if "LLM" in c:
                    parts.append(f"#llm-cap[{e}]")
                else:
                    parts.append(f"#cap[{e}]")
            ann = " \\ ".join(parts)
            emit(f"  node(({coord(pos[0])}, {coord(pos[1])}), align(center)[*{n}*\\ {ann}]),")
        else:
            emit(f"  node(({coord(pos[0])}, {coord(pos[1])}), [*{n}*\\ #cap[(pure)]]),")

    emit("")

    # ── Edges ──
    emit("  // Edges")
    for e in data_edges:
        fr = e["from"]
        to = e["to"]

        # Parse "Node.port" syntax
        if "." in fr:
            from_node, port = fr.rsplit(".", 1)
        else:
            from_node, port = fr, None

        fp = [coord(c) for c in positions.get(from_node, [0, 0])]
        tp = [coord(c) for c in positions.get(to, [0, 0])]

        # Label text: port name for branching edges, output type otherwise
        if port:
            label_text = port
        else:
            src = node_map.get(from_node)
            label_text = src["output"] if src else ""

        label_escaped = esc(label_text)
        # Default label side: flip for left-going diagonal edges so labels
        # don't sit on the line
        default_side = "left" if tp[0] < fp[0] and tp[1] != fp[1] else "right"
        label_side = e.get("label_side", default_side)

        # Colour: from edge_colors for ports, untrusted colour for
        # edges carrying Untrusted<...> data, default otherwise
        color_hex = None
        if port and port in edge_colors:
            color_hex = edge_colors[port]
        elif not port and label_text.startswith("Untrusted<"):
            color_hex = untrusted_color

        if color_hex:
            emit(
                f'  edge(({fp[0]}, {fp[1]}), ({tp[0]}, {tp[1]}), "->",\n'
                f'    label: text(size: 7pt, fill: rgb("{color_hex}"))[{label_escaped}],\n'
                f"    label-side: {label_side}, label-sep: 5pt),"
            )
        else:
            emit(
                f'  edge(({fp[0]}, {fp[1]}), ({tp[0]}, {tp[1]}), "->",\n'
                f"    label: text(size: 7pt)[{label_escaped}],\n"
                f"    label-side: {label_side}, label-sep: 5pt),"
            )

    emit(")")
    return "\n".join(L)


# ── Main ───────────────────────────────────────────────────────────


def main():
    if len(sys.argv) not in (2, 3):
        sys.exit(f"Usage: {sys.argv[0]} <graph.json> [output-dir]")

    json_path = Path(sys.argv[1])
    g = load_graph(json_path)
    stem = json_path.stem

    # Write pseudocode and Fletcher diagram to the output dir (default dist/graphs/).
    out_dir = Path(sys.argv[2]) if len(sys.argv) == 3 else Path("dist/graphs")
    out_dir.mkdir(parents=True, exist_ok=True)

    graph_path = out_dir / f"{stem}.graph"
    graph_path.write_text(generate_pseudocode(g) + "\n")
    print(f"  {graph_path}")

    diagram_path = out_dir / f"{stem}.typ"
    diagram_path.write_text(generate_fletcher(g) + "\n")
    print(f"  {diagram_path}")


if __name__ == "__main__":
    main()
