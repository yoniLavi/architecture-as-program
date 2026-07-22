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

from .handles import Revoker, Rotator, manage, provision
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

# Not an enforcement tier, and reported separately for that reason: a sub-graph
# node's body is another graph, so no tier "runs" it. Its internal nodes each
# report their own tier in the nested result. Calling this "host" would claim a
# confinement story for a node that has none of its own.
TIER_GRAPH = "graph"


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
    handles: dict[str, object]  # capability type string → default (shared-by-type) instance
    # (node name, capability type) → the instance that node binds, present only
    # where the node declares a distinct capability *identity*. Absent means the
    # node falls back to the shared-by-type instance in `handles` — the type-only
    # default that keeps identity-agnostic graphs behaving exactly as before.
    instances: dict[tuple[str, str], object] = field(default_factory=dict)
    # (capability type, identity label) → the authority to sever that instance's
    # caretaker at runtime. Present only for instances declared revocable at
    # assembly; the host holds this map, nodes never do. Exposed directly so a
    # single revoker can also be handed off as a passable ocap token (the
    # true-ocap alternative to the `revoke(...)` convenience method below).
    revokers: dict[tuple[str, str], Revoker] = field(default_factory=dict)
    # (capability type, identity label) → the authority to re-point that instance's
    # caretaker at a new backing handle. Present only for instances declared
    # rotatable; host-held like `revokers`, and granted independently of it (an
    # instance may be revocable, rotatable, both, or neither).
    rotators: dict[tuple[str, str], Rotator] = field(default_factory=dict)
    # node name → {capability type → declared identity label}. The merged identity
    # map (graph JSON plus any `identities=` override), kept so the execution trace
    # can name a crossing by the identity the graph declared (`customer_session`)
    # rather than only by the capability's scope. A node/capability absent here has
    # no declared identity and is named by scope.
    identities: dict[str, dict[str, str]] = field(default_factory=dict)

    def revoke(self, cap_type: str, identity: str) -> None:
        """Sever the named revocable capability instance. Afterwards every node
        bound to `(cap_type, identity)` fails with `RevokedCapabilityError` on its
        next use; siblings of the same type are untouched. Idempotent.

        This method *is* the separation between using and administering authority:
        it lives on the assembled graph, which the host holds and no node receives.
        Raises `KeyError` if that instance was not provisioned revocable —
        revocation is opt-in, so only declared-revocable instances can be severed."""
        try:
            self.revokers[(cap_type, identity)].revoke()
        except KeyError:
            raise KeyError(
                f"no revocable instance {(cap_type, identity)!r}; "
                f"revocable instances are {sorted(self.revokers)}"
            ) from None

    def rotate(self, cap_type: str, identity: str, new_handle: object) -> None:
        """Re-point the named rotatable capability instance at `new_handle`.
        Afterwards every node bound to `(cap_type, identity)` is served by the new
        handle on its next use; siblings of the same type are untouched.

        The replacement must be the same capability kind as the current target
        (a `ResponseChannel` rotates to a `ResponseChannel`, never to a `DBHandle`),
        so the surface a node holds cannot change kind underneath it — `Rotator`
        raises `CapabilityError` otherwise. Like `revoke`, this is a host authority
        no node receives. Raises `KeyError` if the instance was not provisioned
        rotatable — rotation is opt-in."""
        try:
            rotator = self.rotators[(cap_type, identity)]
        except KeyError:
            raise KeyError(
                f"no rotatable instance {(cap_type, identity)!r}; "
                f"rotatable instances are {sorted(self.rotators)}"
            ) from None
        rotator.rotate(new_handle)

    def handle_for(self, node: Node, cap_type: str) -> object:
        """The handle instance `node` binds for capability `cap_type`.

        When the node declared an identity for that capability at assembly time,
        this is its distinct per-identity instance; otherwise it is the
        shared-by-type default. This one method is where capability *identity*
        (per named instance) resolves ahead of capability *type* (shared)."""
        return self.instances.get((node.name, cap_type), self.handles[cap_type])

    def handles_for(self, node: Node) -> dict[str, object]:
        """The capability handles a node declares, keyed by capability type."""
        return {inp: self.handle_for(node, inp) for inp in node.inputs if inp in self.handles}

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


def validate_graph_dicts(graphs: list[dict]) -> list[str]:
    """Validate several in-memory graphs *together*, so the cross-graph checks
    (a sub-graph node's inputs and output against the referenced graph) fire.

    `validate_graph_dict` validates one graph in isolation, where a sub-graph
    reference resolves to nothing and the cross-graph layer is silent. A composition
    mistake — a sub-graph node misdescribing its boundary output — is only visible
    when the referenced graph is in the same batch, which is what this provides."""
    with tempfile.TemporaryDirectory() as td:
        paths = []
        for g in graphs:
            p = Path(td) / f"{g.get('name', 'graph')}.json"
            p.write_text(json.dumps(g))
            paths.append(p)
        return validate_files(paths)


