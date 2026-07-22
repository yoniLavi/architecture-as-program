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

import time
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field

from type_parser import TApp, TList, TName, TString, parse_type

from .graph import (
    TIER_GRAPH,
    TIER_SANDBOX,
    AssembledGraph,
    Node,
    assemble,
    graphs_by_name,
)
from .nodes import REGISTRY
from .sandbox.interfaces import UnmappedCapability, interface_for
from .sandbox.nodes import SANDBOX_REGISTRY
from .trace import GraphTrace, NodeTrace, RecordingHandle, TraceCollector, trust_label
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
    # The structured, schema-pinned trace of this run: nodes in execution order,
    # their tiers, trust labels, and capability crossings, with sub-graph runs
    # nested. The machine-readable form of what the fields above expose piecemeal.
    # `execute` always replaces this; the empty default keeps it non-optional for
    # readers (a bare `ExecutionResult()` has an empty, well-formed trace).
    trace: GraphTrace = field(default_factory=lambda: GraphTrace(graph=""))


class ExecutionError(RuntimeError):
    pass


# ── Crossing attribution: interface and instance name for the trace ──────────


def _crossing_interface(cap_type: str) -> str:
    """The interface name a crossing of `cap_type` records.

    The WIT interface where the capability is realised on the confined tier — so a
    host-tier and a confined-tier crossing of the same capability name the *same*
    interface — falling back to the capability type string for a host-only
    capability (append/read-write `DBHandle`) that this tier does not model as WIT."""
    try:
        return interface_for(cap_type)
    except UnmappedCapability:
        return cap_type


def _scope_of(cap_type: str) -> str:
    """The scope baked into a capability type, used to name an instance that carries
    no declared identity: `ResponseChannel<user-session>` → `user-session`,
    `DBHandle<'knowledge-base', read>` → `knowledge-base`, `LLMClient<inference>` →
    `inference`, `LLMClient<[lookup]>` → `lookup`."""
    ast = parse_type(cap_type)
    if isinstance(ast, TApp) and ast.args:
        arg = ast.args[0]
        if isinstance(arg, TString):
            return arg.value
        if isinstance(arg, TName):
            return arg.name
        if isinstance(arg, TList):
            names = sorted(i.name for i in arg.items if isinstance(i, TName))
            if names:
                return "+".join(names)
    return cap_type


def _instance_name(graph: AssembledGraph, node: Node, cap_type: str) -> str:
    """The name a crossing of `cap_type` by `node` records: the graph-declared
    identity label where the node declares one (so identity routing is visible in
    the trace), otherwise the capability's scope."""
    return graph.identities.get(node.name, {}).get(cap_type) or _scope_of(cap_type)


def _wrap(
    handle: object,
    cap_type: str,
    graph: AssembledGraph,
    node: Node,
    collector: TraceCollector,
) -> object:
    """Wrap a handle so its use records a crossing — unless it is already wrapped.

    A handle routed in from a parent graph arrives already wrapped, carrying the
    parent's declared instance label (`customer_session`). Re-wrapping it here would
    re-name that crossing by the child's scope and lose the routing, so an
    already-wrapped handle is passed through untouched."""
    if isinstance(handle, RecordingHandle):
        return handle
    return RecordingHandle(
        handle,
        _crossing_interface(cap_type),
        _instance_name(graph, node, cap_type),
        collector,
    )


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


def _capability_handles(
    graph: AssembledGraph, node: Node, collector: TraceCollector
) -> list[object]:
    """The node's capability handles, in the order they appear in its inputs, each
    wrapped so its use records a crossing against the running node.

    Resolved through `handle_for`, so a node that declared a distinct capability
    identity at assembly time receives its own instance rather than the
    shared-by-type default."""
    return [
        _wrap(graph.handle_for(node, inp), inp, graph, node, collector)
        for inp in node.inputs
        if inp in graph.handles
    ]


def _route_handles(
    parent: AssembledGraph, node: Node, child: dict, collector: TraceCollector
) -> dict[str, object]:
    """Bind the handles the parent provisioned for `node` to the child's capability
    parameters, position by position.

    This is routing option (i) of the research agenda's *hierarchical capability
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
        # Wrap at the routing point, keyed by the *parent's* input and node, so the
        # crossing this handle records inside the child carries the parent's declared
        # instance label (e.g. `customer_session`). The child receives it already
        # wrapped and passes it through, so the label survives the boundary.
        handle = parent.handle_for(node, provided)
        routed[expected] = _wrap(handle, provided, parent, node, collector)
    return routed


def _boundary_output(name: str, sub: ExecutionResult) -> object:
    """The single value a sub-graph hands back to its parent.

    Deliberately narrow: exactly one terminal must have been reached. A run ending
    at several terminals — or at terminals of differing type — is the multi-terminal
    *aggregation* question, which this runtime does not answer. Raising here keeps
    that boundary visible instead of silently picking a winner, which would make the
    parent's declared output type a fiction (see the research agenda, "Sub-graph output
    aggregation")."""
    if len(sub.terminals) != 1:
        reached = ", ".join(sorted(sub.terminals)) or "none"
        raise ExecutionError(
            f"sub-graph {name!r} finished at {len(sub.terminals)} terminals ({reached}); "
            f"a sub-graph node requires exactly one boundary output. Collapsing several "
            f"terminals into one boundary value is multi-terminal aggregation, which the "
            f"runtime does not implement (see the paper's research agenda)."
        )
    return next(iter(sub.terminals.values()))


