"""Signal-graph executor.

Propagates a boundary input value through an `AssembledGraph`. Because the
validator guarantees each node has exactly one data input, execution is a simple
data-driven walk: deliver a value to a node, run its implementation with its
declared capability handles, then route the output along the matching edges
(selecting the variant for sum-typed outputs).

A node whose name resolves to another graph is a **sub-graph node**: its body is
that graph. It is executed by assembling and running the referenced graph as a
nested unit — the same `assemble`, the same `execute` — so composition adds no
second execution model. What the parent routes to that node is exactly what the
sub-graph gets: the handles are supplied to the nested assembly, and since
`execute` holds no backend to provision from, a sub-graph *cannot* mint authority
of its own. Confinement across the boundary is a property of the plumbing rather
than a rule someone has to remember.

The executor records a trace of which nodes ran and what each received, so tests
and the demo can inspect exactly what reached each node — in particular, what the
tool-capable node received as input.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field

from .graph import (
    TIER_GRAPH,
    TIER_SANDBOX,
    AssembledGraph,
    Node,
    assemble,
    graphs_by_name,
)
from .nodes import REGISTRY
from .sandbox.nodes import SANDBOX_REGISTRY
from .values import Variant

# How a sub-graph reference resolves to a graph. Defaults to the canonical graphs
# on disk (by declared name, not filename); tests supply their own.
GraphResolver = Callable[[str], "dict | None"]


@dataclass
class ExecutionResult:
    terminals: dict[str, object] = field(default_factory=dict)
    # node name → the data value it received as input
    received: dict[str, object] = field(default_factory=dict)
    order: list[str] = field(default_factory=list)
    # node name → the enforcement tier that ran it ("host" | "sandbox" | "graph")
    tiers: dict[str, str] = field(default_factory=dict)
    # sub-graph node name → the nested run's own result, so a composed execution
    # can be inspected at both altitudes.
    subgraphs: dict[str, ExecutionResult] = field(default_factory=dict)


class ExecutionError(RuntimeError):
    pass


def _resolver(graphs: GraphResolver | Mapping[str, dict] | None) -> GraphResolver:
    """Normalise the sub-graph lookup: a callable, a name→graph mapping, or the
    canonical graphs on disk.

    The disk index is built once here rather than per node — `load_graph_by_name`
    rescans the directory on each call, which a graph-walk would otherwise pay for
    every node it visits. Nested runs are handed the resolved callable, so a
    composed execution scans once in total."""
    if graphs is None:
        return graphs_by_name().get
    if callable(graphs):
        return graphs
    return graphs.get


def _capability_handles(graph: AssembledGraph, node: Node) -> list[object]:
    """The node's capability handles, in the order they appear in its inputs.

    Resolved through `handle_for`, so a node that declared a distinct capability
    identity at assembly time receives its own instance rather than the
    shared-by-type default."""
    return [graph.handle_for(node, inp) for inp in node.inputs if inp in graph.handles]


def _route_handles(parent: AssembledGraph, node: Node, child: dict) -> dict[str, object]:
    """Bind the handles the parent provisioned for `node` to the child's capability
    parameters, position by position.

    This is routing option (i) of Technical Note A's *hierarchical capability
    routing*: the sub-graph exposes a flat parameter list, the parent matches it by
    position and type, and fan-out to the sub-graph's internal nodes is the
    sub-graph's own business (its `with` clauses). Options (ii) named slots and
    (iii) structural matching remain open.

    Positions are keyed by the *child's* parameter string, not the parent's input
    string: the two can legitimately differ where the parent supplies a handle with
    more authority than the sub-graph asks for (capability narrowing, which the
    cross-graph validator has already checked). The handle itself is resolved
    through `handle_for`, so a parent that declared a distinct identity for this
    node routes *that instance* across the boundary — which is what gives the
    assembly-time identity routing an executable consequence."""
    params = child["parameters"]
    child_caps = set(child["capabilities"])
    if len(node.inputs) != len(params):
        raise ExecutionError(
            f"sub-graph node {node.name!r} has arity {len(node.inputs)} but graph "
            f"{child['name']!r} declares {len(params)} parameters"
        )

    routed: dict[str, object] = {}
    for provided, expected in zip(node.inputs, params, strict=True):
        if expected not in child_caps:
            continue  # the data position; the parent's signal fills it
        if provided not in parent.handles:
            raise ExecutionError(
                f"sub-graph node {node.name!r} must supply a handle for the "
                f"{expected!r} parameter of {child['name']!r}, but its {provided!r} "
                f"input is not a capability of the parent graph"
            )
        routed[expected] = parent.handle_for(node, provided)
    return routed


def _boundary_output(name: str, sub: ExecutionResult) -> object:
    """The single value a sub-graph hands back to its parent.

    Deliberately narrow: exactly one terminal must have been reached. A run ending
    at several terminals — or at terminals of differing type — is the multi-terminal
    *aggregation* question, which this runtime does not answer. Raising here keeps
    that boundary visible instead of silently picking a winner, which would make the
    parent's declared output type a fiction (see Technical Note A, "Sub-graph output
    aggregation")."""
    if len(sub.terminals) != 1:
        reached = ", ".join(sorted(sub.terminals)) or "none"
        raise ExecutionError(
            f"sub-graph {name!r} finished at {len(sub.terminals)} terminals ({reached}); "
            f"a sub-graph node requires exactly one boundary output. Collapsing several "
            f"terminals into one boundary value is multi-terminal aggregation, which the "
            f"runtime does not implement (see Technical Note A)."
        )
    return next(iter(sub.terminals.values()))