def load_graph_dict(name_or_path: str | Path) -> dict:
    """Load a graph JSON by canonical name (e.g. 'customer-support') or path."""
    path = Path(name_or_path)
    if not path.exists():
        path = GRAPHS_DIR / f"{name_or_path}.json"
    return json.loads(path.read_text())


def graphs_by_name() -> dict[str, dict]:
    """Every canonical graph, indexed by its declared `name`.

    Note the indirection: a graph's *name* (`CustomerSupport`) is not its
    *filename* (`customer-support.json`), so a sub-graph reference — which names a
    graph, not a file — cannot be resolved by `load_graph_dict`. This is the same
    name-keyed index the cross-graph validator builds to check those references,
    which is why it resolves the same set."""
    index: dict[str, dict] = {}
    for path in sorted(GRAPHS_DIR.glob("*.json")):
        if path.name == "schema.json":
            continue
        graph = json.loads(path.read_text())
        index[graph["name"]] = graph
    return index


def load_graph_by_name(name: str) -> dict | None:
    """The canonical graph declaring `name`, or None if no graph does.

    None is the answer to "is this node a sub-graph reference?" — an ordinary node
    simply names no graph."""
    return graphs_by_name().get(name)


def _merge_identities(
    graph_nodes: list[dict],
    argument: Mapping[str, Mapping[str, str]] | None,
) -> dict[str, dict[str, str]]:
    """Combine graph-declared capability identities with the `identities=`
    argument. The graph JSON is the base — each node's `capability_identities`
    map — and the argument overrides it at the `(node, capability type)`
    granularity: the argument wins where both name an identity for the same slot,
    the graph declaration applies everywhere else. Overriding one slot therefore
    never drops a node's other graph-declared identities. The merged map is
    validated downstream by the same rule the runtime already enforced on the
    argument, so a graph-declared identity for an unheld capability is rejected at
    assembly exactly as an argument one is (and at validation time too)."""
    merged: dict[str, dict[str, str]] = {
        n["name"]: dict(n["capability_identities"])
        for n in graph_nodes
        if n.get("capability_identities")
    }
    for node_name, per_cap in (argument or {}).items():
        merged.setdefault(node_name, {}).update(per_cap)
    return merged


