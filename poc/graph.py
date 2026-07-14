"""Load a canonical signal-graph JSON, gate assembly through the existing
validator, and provision capability handles.

The "reject unsafe wiring at assembly time" guarantee is delegated to the
project's `graph_validator` — the runtime does not re-implement type checking. A
graph (or a hand-built unsafe variant of one) is assembled only if the validator
reports zero errors.
"""

from __future__ import annotations

import json
import tempfile
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path

from graph_validator import validate_files

from .handles import provision
from .llm import LLMBackend

REPO_ROOT = Path(__file__).resolve().parent.parent
GRAPHS_DIR = REPO_ROOT / "graphs"


class AssemblyError(RuntimeError):
    """Raised when a graph fails validation and therefore cannot be assembled.
    Carries the validator's error messages."""

    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("graph failed validation:\n  " + "\n  ".join(errors))


# Enforcement tiers a node may run on. `host` is the default host-discipline
# tier; `sandbox` runs the node body as a confined WASM module (see poc/sandbox).
TIER_HOST = "host"
TIER_SANDBOX = "sandbox"


@dataclass
class Node:
    name: str
    inputs: list[str]
    output: str
    discharges_trust: bool
    tier: str = field(default=TIER_HOST)


@dataclass
class Edge:
    src_node: str
    src_port: str | None  # variant role, or None for the whole output
    dst_node: str


@dataclass
class AssembledGraph:
    name: str
    parameters: list[str]
    capabilities: list[str]
    nodes: dict[str, Node]
    edges: list[Edge]
    handles: dict[str, object]  # capability type string → handle instance

    def handles_for(self, node: Node) -> dict[str, object]:
        """The capability handles a node declares, keyed by capability type."""
        return {inp: self.handles[inp] for inp in node.inputs if inp in self.handles}

    def data_input_type(self, node: Node) -> str | None:
        """The single non-capability input type of a node (or None for a source
        node with only a boundary/parameter input)."""
        data = [inp for inp in node.inputs if inp not in self.capabilities]
        return data[0] if data else None


def validate_graph_dict(graph: dict) -> list[str]:
    """Run the project validator over an in-memory graph dict. Returns the list
    of validation errors (empty == valid)."""
    with tempfile.TemporaryDirectory() as td:
        # Name the temp file after the graph so validator messages read naturally.
        p = Path(td) / f"{graph.get('name', 'graph')}.json"
        p.write_text(json.dumps(graph))
        return validate_files([p])


def load_graph_dict(name_or_path: str | Path) -> dict:
    """Load a graph JSON by canonical name (e.g. 'customer-support') or path."""
    path = Path(name_or_path)
    if not path.exists():
        path = GRAPHS_DIR / f"{name_or_path}.json"
    return json.loads(path.read_text())


def assemble(
    graph: dict,
    *,
    backend: LLMBackend,
    stores: Mapping[str, Mapping[str, list[str]]] | None = None,
    sandbox: Iterable[str] = (),
) -> AssembledGraph:
    """Validate and assemble a graph dict into a runnable `AssembledGraph`.

    Raises `AssemblyError` if validation fails — this is the assembly-time
    rejection of unsafe wiring.

    `sandbox` names the nodes to run on the confined WASM tier; every other node
    runs on the host tier. The two tiers compose in one graph, which is the
    proposal's incremental-migration path (opaque host node → confined node)."""
    errors = validate_graph_dict(graph)
    if errors:
        raise AssemblyError(errors)

    sandbox_nodes = set(sandbox)
    stores = stores or {}
    nodes = {
        n["name"]: Node(
            name=n["name"],
            inputs=list(n["inputs"]),
            output=n["output"],
            discharges_trust=bool(n.get("discharges_trust", False)),
            tier=TIER_SANDBOX if n["name"] in sandbox_nodes else TIER_HOST,
        )
        for n in graph["nodes"]
    }
    unknown = sandbox_nodes - set(nodes)
    if unknown:
        raise AssemblyError([f"unknown node(s) requested for sandbox tier: {sorted(unknown)}"])

    edges: list[Edge] = []
    for e in graph["data_edges"]:
        fr = e["from"]
        if "." in fr:
            src_node, src_port = fr.rsplit(".", 1)
        else:
            src_node, src_port = fr, None
        edges.append(Edge(src_node=src_node, src_port=src_port, dst_node=e["to"]))

    handles: dict[str, object] = {
        cap: provision(cap, backend=backend, stores=stores) for cap in graph["capabilities"]
    }

    return AssembledGraph(
        name=graph["name"],
        parameters=list(graph["parameters"]),
        capabilities=list(graph["capabilities"]),
        nodes=nodes,
        edges=edges,
        handles=handles,
    )