def _run_subgraph(
    parent: AssembledGraph,
    node: Node,
    child: dict,
    value: object,
    resolve: GraphResolver,
    sandbox: Mapping[str, Iterable[str]] | None,
    stack: tuple[str, ...],
    collector: TraceCollector,
) -> tuple[object, ExecutionResult]:
    """Execute a node whose body is another graph, and lift its output back.

    Note what is *not* passed: no backend, no stores. The child is assembled purely
    from the handles the parent routed, so it can exercise the parent's authority
    and nothing besides — which is why confinement across the boundary holds for
    free, and holds *whichever tier* the child's nodes run on: `sandbox` names which
    of the child's nodes run confined, but supplies no way to provision authority,
    so a confined child node still gets exactly the handles the parent routed."""
    if node.name in stack:
        chain = " → ".join([*stack, node.name])
        raise ExecutionError(
            f"sub-graph {node.name!r} references itself ({chain}); refusing to recurse "
            f"without bound"
        )

    child_sandbox = sandbox.get(child["name"], ()) if sandbox else ()
    nested = assemble(
        child, handles=_route_handles(parent, node, child, collector), sandbox=child_sandbox
    )
    try:
        # Share the collector: the child sets its own current node as it runs, so a
        # crossing inside the child attaches to the child's node, and the routed
        # handles (wrapped above) record into the child's trace, not the parent's.
        sub = execute(
            nested,
            value,
            graphs=resolve,
            sandbox=sandbox,
            _stack=(*stack, node.name),
            _collector=collector,
        )
    except ExecutionError as e:
        # Minimal comprehension aid: name the boundary the failure happened behind,
        # so a parent-level reader is not handed a bare node name from two altitudes
        # down. The richer story (research agenda, "Graph-scale comprehension")
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
    sandbox: Mapping[str, Iterable[str]] | None = None,
    record_timing: bool = False,
    _stack: tuple[str, ...] = (),
    _collector: TraceCollector | None = None,
) -> ExecutionResult:
    """Run the graph from its boundary input. Returns terminal outputs and a
    structured trace (`result.trace`). Branching is handled by following only edges
    whose port matches the variant a node actually emitted.

    `record_timing` populates each node's optional `timing_us`; it is off by
    default so trace structure stays deterministic (timing is excluded from every
    structural comparison and from the schema's required fields).

    A node whose name resolves to a graph is run as a sub-graph (nested assembly +
    run); every other node runs its registered host- or sandbox-tier
    implementation. `graphs` overrides how a reference resolves — a callable or a
    name→graph mapping — and defaults to the canonical graphs on disk.

    `sandbox` makes composition tier-aware: it maps a (sub-)graph's name to the set
    of *its* nodes that run on the confined tier, so a host-tier parent can nest a
    child whose nodes resolve to their own tiers. The parent graph passed here was
    assembled with its own tiers already fixed; this only reaches the children the
    runtime assembles, and it carries no backend, so a confined child node is still
    confined to the handles the parent routed. `_stack` carries the chain of
    sub-graphs currently being executed, which is what the recursion guard checks."""
    resolve = _resolver(graphs)
    # One collector is shared across a whole nested execution; a top-level run mints
    # it, a sub-graph run inherits the parent's so crossings land in the right node.
    collector = _collector if _collector is not None else TraceCollector()
    result = ExecutionResult()
    trace = GraphTrace(graph=graph.name)
    result.trace = trace
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

        # Open this node's trace entry and make it the collector's current node, so
        # any capability crossing during its run is attributed here.
        entry = NodeTrace(node=node_name, tier="", input_trust=trust_label(value))
        trace.nodes.append(entry)
        collector.current = entry
        started = time.perf_counter() if record_timing else 0.0

        # A node whose name resolves to a graph *is* that graph; it needs no
        # registered implementation. Resolution is checked first so composition is
        # decided by the graph, not by whatever happens to be in the registry.
        child = resolve(node_name)
        if child is not None:
            entry.tier = result.tiers[node_name] = TIER_GRAPH
            output, sub = _run_subgraph(
                graph, node, child, value, resolve, sandbox, _stack, collector
            )
            result.subgraphs[node_name] = sub
            entry.subgraph = sub.trace
        else:
            registry = SANDBOX_REGISTRY if node.tier == TIER_SANDBOX else REGISTRY
            impl = registry.get(node_name)
            if impl is None:
                raise ExecutionError(
                    f"no {node.tier}-tier implementation registered for node {node_name!r}"
                )
            entry.tier = result.tiers[node_name] = node.tier
            output = impl(value, *_capability_handles(graph, node, collector))

        entry.output_trust = trust_label(output)
        if record_timing:
            entry.timing_us = (time.perf_counter() - started) * 1_000_000.0

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
