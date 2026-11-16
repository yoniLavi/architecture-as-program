"""A bound grant, as every review rendering prints it (value-bound grants, task 3.1).

One line, the same in the reviewers' canonical graph, the behaviour view and the
human review page:

    Payments<[any], '2000'> bound payee=in0.iban, amount=in0.total, once; untrusted

The static type, then `bound`, each bound field and its path, the uses, and the
trust label the validator computes (`graph_validator.bind_label`). A `trusted`
label after a *declared* discharge is trusted nominally (design D2), so the line
then names the discharging node, and a reviewer can see what the label rests on.

Stdlib-only; it calls no model.
"""

from __future__ import annotations

from collections.abc import Mapping

from graph_validator import BIND_PATH, bind_label, bind_paths


def _uses(n: object) -> str:
    return "once" if n == 1 else f"{n} uses"


def _dischargers(graph: dict, node: dict, spec: dict) -> list[str]:
    """The declared dischargers feeding an input `spec`'s paths read."""
    positions = {
        int(m.group(1)) for p in bind_paths(spec).values() if (m := BIND_PATH.fullmatch(p))
    }
    nodes = {n["name"]: n for n in graph.get("nodes", [])}
    out = []
    for e in graph.get("data_edges", []):
        src = nodes.get(e["from"].split(".")[0])
        if (
            e["to"] == node["name"]
            and e.get("to_input", 0) in positions
            and src is not None
            and src.get("discharges_trust")
        ):
            out.append(src["name"])
    return sorted(set(out))


def render_bind(graph: dict, node: dict, grant: str, names: Mapping[str, str] | None = None) -> str:
    """`grant`, held by `node`, with its bind and trust label on one line. `names`
    renames nodes (the reviewer's `N1…Nk`)."""
    spec = (node.get("bind") or {}).get(grant)
    if not isinstance(spec, dict):
        return grant
    names = names or {}
    fields = ", ".join(f"{f}={p}" for f, p in bind_paths(spec).items())
    label = bind_label(node, list(graph["capabilities"]), spec)
    if label == "trusted":
        by = [names.get(d, d) for d in _dischargers(graph, node, spec)]
        if by:
            label += f" (as declared: {', '.join(by)} discharges trust)"
    if spec.get("trusted") is True:
        label += ", claimed"
    return f"{grant} bound {fields + ', ' if fields else ''}{_uses(spec.get('uses'))}; {label}"