def _run_subgraph(
    parent: AssembledGraph,
    node: Node,
    child: dict,
    value: object,
    resolve: GraphResolver,
    stack: tuple[str, ...],
) -> tuple[object, ExecutionResult]:
    """Execute a node whose body is another graph, and lift its output back.

    Note what is *not* passed: no backend, no stores. The child is assembled purely
    from the handles the parent routed, so it can exercise the parent's authority
    and nothing besides."""
    if node.name in stack:
        chain = " → ".join([*stack, node.name])
        raise ExecutionError(
            f"sub-graph {node.name!r} references itself ({chain}); refusing to recurse "
            f"without bound"
        )

    nested = assemble(child, handles=_route_handles(parent, node, child))
    try:
        sub = execute(nested, value, graphs=resolve, _stack=(*stack, node.name))
    except ExecutionError as e:
        # Minimal comprehension aid: name the boundary the failure happened behind,
        # so a parent-level reader is not handed a bare node name from two altitudes
        # down. The richer story (Technical Note A, "Graph-scale comprehension")
        # is deferred.
        raise ExecutionError(f"in sub-graph {node.name!r}: {e}") from e
    return _boundary_output(node.name, sub), sub


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


def execute(
    graph: AssembledGraph,
    boundary_value: object,
    *,
    graphs: GraphResolver | Mapping[str, dict] | None = None,
    _stack: tuple[str, ...] = (),
) -> ExecutionResult:
    """Run the graph from its boundary input. Returns terminal outputs and a
    trace. Branching is handled by following only edges whose port matches the
    variant a node actually emitted.

    A node whose name resolves to a graph is run as a sub-graph (nested assembly +
    run); every other node runs its registered host- or sandbox-tier
    implementation. `graphs` overrides how a reference resolves — a callable or a
    name→graph mapping — and defaults to the canonical graphs on disk. `_stack`
    carries the chain of sub-graphs currently being executed, which is what the
    recursion guard checks."""
    resolve = _resolver(graphs)
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

        result.received[node_name] = value
        result.order.append(node_name)

        # A node whose name resolves to a graph *is* that graph; it needs no
        # registered implementation. Resolution is checked first so composition is
        # decided by the graph, not by whatever happens to be in the registry.
        child = resolve(node_name)
        if child is not None:
            result.tiers[node_name] = TIER_GRAPH
            output, sub = _run_subgraph(graph, node, child, value, resolve, _stack)
            result.subgraphs[node_name] = sub
        else:
            registry = SANDBOX_REGISTRY if node.tier == TIER_SANDBOX else REGISTRY
            impl = registry.get(node_name)
            if impl is None:
                raise ExecutionError(
                    f"no {node.tier}-tier implementation registered for node {node_name!r}"
                )
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