def assemble(
    graph: dict,
    *,
    backend: LLMBackend | None = None,
    stores: Mapping[str, Mapping[str, list[str]]] | None = None,
    sandbox: Iterable[str] = (),
    identities: Mapping[str, Mapping[str, str]] | None = None,
    revocable_instances: Iterable[tuple[str, str]] = (),
    rotatable_instances: Iterable[tuple[str, str]] = (),
    handles: Mapping[str, object] | None = None,
) -> AssembledGraph:
    """Validate and assemble a graph dict into a runnable `AssembledGraph`.

    Raises `AssemblyError` if validation fails — this is the assembly-time
    rejection of unsafe wiring.

    `sandbox` names the nodes to run on the confined WASM tier; every other node
    runs on the host tier. The two tiers compose in one graph, which is the
    proposal's incremental-migration path (opaque host node → confined node).

    Capability *identity* names a distinct instance of a capability type: two
    nodes that declare the same capability type but distinct identity labels
    receive *distinct* handle instances; two that name the same label share one
    instance (identity, not node, is the unit). Any capability with no identity
    declared keeps today's shared-by-type provisioning, so identity is opt-in and
    simple graphs are unaffected. Identity is spelled in the **canonical graph
    JSON** — each node's optional `capability_identities` map (declared-capability
    type → label) — so it lives in the source of truth rather than only in this
    call. On a sub-graph-reference node the same map routes a named instance across
    the composition boundary. The `identities` argument here stays as an escape
    hatch and **overrides** the graph per `(node, capability type)`: the argument
    wins where both name an identity for one slot, the graph applies elsewhere.
    This is the narrow half of the research agenda's capability-routing item — naming
    identity — and the prerequisite a later revocation change needs to target a
    specific instance.

    `revocable_instances` and `rotatable_instances` name identity instances — as
    `(capability type, identity label)` pairs, matching the pool `identities` builds
    — that the host can administer at runtime: revoke (withdraw authority) and/or
    rotate (re-point at a new backing handle). An instance named in either set is
    provisioned behind a caretaker (a forwarding proxy); the paired revoker/rotator
    is kept on the assembled graph in `revokers`/`rotators`, reachable via
    `graph.revoke(...)` / `graph.rotate(...)`. Nodes only ever receive the
    caretaker. Both are opt-in and layered on identity: an instance is
    revocable/rotatable only if some node declares that `(capability, identity)`,
    the two authorities are granted independently (an instance may be one, both, or
    neither), and un-named instances (type-only and plain-identity) are provisioned
    bare, exactly as before. This is the narrow, host-tier form of Technical Note
    A's revocation-and-rotation item; the redeployment form and the sandbox tier
    remain open.

    `handles` supplies already-provisioned capability handles by capability type,
    instead of minting new ones from `backend`/`stores`. This is what makes a
    *sub-graph* a sub-graph rather than a second independent program: when the
    runtime executes a node whose body is another graph, it assembles that graph
    with the handles the parent routed to that node, so the child exercises the
    parent's authority and cannot quietly provision more of its own. A capability
    with no supplied handle is provisioned as before, so `backend` is required only
    when something actually needs provisioning."""
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

    capabilities = list(graph["capabilities"])
    supplied = dict(handles or {})

    def _provision(cap_type: str) -> object:
        """Mint a handle, or fail with a message that names what was missing.
        Provisioning needs a backend; a graph assembled purely from supplied
        handles (a sub-graph) legitimately has none."""
        if backend is None:
            raise AssemblyError(
                [
                    f"capability {cap_type!r} has no supplied handle and no backend to "
                    f"provision one from"
                ]
            )
        return provision(cap_type, backend=backend, stores=stores)

    provisioned: dict[str, object] = {
        cap: supplied[cap] if cap in supplied else _provision(cap) for cap in capabilities
    }

    unknown_supplied = set(supplied) - set(capabilities)
    if unknown_supplied:
        raise AssemblyError(
            [
                f"handle supplied for capability {c!r}, which this graph does not declare"
                for c in sorted(unknown_supplied)
            ]
        )

    # Identity-aware provisioning. Distinct identity labels for one capability
    # type get distinct handle instances (pooled by label so a shared label means
    # a shared instance); nodes without a declared identity fall through to the
    # shared-by-type default in `handles` above.
    #
    # The canonical graph JSON is the source of identity: each node may carry a
    # `capability_identities` map (declared-capability type → label). The
    # `identities=` argument stays as an escape hatch and overrides the graph at
    # the (node, capability) granularity — the argument wins where both name an
    # identity for the same slot, the graph applies everywhere else, so overriding
    # one slot never silently drops a node's other declared identities. This is
    # what makes the graph, not the Python call site, the source of truth while
    # keeping the existing API working.
    identities = _merge_identities(graph["nodes"], identities)
    cap_set = set(capabilities)
    identity_pool: dict[tuple[str, str], object] = {}
    # (node name, capability type) → the identity-pool key it binds. Recorded now
    # and resolved into `instances` after revocable wrapping, so a node binds the
    # caretaker (not the bare handle) whenever its instance is revocable.
    bindings: list[tuple[str, str, tuple[str, str]]] = []
    for node_name, per_cap in identities.items():
        node = nodes.get(node_name)
        if node is None:
            raise AssemblyError([f"identity declared for unknown node {node_name!r}"])
        for cap_type, label in per_cap.items():
            if cap_type not in cap_set:
                raise AssemblyError(
                    [f"identity declared for unknown capability {cap_type!r} on node {node_name!r}"]
                )
            if cap_type not in node.inputs:
                raise AssemblyError(
                    [
                        f"node {node_name!r} does not declare capability {cap_type!r}, "
                        f"so it cannot be given an identity for it"
                    ]
                )
            key = (cap_type, label)
            if key not in identity_pool:
                identity_pool[key] = _provision(cap_type)
            bindings.append((node_name, cap_type, key))

    # Opt-in revocation/rotation: wrap each named identity instance behind a
    # caretaker once, and mint the paired host authorities — a revoker if the
    # instance is revocable, a rotator if rotatable, both if both. Only instances
    # some node actually binds can be managed — otherwise there is nothing to sever
    # or re-point — so an unbound `(cap_type, identity)` is a loud assembly error,
    # not a silent no-op. The two sets are de-duplicated and unioned so an instance
    # named in both is wrapped exactly once.
    revocable_set = set(revocable_instances)
    rotatable_set = set(rotatable_instances)
    revokers: dict[tuple[str, str], Revoker] = {}
    rotators: dict[tuple[str, str], Rotator] = {}
    for key in dict.fromkeys([*revocable_instances, *rotatable_instances]):  # union, ordered
        if key not in identity_pool:
            kind = "revocable" if key in revocable_set else "rotatable"
            raise AssemblyError(
                [
                    f"{kind} instance {key!r} is not a declared identity; an instance "
                    f"is {kind} only if some node declares that (capability, identity)"
                ]
            )
        caretaker, revoker, rotator = manage(
            identity_pool[key],
            revocable=key in revocable_set,
            rotatable=key in rotatable_set,
        )
        identity_pool[key] = caretaker
        if revoker is not None:
            revokers[key] = revoker
        if rotator is not None:
            rotators[key] = rotator

    instances: dict[tuple[str, str], object] = {
        (node_name, cap_type): identity_pool[key] for node_name, cap_type, key in bindings
    }

    return AssembledGraph(
        name=graph["name"],
        parameters=list(graph["parameters"]),
        capabilities=capabilities,
        nodes=nodes,
        edges=edges,
        handles=provisioned,
        instances=instances,
        revokers=revokers,
        rotators=rotators,
        identities={n: dict(caps) for n, caps in identities.items()},
    )
