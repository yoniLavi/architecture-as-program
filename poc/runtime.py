"""Signal-graph executor.

Propagates a boundary input value through an `AssembledGraph`. Execution is a
data-driven walk: deliver a value to a node, run its implementation with its
declared capability handles, then route the output along the matching edges
(selecting the variant for sum-typed outputs).

Fan-in exists in two restricted forms, and no others. A **join** is a node with
several data inputs, each fed by exactly one edge naming its position; it runs
once, when every position holds a value, and receives them by position. A
**per-item map** is a sub-graph node declaring `each`: the sub-graph is run once
per element of a list, each element in its own isolated run. What is still
refused is a second arrival at one input — merging streams, where the result
would depend on arrival order.

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
from types import SimpleNamespace

from type_parser import TApp, TList, TName, TString, parse_type

from . import contracts
from .graph import (
    TIER_GRAPH,
    TIER_SANDBOX,
    AssembledGraph,
    AssemblyError,
    Node,
    assemble,
    graphs_by_name,
    validate_graph_dicts,
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
    # per-item node name → one nested result per list element, in list order.
    elements: dict[str, list[ExecutionResult]] = field(default_factory=dict)
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
            # A tool list holds names; an HTTP allowlist holds string literals.
            names = sorted(
                i.name if isinstance(i, TName) else i.value
                for i in arg.items
                if isinstance(i, TName | TString)
            )
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
    cross-graph validator has already checked at assembly). The wider handle is
    routed as is, *not* attenuated to the child's declared scope: narrowing is
    checked, not enforced. The handle itself is resolved
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
    acting_as: tuple[str, ...] = (),
) -> tuple[object, ExecutionResult]:
    """Execute a node whose body is another graph, and lift its output back.

    Note what is *not* passed: no backend, no stores. The child is assembled purely
    from the handles the parent routed, so it can exercise the parent's authority
    and nothing besides — which is why confinement across the boundary holds for
    free, and holds *whichever tier* the child's nodes run on: `sandbox` names which
    of the child's nodes run confined, but supplies no way to provision authority,
    so a confined child node still gets exactly the handles the parent routed."""
    _check_composition(parent, node, child, stack)
    return _run_child(parent, node, child, value, resolve, sandbox, stack, collector, acting_as)


def _check_composition(
    parent: AssembledGraph, node: Node, child: dict, stack: tuple[str, ...]
) -> None:
    """Refuse a composition the cross-graph analyses reject, before running it."""
    if node.name in stack:
        chain = " → ".join([*stack, node.name])
        raise ExecutionError(
            f"sub-graph {node.name!r} references itself ({chain}); refusing to recurse "
            f"without bound"
        )

    # Assembly checked the parent against the canonical graphs; a caller may resolve
    # sub-graphs through its own mapping, so check the parent against the child
    # actually resolved before running it. The runtime must not execute a
    # composition the cross-graph analyses reject, whoever supplied the child.
    if child.get("name") != node.name:
        # The validator resolves a sub-graph by name; a child under another name
        # would be checked against nothing (or against the parent itself).
        raise AssemblyError(
            [
                f"sub-graph node {node.name!r} resolved to a graph named "
                f"{child.get('name')!r}; a sub-graph must carry its node's name"
            ]
        )
    if parent.source:
        errors = validate_graph_dicts([parent.source, child])
        if errors:
            raise AssemblyError(errors)


def _run_child(
    parent: AssembledGraph,
    node: Node,
    child: dict,
    value: object,
    resolve: GraphResolver,
    sandbox: Mapping[str, Iterable[str]] | None,
    stack: tuple[str, ...],
    collector: TraceCollector,
    acting_as: tuple[str, ...] = (),
) -> tuple[object, ExecutionResult]:
    """One nested assembly and run of `child` on `value`: the whole of what a
    sub-graph node does, and one element's worth of what a per-item node does."""
    child_sandbox = sandbox.get(child["name"], ()) if sandbox else ()
    # The principal crosses the composition boundary with the routed handles: a
    # sub-graph acts on behalf of whoever the parent is acting for, and — like the
    # handles themselves — cannot widen it, because the child is assembled with the
    # parent's principal rather than provisioning one of its own.
    nested = assemble(
        child,
        handles=_route_handles(parent, node, child, collector),
        sandbox=child_sandbox,
        principal=parent.principal,
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
            _acting_as=acting_as,
        )
    except ExecutionError as e:
        # Minimal comprehension aid: name the boundary the failure happened behind,
        # so a parent-level reader is not handed a bare node name from two altitudes
        # down. The richer story (research agenda, "Graph-scale comprehension")
        # is deferred.
        raise ExecutionError(f"in sub-graph {node.name!r}: {e}") from e
    return _boundary_output(node.name, sub), sub


