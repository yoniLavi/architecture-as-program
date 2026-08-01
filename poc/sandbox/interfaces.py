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

from type_parser import TApp, TList, TName, TString, parse_type

# The WIT package the node components are built against. Bumping the version is a
# breaking change for every committed artifact: the host's interface names and the
# names baked into the components must agree exactly, or instantiation fails.
WIT_PACKAGE = "aap:caps"
WIT_VERSION = "0.1.0"


def _iface(name: str) -> str:
    """Fully-qualified WIT interface name, as it appears in a component's imports."""
    return f"{WIT_PACKAGE}/{name}@{WIT_VERSION}"


# The capability kinds of the vertical, as typed interfaces.
INFERENCE_LLM = _iface("inference-llm")  # LLMClient<inference>
TOOL_LLM = _iface("tool-llm")  # LLMClient<[...]>
KB_READ = _iface("kb-read")  # DBHandle<_, read>
RESPONSE_CHANNEL = _iface("response-channel")  # ResponseChannel<_>
EVENT_EMITTER = _iface("event-emitter")  # EventEmitter<_>
HTTP_CLIENT = _iface("http-client")  # HTTPClient<[host, ...]>
NOTIFIER = _iface("notifier")  # Notifier<'channel'>

# `Clock` is deliberately NOT an aap:caps interface: it is the upstream WASI
# wall clock, granted directly (the WIT source is vendored under wit/deps/clocks).
# A WASI interface is one instance of capability-as-interface, and granting the
# real one is the honest form of that argument. The consequence for this module is
# exactly one line — the mapping entry — and the consequence for `wasi_imports()`
# is definitional: ambient authority is an import that was *not* granted as a
# capability, so a declared clock does not count against "no ambient imports"
# while an undeclared one still would.
CLOCK = "wasi:clocks/wall-clock@0.2.0"  # Clock

# The graph-level capability kinds (heads of `with`-clause types) this tier
# models. `LLMClient` is one kind realised by two interfaces (inference vs tool
# scope), which is why this tuple and CAPABILITY_INTERFACES have different sizes.
CAPABILITY_KINDS = (
    "LLMClient",
    "DBHandle",
    "ResponseChannel",
    "EventEmitter",
    "Clock",
    "HTTPClient",
    "Notifier",
)

# The shared domain vocabulary: records, enums and variants, and *no functions*.
# Every component imports it, and it grants no authority — it is how the two sides
# agree what a `customer-query` is. It must therefore be excluded when asking "what
# authority does this component import?", which is what `capability_imports` does.
TYPES = _iface("types")

# Every interface that carries authority. Anything a component imports which is
# not in here and is not TYPES is, by definition, something this tier did not
# intend to hand out.
CAPABILITY_INTERFACES = frozenset(
    {
        INFERENCE_LLM,
        TOOL_LLM,
        KB_READ,
        RESPONSE_CHANNEL,
        EVENT_EMITTER,
        HTTP_CLIENT,
        NOTIFIER,
        CLOCK,
    }
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

    # `Clock` is the one kind spelled as a bare name: it has no scope parameter,
    # because the authority it grants (read the wall clock) has no narrower form.
    if isinstance(ast, TName) and ast.name == "Clock":
        return CLOCK

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

    if ast.head == "HTTPClient":
        # The scope is a non-empty allowlist of string-literal hosts. The
        # *interface* is the same whatever the allowlist says — the set lives in
        # the handle, exactly as a tool-LLM's tool scope does — but a shape this
        # mapping cannot read is refused rather than granted an interface anyway.
        if (
            len(ast.args) == 1
            and isinstance(ast.args[0], TList)
            and ast.args[0].items
            and all(isinstance(i, TString) for i in ast.args[0].items)
        ):
            return HTTP_CLIENT
        raise UnmappedCapability(f"unrecognised HTTPClient shape: {cap_type!r}")

    if ast.head == "Notifier":
        return NOTIFIER

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
