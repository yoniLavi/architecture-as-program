"""S2 over the repository's graphs. Writes results.json and prints a table.

    cd spikes/specified-architecture && PYTHONPATH=../../scripts:../.. python -m s2.run

Corpus: every graph in `graphs/` with its own contracts, plus the contracts Paper 3's
generation experiment holds node bodies to (`poc/generation/contracts.json`), laid
over the graph they belong to. The overlay is reported as its own corpus, because
those contracts are not in the canonical graph.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from .implication import implies, rebase

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent / "results.json"


def _graphs() -> list[tuple[str, dict]]:
    out = []
    for f in sorted((ROOT / "graphs").glob("*.json")):
        if f.name != "schema.json":
            out.append((f.stem, json.loads(f.read_text())))
    overlay = json.loads((ROOT / "poc/generation/contracts.json").read_text())
    for name, contracts in overlay.items():
        path = ROOT / "graphs" / f"{name}.json"
        if not path.exists():
            continue  # feed-pulse is not a shipped graph
        g = json.loads(path.read_text())
        for n in g["nodes"]:
            n.update(contracts.get(n["name"], {}))
        out.append((f"{name}+generation-contracts", g))
    return out


def edges(graph: dict) -> list[dict]:
    """Each (edge, requires atom) pair, with the verdict."""
    nodes = {n["name"]: n for n in graph["nodes"]}
    into: Counter = Counter(e["to"] for e in graph.get("data_edges", []))
    rows = []
    for e in graph.get("data_edges", []):
        src, _, role = e["from"].partition(".")
        producer, consumer = nodes.get(src), nodes.get(e["to"])
        if producer is None or consumer is None:
            continue
        requires = consumer.get("requires") or []
        ensures = producer.get("ensures") or []
        join = "to_input" in e
        for r in requires:
            if join:
                from .implication import atom

                rb = rebase(atom(r), f"in{e['to_input']}")
                if rb is None:
                    continue  # this atom reads another input
                req = rb.source.replace(f"in{e['to_input']}.", "", 1)
            else:
                req = r
            v = implies(ensures, req)
            rows.append(
                {
                    "edge": f"{e['from']} -> {e['to']}" + (f"[{e['to_input']}]" if join else ""),
                    "variant": role or None,
                    "requires": r,
                    "producer_ensures": ensures,
                    "verdict": v.verdict,
                    "integer_caveat": v.integer_caveat,
                    "fan_in": into[e["to"]],
                }
            )
    return rows


def main() -> None:
    report = {}
    for name, g in _graphs():
        ds = g.get("data_edges", [])
        nodes = {n["name"]: n for n in g["nodes"]}
        both = sum(
            1
            for e in ds
            if (nodes.get(e["from"].split(".")[0]) or {}).get("ensures")
            and (nodes.get(e["to"]) or {}).get("requires")
        )
        rows = edges(g)
        report[name] = {
            "edges": len(ds),
            "edges_with_contracts_on_both_sides": both,
            "edges_into_a_requires": len({r["edge"] for r in rows}),
            "verdicts": dict(Counter(r["verdict"] for r in rows)),
            "rows": rows,
        }
    OUT.write_text(json.dumps(report, indent=2) + "\n")
    for name, r in report.items():
        print(f"{name}: {r['edges']} edges, {r['edges_with_contracts_on_both_sides']} with "
              f"contracts on both sides, verdicts {r['verdicts']}")  # fmt: skip
        for row in r["rows"]:
            print(f"   {row['verdict']:13} {row['edge']:40} requires {row['requires']}")


if __name__ == "__main__":
    main()