def _run_each(
    parent: AssembledGraph,
    node: Node,
    child: dict,
    values: object,
    resolve: GraphResolver,
    sandbox: Mapping[str, Iterable[str]] | None,
    stack: tuple[str, ...],
    collector: TraceCollector,
    acting_as: tuple[str, ...] = (),
) -> tuple[tuple[object, ...], list[ExecutionResult]]:
    """The per-item map: run the sub-graph once per element, each in its own run.

    Isolation is the point, and it is structural. Each element gets a fresh
    assembly of the child and its own execution; the child receives one element
    as its boundary input and nothing else, so no node inside it can be handed a
    second. What an instruction hidden in one feed item can reach is therefore
    that item — there is no wiring by which it could see the others. (The child
    runs do share the handles the parent routed: one model client, by design. They
    share no *data*.)

    Elements run in list order and results are collected in that order. A failing
    element fails the whole node, naming its index, and no partial list is
    emitted: a list one short would silently misalign with whatever consumes it."""
    if not isinstance(values, list | tuple):
        raise ExecutionError(
            f"per-item node {node.name!r} expects a list, got {type(values).__name__}"
        )
    _check_composition(parent, node, child, stack)
    outputs: list[object] = []
    runs: list[ExecutionResult] = []
    for index, element in enumerate(values):
        try:
            output, sub = _run_child(
                parent, node, child, element, resolve, sandbox, stack, collector, acting_as
            )
        except Exception as e:
            raise ExecutionError(
                f"element {index} of per-item node {node.name!r} failed: {e}"
            ) from e
        outputs.append(output)
        runs.append(sub)
    return tuple(outputs), runs


def _schedule_rank(graph: AssembledGraph) -> dict[str, tuple[int, str]]:
    """A fixed order to run ready nodes in: by depth (the longest path from the
    entry), then by name.

    With fan-out, several nodes can be ready at once, and which the worklist
    happened to hold first would otherwise depend on the order edges were listed
    in. Ranking by a property of the graph's shape makes a run's order — and so
    its trace — the same however the JSON is arranged, which is what lets a join
    be described as commutative: its inputs are delivered by position, and nothing
    else about the run moves with their arrival order either."""
    predecessors: dict[str, list[str]] = {n: [] for n in graph.nodes}
    for e in graph.edges:
        predecessors[e.dst_node].append(e.src_node)
    depth: dict[str, int] = {}

    def of(name: str, visiting: frozenset[str]) -> int:
        if name not in depth:
            if name in visiting:  # unreachable: validation rejects a cycle
                return 0
            sources = predecessors[name]
            depth[name] = 1 + max((of(s, visiting | {name}) for s in sources), default=-1)
        return depth[name]

    return {name: (of(name, frozenset()), name) for name in graph.nodes}


