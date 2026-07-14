"""Signal-graph executor.

Propagates a boundary input value through an `AssembledGraph`. Because the
validator guarantees each node has exactly one data input, execution is a simple
data-driven walk: deliver a value to a node, run its implementation with its
declared capability handles, then route the output along the matching edges
(selecting the variant for sum-typed outputs).

The executor records a trace of which nodes ran and what each received, so tests
and the demo can inspect exactly what reached each node — in particular, what the
tool-capable node received as input.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .graph import TIER_SANDBOX, AssembledGraph, Node
from .nodes import REGISTRY
from .sandbox.nodes import SANDBOX_REGISTRY
from .values import Variant


@dataclass
class ExecutionResult:
    terminals: dict[str, object] = field(default_factory=dict)
    # node name → the data value it received as input
    received: dict[str, object] = field(default_factory=dict)
    order: list[str] = field(default_factory=list)
    # node name → the enforcement tier that ran it ("host" | "sandbox")
    tiers: dict[str, str] = field(default_factory=dict)


class ExecutionError(RuntimeError):
    pass


def _capability_handles(graph: AssembledGraph, node: Node) -> list[object]:
    """The node's capability handles, in the order they appear in its inputs."""
    return [graph.handles[inp] for inp in node.inputs if inp in graph.handles]


def _entry_node(graph: AssembledGraph) -> Node:
    """The node that consumes the graph's boundary data parameter."""
    data_params = [p for p in graph.parameters if p not in graph.capabilities]
    if len(data_params) != 1:
        raise ExecutionError(f"expected exactly one boundary data parameter, got {data_params}")
    boundary = data_params[0]
    for node in graph.nodes.values():
        if graph.data_input_type(node) == boundary:
            return node
    raise ExecutionError(f"no node consumes boundary input {boundary!r}")


def execute(graph: AssembledGraph, boundary_value: object) -> ExecutionResult:
    """Run the graph from its boundary input. Returns terminal outputs and a
    trace. Branching is handled by following only edges whose port matches the
    variant a node actually emitted."""
    result = ExecutionResult()
    # Worklist of (node_name, input_value) pairs ready to run.
    pending: list[tuple[str, object]] = [(_entry_node(graph).name, boundary_value)]

    # Precompute outgoing edges per source node.
    out_edges: dict[str, list] = {n: [] for n in graph.nodes}
    for e in graph.edges:
        out_edges[e.src_node].append(e)

    while pending:
        node_name, value = pending.pop(0)
        node = graph.nodes[node_name]
        registry = SANDBOX_REGISTRY if node.tier == TIER_SANDBOX else REGISTRY
        impl = registry.get(node_name)
        if impl is None:
            raise ExecutionError(
                f"no {node.tier}-tier implementation registered for node {node_name!r}"
            )

        result.received[node_name] = value
        result.order.append(node_name)
        result.tiers[node_name] = node.tier

        output = impl(value, *_capability_handles(graph, node))

        edges = out_edges[node_name]
        if not edges:
            result.terminals[node_name] = output
            continue

        # Route. For a Variant output, follow only the matching-port edge(s);
        # for a plain output, follow the unported edge(s).
        for e in edges:
            if isinstance(output, Variant):
                if e.src_port == output.role:
                    pending.append((e.dst_node, output.value))
            else:
                if e.src_port is None:
                    pending.append((e.dst_node, output))

    return result
