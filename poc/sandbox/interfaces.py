"""The capability → WIT-interface mapping, derived from the graph's own types.

This module is the hinge of the component tier. `wit/caps.wit` declares what each
capability kind *is* at the runtime boundary; the graph JSON declares which
capabilities each node *holds*. Something has to connect them, and if that
something were a hand-maintained table, the boundary could silently drift from
the node signatures it is supposed to enforce — a node's world could grant an
interface its `with` clause never asked for, and nothing would notice.

So the connection is computed. `interfaces_for_node` parses a node's capability
types with the project's own `type_parser` (the same parser the validator uses)
and maps each to the WIT interface that realises it. The test suite then asserts
that every ported component's *actual* import set equals the set derived here
from the graph. A world that over-grants is a test failure, not a subtlety.

Deliberately stdlib-only apart from `type_parser`: this module must be importable
without `wasmtime`, so tests can check the mapping even where the sandbox tier
cannot run.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping

from type_parser import TApp, TList, TName, parse_type

# The WIT package the node components are built against. Bumping the version is a
# breaking change for every committed artifact: the host's interface names and the
# names baked into the components must agree exactly, or instantiation fails.
WIT_PACKAGE = "aap:caps"
WIT_VERSION = "0.1.0"


def _iface(name: str) -> str:
    """Fully-qualified WIT interface name, as it appears in a component's imports."""
    return f"{WIT_PACKAGE}/{name}@{WIT_VERSION}"


# The five capability kinds of the vertical, as typed interfaces.
INFERENCE_LLM = _iface("inference-llm")  # LLMClient<inference>
TOOL_LLM = _iface("tool-llm")  # LLMClient<[...]>
KB_READ = _iface("kb-read")  # DBHandle<_, read>
RESPONSE_CHANNEL = _iface("response-channel")  # ResponseChannel<_>
EVENT_EMITTER = _iface("event-emitter")  # EventEmitter<_>

# The shared domain vocabulary: records, enums and variants, and *no functions*.
# Every component imports it, and it grants no authority — it is how the two sides
# agree what a `customer-query` is. It must therefore be excluded when asking "what
# authority does this component import?", which is what `capability_imports` does.
TYPES = _iface("types")

# Every interface that carries authority. Anything a component imports which is
# not in here and is not TYPES is, by definition, something this tier did not
# intend to hand out.
CAPABILITY_INTERFACES = frozenset(
    {INFERENCE_LLM, TOOL_LLM, KB_READ, RESPONSE_CHANNEL, EVENT_EMITTER}
)


class UnmappedCapability(ValueError):
    """A capability type in the graph has no WIT interface on this tier.

    Raised rather than ignored: silently dropping a capability we cannot model
    would let a node be instantiated with *less* authority than its signature
    declares, which fails in confusing ways at call time instead of here.
    """


def interface_for(cap_type: str) -> str:
    """The WIT interface realising a graph capability type.

    Mirrors `poc.handles.provision`, which maps the same type strings onto host-tier
    handle objects — the two tiers realise one capability type in two ways, and both
    derive it from the type rather than from a node's name.
    """
    ast = parse_type(cap_type)
    if not isinstance(ast, TApp):
        raise UnmappedCapability(f"not a capability type: {cap_type!r}")

    if ast.head == "LLMClient":
        if len(ast.args) != 1:
            raise UnmappedCapability(f"unrecognised LLMClient shape: {cap_type!r}")
        arg = ast.args[0]
        # LLMClient<inference>: model access, no tools. The distinction is the
        # whole point of the two LLM interfaces — `inference-llm` has no way to
        # return a tool request, so a node holding it cannot act on model output.
        if isinstance(arg, TName) and arg.name == "inference":
            return INFERENCE_LLM
        # LLMClient<[lookup, ...]>: model access plus a named tool set.
        if isinstance(arg, TList) and arg.items:
            return TOOL_LLM
        raise UnmappedCapability(f"unrecognised LLMClient shape: {cap_type!r}")

    if ast.head == "DBHandle":
        # Only read mode is modelled; `kb-read` has no `write` function, so a
        # write-mode handle has no interface to map onto and must not be silently
        # downgraded to a read one.
        mode = ast.args[1] if len(ast.args) == 2 else None
        if isinstance(mode, TName) and mode.name == "read":
            return KB_READ
        raise UnmappedCapability(f"component tier models only read-mode DBHandle: {cap_type!r}")

    if ast.head == "ResponseChannel":
        return RESPONSE_CHANNEL

    if ast.head == "EventEmitter":
        return EVENT_EMITTER

    raise UnmappedCapability(f"unknown capability kind: {cap_type!r}")


def interfaces_for_node(node: Mapping[str, object], capabilities: Iterable[str]) -> list[str]:
    """The WIT interfaces a node's `with` clause entitles it to import.

    This is the expected import set of the node's component, computed from the
    graph JSON. `capabilities` is the graph's capability list — the inputs of the
    node that appear in it are its capability inputs; the rest is its data input.
    """
    caps = set(capabilities)
    inputs = node.get("inputs", [])
    if not isinstance(inputs, list):
        raise UnmappedCapability(f"node {node.get('name')!r} has malformed inputs")
    return sorted({interface_for(i) for i in inputs if i in caps})


def expected_imports(graph: Mapping[str, object], node_name: str) -> list[str]:
    """The full expected import set of a node's component: its capability
    interfaces plus the shared type vocabulary, sorted — directly comparable with
    `host.component_imports(...)`."""
    nodes = graph.get("nodes", [])
    capabilities = graph.get("capabilities", [])
    if not isinstance(nodes, list) or not isinstance(capabilities, list):
        raise UnmappedCapability("malformed graph")
    for node in nodes:
        if node.get("name") == node_name:
            return sorted([*interfaces_for_node(node, capabilities), TYPES])
    raise UnmappedCapability(f"no node {node_name!r} in graph {graph.get('name')!r}")