def _entry_node(graph: AssembledGraph) -> Node:
    """The graph's one entry: the node no edge reaches, which takes the boundary
    data parameter. Chosen by the edges, never by file order, which once let a
    validated gate listed after the node it guards be skipped."""
    data_params = [p for p in graph.parameters if p not in graph.capabilities]
    if len(data_params) != 1:
        raise ExecutionError(f"expected exactly one boundary data parameter, got {data_params}")
    boundary = data_params[0]
    targets = {e.dst_node for e in graph.edges}
    entries = [n for name, n in graph.nodes.items() if name not in targets]
    if len(entries) != 1:
        raise ExecutionError(
            f"expected exactly one entry node, got {sorted(n.name for n in entries)}"
        )
    if graph.data_input_type(entries[0]) != boundary:
        raise ExecutionError(
            f"entry node {entries[0].name!r} does not consume boundary input {boundary!r}"
        )
    return entries[0]


def execute(
    graph: AssembledGraph,
    boundary_value: object,
    *,
    graphs: GraphResolver | Mapping[str, dict] | None = None,
    sandbox: Mapping[str, Iterable[str]] | None = None,
    record_timing: bool = False,
    _stack: tuple[str, ...] = (),
    _collector: TraceCollector | None = None,
    _acting_as: tuple[str, ...] = (),
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
    # Each item carries the delegation chain in force for that node: a binder
    # extends the chain for everything downstream of itself, and the chain travels
    # with the value rather than being a single cursor, so two branches descending
    # from different binders cannot pick up each other's delegates.
    # An item is (node, input position, value, chain): one value arriving at one
    # of a node's data inputs.
    pending: list[tuple[str, int, object, tuple[str, ...]]] = [
        (_entry_node(graph).name, 0, boundary_value, tuple(_acting_as))
    ]
    rank = _schedule_rank(graph)
    # Joins part-way to firing: node → position → (value, chain).
    waiting: dict[str, dict[int, tuple[object, tuple[str, ...]]]] = {}

    # Precompute outgoing edges per source node.
    out_edges: dict[str, list] = {n: [] for n in graph.nodes}
    for e in graph.edges:
        out_edges[e.src_node].append(e)

    while pending:
        # The ready item of lowest rank, not the oldest: see `_schedule_rank`.
        pending.sort(key=lambda item: (rank[item[0]], item[1]))
        node_name, position, value, acting_as = pending.pop(0)
        if node_name in result.received:
            # Each node runs once per run. A second arrival at a position is a
            # *merge* of streams — the order-sensitive fan-in this model does not
            # address — so it is refused rather than run again.
            raise ExecutionError(
                f"node {node_name!r} would run a second time; merging several "
                f"arrivals at one input is unaddressed, so a run reaching a node "
                f"twice is refused"
            )
        node = graph.nodes[node_name]

        # A join holds each arriving value until every position has one, then runs
        # once on all of them, delivered by position. Nothing about the result
        # depends on which arrived first.
        arity = len(graph.data_inputs(node))
        is_join = arity > 1
        if is_join:
            held = waiting.setdefault(node_name, {})
            if position in held:
                raise ExecutionError(
                    f"join {node_name!r} received a second value at position {position}; "
                    f"each position of a join takes exactly one"
                )
            held[position] = (value, acting_as)
            if len(held) < arity:
                continue
            del waiting[node_name]
            value = tuple(held[i][0] for i in range(arity))
            # The join acts for everyone its inputs were acting for.
            acting_as = tuple(dict.fromkeys(d for i in range(arity) for d in held[i][1]))

        result.received[node_name] = value
        result.order.append(node_name)

        # Open this node's trace entry and make it the collector's current node, so
        # any capability crossing during its run is attributed here.
        # The principal this node acts on behalf of, and the chain of delegates
        # acting for it. The principal is bound once at assembly and never widened
        # here; only a node declaring `binds_principal` extends the chain, and it
        # extends it for the work *downstream* of itself, which is what makes the
        # hop auditable rather than ambient.
        entry = NodeTrace(
            node=node_name,
            tier="",
            input_trust=trust_label(value),
            principal=graph.principal,
            acting_as=list(acting_as),
        )
        trace.nodes.append(entry)
        collector.current = entry
        started = time.perf_counter() if record_timing else 0.0

        # Contracts bracket the body: preconditions before, postconditions after,
        # each carrying blame so a violation names the side that broke the
        # agreement rather than only the fact of breakage. The precondition is
        # checked before either branch, so a sub-graph node's `requires` is
        # evaluated exactly as a leaf's is.
        # A join's precondition reads its inputs by position: `in0.field`, `in1.field`.
        subject = (
            SimpleNamespace(**{f"in{i}": v for i, v in enumerate(value)})  # type: ignore[arg-type]
            if is_join
            else value
        )
        contracts.check(node.requires, subject, node=node_name, kind="requires")

        # A node whose name resolves to a graph *is* that graph; it needs no
        # registered implementation. Resolution is checked first so composition is
        # decided by the graph, not by whatever happens to be in the registry.
        child = resolve(node_name)
        if node.each:
            # A per-item node is a sub-graph by definition. Refusing a leaf here is
            # what keeps `each` from becoming a way to hand one body a whole list
            # while the graph claims per-element isolation.
            if child is None:
                raise ExecutionError(
                    f"per-item node {node_name!r} names no graph; `each` applies a "
                    f"sub-graph to each element and has no meaning on a leaf"
                )
            entry.tier = result.tiers[node_name] = TIER_GRAPH
            output, runs = _run_each(
                graph, node, child, value, resolve, sandbox, _stack, collector, acting_as
            )
            result.elements[node_name] = runs
            entry.elements = [run.trace for run in runs]
            # The child runs moved the collector's cursor; nothing else this node
            # does crosses a capability, so there is nothing to restore it for.
        elif child is not None:
            entry.tier = result.tiers[node_name] = TIER_GRAPH
            output, sub = _run_subgraph(
                graph, node, child, value, resolve, sandbox, _stack, collector, acting_as
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
            data = value if is_join else (value,)
            output = impl(*data, *_capability_handles(graph, node, collector))  # type: ignore[misc]

        # Postconditions see the value the node actually emitted. A Variant is
        # checked on its payload, so a contract talks about the value that flows
        # rather than about the routing wrapper around it.
        contracts.check(
            node.ensures,
            output.value if isinstance(output, Variant) else output,
            node=node_name,
            kind="ensures",
        )

        entry.output_trust = trust_label(output)
        if record_timing:
            entry.timing_us = (time.perf_counter() - started) * 1_000_000.0

        edges = out_edges[node_name]
        if not edges:
            result.terminals[node_name] = output
            continue

        # Route. For a Variant output, follow only the matching-port edge(s);
        # for a plain output, follow the unported edge(s).
        # A binder is a delegate for everything downstream of it: it acts on the
        # principal's behalf, and says so in the graph rather than in its body.
        downstream = (*acting_as, node_name) if node.binds_principal else acting_as
        routed = False
        for e in edges:
            if isinstance(output, Variant):
                if e.src_port == output.role:
                    pending.append((e.dst_node, e.dst_input, output.value, downstream))
                    routed = True
            else:
                if e.src_port is None:
                    pending.append((e.dst_node, e.dst_input, output, downstream))
                    routed = True
        # A node with out-edges is not a terminal, so a value no edge carries would
        # vanish with no error. Validation should make this unreachable; refusing it
        # here means a gap in validation fails loudly instead of silently.
        if not routed:
            role = output.role if isinstance(output, Variant) else None
            raise ExecutionError(
                f"node {node_name!r} emitted {'variant ' + repr(role) if role else 'a value'} "
                f"that no edge carries"
            )

    # A join still holding a value has an input that never came: one of its
    # positions sits on a branch this run did not take. The value it holds would
    # be dropped without a word, so the run is refused instead. (Validation
    # rejects the join that can *never* fire; this catches the one that did not.)
    if waiting:
        stuck = ", ".join(
            f"{name!r} (holding position(s) {sorted(held)})"
            for name, held in sorted(waiting.items())
        )
        raise ExecutionError(f"the run ended with a join still waiting: {stuck}")

    return result
