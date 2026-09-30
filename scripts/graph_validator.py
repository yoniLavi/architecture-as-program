"""Validator for signal-graph JSON definitions.

Four layers of check:

  1. Structural. Required fields present with correct JSON types
     (informal mirror of graphs/schema.json).
  2. Intra-graph. Declared capabilities are used; declared boundary
     data inputs are consumed; edges reference existing nodes; sum-
     type variant ports exist; layout references only known nodes.
  3. Type-aware. Edge type compatibility with sum-type variant
     resolution, and trust propagation — every node that consumes an
     `Untrusted<_>` input and emits a non-`Untrusted` output must
     declare `discharges_trust: true`, making the discharge point
     explicit.
  4. Cross-graph. If a node's name matches another graph's `name`,
     its input list must equal that graph's parameter list. Catches
     sub-graph signature mismatches.

Designed to be stdlib-only so the pre-commit hook stays portable.
The validator is imported by tests and wrapped by
scripts/validate-graphs.py for CLI use.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable
from pathlib import Path

from type_parser import (
    CAPABILITY_HEADS,
    ParseError,
    TApp,
    TList,
    TName,
    Trust,
    TSum,
    Type,
    contains_capability,
    deep_trust_level,
    is_assignable,
    output_variant_levels,
    parse_type,
    strip_trust,
    sum_roles,
    sum_variant_type,
    trust_flows_to,
    trust_level,
    trust_meet,
    unparse,
)

_NAME_RE = re.compile(r"^[A-Z][A-Za-z0-9]*$")


# ── Per-graph validation ───────────────────────────────────────────


def _validate_structure(graph: dict, path: Path, errors: list[str]) -> bool:
    """Minimal structural check. Returns True if the graph is valid
    enough to proceed to semantic checks."""
    ok = True
    for field in ("name", "parameters", "capabilities", "nodes", "data_edges"):
        if field not in graph:
            errors.append(f"{path.name}: missing required field: {field}")
            ok = False
    if not ok:
        return False

    if not isinstance(graph["name"], str) or not _NAME_RE.match(graph["name"]):
        errors.append(f"{path.name}: `name` must be PascalCase, got: {graph['name']!r}")
        ok = False
    for f in ("parameters", "capabilities"):
        v = graph[f]
        if not isinstance(v, list) or not all(isinstance(s, str) and s for s in v):
            errors.append(f"{path.name}: `{f}` must be a list of non-empty strings")
            ok = False
    if not isinstance(graph["nodes"], list) or not graph["nodes"]:
        errors.append(f"{path.name}: `nodes` must be a non-empty list")
        ok = False
    if not isinstance(graph["data_edges"], list):
        errors.append(f"{path.name}: `data_edges` must be a list")
        ok = False
    return ok


def _data_inputs(node: dict, caps: list[str]) -> list[str]:
    """Non-capability inputs of a node, in declaration order."""
    return [inp for inp in node["inputs"] if inp not in caps]


def _try_parse(src: str, label: str, path: Path, errors: list[str]) -> Type | None:
    try:
        return parse_type(src)
    except ParseError as e:
        errors.append(f"{path.name}: cannot parse {label}: {e}")
        return None


def _validate_semantic(graph: dict, path: Path, errors: list[str]) -> dict[str, dict]:
    params = graph["parameters"]
    caps = graph["capabilities"]
    nodes = graph["nodes"]
    edges = graph["data_edges"]

    # Every capability must be declared as a parameter.
    for c in caps:
        if c not in params:
            errors.append(f"{path.name}: capability {c!r} not listed in parameters")

    # Nodes: shape + uniqueness.
    node_map: dict[str, dict] = {}
    for n in nodes:
        if not isinstance(n, dict):
            errors.append(f"{path.name}: node must be an object, got: {n!r}")
            continue
        missing = [f for f in ("name", "inputs", "output") if f not in n]
        if missing:
            errors.append(f"{path.name}: node missing fields {missing}: {n}")
            continue
        nname = n["name"]
        if not isinstance(nname, str) or not _NAME_RE.match(nname):
            errors.append(f"{path.name}: node name must be PascalCase: {nname!r}")
            continue
        if nname in node_map:
            errors.append(f"{path.name}: duplicate node name: {nname!r}")
            continue
        if not isinstance(n["inputs"], list) or not all(
            isinstance(s, str) and s for s in n["inputs"]
        ):
            errors.append(
                f"{path.name}: node {nname!r} `inputs` must be a list of non-empty strings"
            )
            continue
        if not isinstance(n["output"], str) or not n["output"]:
            errors.append(f"{path.name}: node {nname!r} `output` must be a non-empty string")
            continue
        if "discharges_trust" in n and not isinstance(n["discharges_trust"], bool):
            errors.append(f"{path.name}: node {nname!r} `discharges_trust` must be boolean")
            continue
        if "binds_principal" in n and not isinstance(n["binds_principal"], bool):
            errors.append(f"{path.name}: node {nname!r} `binds_principal` must be boolean")
            continue
        # Contracts are checked for *parseability* here. Resolvable field paths are
        # not yet checked anywhere before a run (poc/contracts.py
        # `unresolvable_paths` is not called). The split is forced by what each
        # layer can know: this
        # validator is dependency-free and holds no field schema for a declared type
        # name, so it can tell a malformed predicate from a well-formed one but not
        # a real field from an imagined one.
        contract_error = _contract_syntax_error(n)
        if contract_error is not None:
            # Record it and keep the node: dropping it would cascade into
            # spurious "unknown node" errors on every edge that names it, and
            # silently skip the node's other checks.
            errors.append(f"{path.name}: node {nname!r} {contract_error}")
        node_map[nname] = n

    # Capabilities are provisioned through `with` clauses and never carried as
    # data. A capability type in a data position — a boundary parameter not
    # declared as a capability, a data input, or anywhere in an output — would be
    # a handle passed along an edge: the reference passing the graph gives up to
    # keep its authority topology statically analysable. A spelling variant of a
    # declared capability lands here too, rather than silently becoming data.
    for c in caps:
        ast = _try_parse(c, f"capability {c!r}", path, errors)
        if ast is not None and not (
            (isinstance(ast, TApp) and ast.head in CAPABILITY_HEADS)
            or (isinstance(ast, TName) and ast.name in CAPABILITY_HEADS)
        ):
            errors.append(f"{path.name}: {c!r} is listed as a capability but is not one")
    for p in params:
        if p in caps:
            continue
        ast = _try_parse(p, f"parameter {p!r}", path, errors)
        if ast is not None and contains_capability(ast):
            errors.append(
                f"{path.name}: parameter {p!r} carries a capability type as data; "
                f"capabilities are provisioned, not passed along edges"
            )
    for nname, n in node_map.items():
        positions = [("input", i) for i in n["inputs"] if i not in caps]
        positions.append(("output", n["output"]))
        for role, src in positions:
            ast = _try_parse(src, f"{role} of node {nname!r}", path, errors)
            if ast is not None and contains_capability(ast):
                errors.append(
                    f"{path.name}: node {nname!r} has a capability type in a data "
                    f"{role} ({src!r}); capabilities are provisioned through `with` "
                    f"clauses, not passed along edges"
                )

    # A principal binder must hold authority to scope. Declaring the acting-on-
    # behalf-of hop on a node that holds no capability is a marker with nothing to
    # bind — the same class of error as declaring a trust discharge on a node with
    # no untrusted input, and caught here for the same reason: a declaration that
    # cannot mean anything is a graph mistake, not a runtime surprise.
    for nname, n in node_map.items():
        if not n.get("binds_principal", False):
            continue
        if not any(inp in caps for inp in n["inputs"]):
            errors.append(
                f"{path.name}: node {nname!r} declares `binds_principal: true` but holds no "
                f"capability; a principal binder with no authority to scope binds nothing"
            )

    # Every declared capability must be used by at least one node.
    used_caps: set[str] = set()
    for n in node_map.values():
        for inp in n["inputs"]:
            if inp in caps:
                used_caps.add(inp)
    for c in caps:
        if c not in used_caps:
            errors.append(f"{path.name}: capability {c!r} declared but never used in any node")

    # Every non-capability parameter must be consumed by at least one node.
    data_params = [p for p in params if p not in caps]
    consumed: set[str] = set()
    for n in node_map.values():
        for inp in n["inputs"]:
            if inp in data_params:
                consumed.add(inp)
    for p in data_params:
        if p not in consumed:
            errors.append(f"{path.name}: boundary data input {p!r} declared but never consumed")

    _validate_edges(path, node_map, caps, edges, errors)
    _validate_node_trust_flow(path, node_map, caps, errors)
    _validate_identities(path, node_map, caps, errors)
    _validate_layout(path, node_map, graph.get("layout", {}), errors)

    return node_map


def _validate_capability_identities_shape(
    path: Path, name: str, ci: object, errors: list[str]
) -> dict | None:
    """Shape-only check for a node's optional `capability_identities` field:
    it must be an object mapping capability-type strings to non-empty label
    strings. Returns the map if well-shaped, else None (with errors appended).
    Kept separate from the semantic check so a malformed field fails loudly
    rather than being silently ignored."""
    if not isinstance(ci, dict):
        errors.append(
            f"{path.name}: node {name!r} `capability_identities` must be an object "
            f"mapping a capability type to an identity label"
        )
        return None
    ok = True
    for cap_type, label in ci.items():
        if not isinstance(label, str) or not label:
            errors.append(
                f"{path.name}: node {name!r} identity label for {cap_type!r} must be "
                f"a non-empty string"
            )
            ok = False
    return ci if ok else None


def _validate_identities(
    path: Path,
    node_map: dict[str, dict],
    caps: list[str],
    errors: list[str],
) -> None:
    """Validate optional per-node `capability_identities` declarations.

    An identity labels a distinct instance of a capability the node holds, so the
    sole semantic rule — the *same* one the runtime enforces at assembly time (see
    `poc/graph.py`) — is that the labelled type is actually a capability the node
    declares in its `inputs`. Catching it here means a misrouted identity is a
    validation error, mirroring the runtime's assembly-time rejection, rather than
    surfacing only when someone tries to assemble the graph."""
    cap_set = set(caps)
    for name, n in node_map.items():
        if "capability_identities" not in n:
            continue
        ci = _validate_capability_identities_shape(path, name, n["capability_identities"], errors)
        if ci is None:
            continue
        for cap_type in ci:
            if cap_type not in cap_set:
                errors.append(
                    f"{path.name}: node {name!r} declares an identity for {cap_type!r}, "
                    f"which is not a declared capability of the graph"
                )
            elif cap_type not in n["inputs"]:
                errors.append(
                    f"{path.name}: node {name!r} declares an identity for capability "
                    f"{cap_type!r} it does not hold; an identity may be declared only for "
                    f"a capability the node's `inputs` names"
                )


def _validate_edges(
    path: Path,
    node_map: dict[str, dict],
    caps: list[str],
    edges: list[dict],
    errors: list[str],
) -> None:
    # Track, per source node, which output-variant roles have at least one
    # consumer. Used for the variant-completeness check below.
    consumed_ports: dict[str, set[str]] = {n: set() for n in node_map}
    seen_edges: set[tuple[str, str]] = set()
    successors: dict[str, set[str]] = {n: set() for n in node_map}

    for e in edges:
        if not isinstance(e, dict) or "from" not in e or "to" not in e:
            errors.append(f"{path.name}: edge must be an object with `from` and `to`: {e!r}")
            continue
        fr = e["from"]
        to = e["to"]
        # The runtime schedules a node once per arriving edge, so a repeated
        # edge runs its target twice (a tool-capable node twice, a reply sent
        # twice) — fan-out the model does not address.
        if (fr, to) in seen_edges:
            errors.append(f"{path.name}: duplicate edge {fr!r}→{to!r}")
            continue
        seen_edges.add((fr, to))
        base = fr.rsplit(".", 1)[0] if "." in fr else fr
        if base in successors and to in node_map:
            successors[base].add(to)
        if "." in fr:
            from_node, port = fr.rsplit(".", 1)
        else:
            from_node, port = fr, None

        if from_node not in node_map:
            errors.append(f"{path.name}: edge `from` references unknown node: {fr!r}")
            continue
        if to not in node_map:
            errors.append(f"{path.name}: edge `to` references unknown node: {to!r}")
            continue

        src_node = node_map[from_node]
        tgt_node = node_map[to]

        src_output_ast = _try_parse(
            src_node["output"], f"output of node {from_node!r}", path, errors
        )
        if src_output_ast is None:
            continue

        # Variant resolution.
        if port is not None:
            variants = sum_roles(src_output_ast)
            if not variants:
                errors.append(
                    f"{path.name}: edge {fr!r}→{to!r} addresses a port but "
                    f"{from_node!r}'s output is not a sum type: "
                    f"{unparse(src_output_ast)!r}"
                )
                continue
            if port not in variants:
                errors.append(
                    f"{path.name}: edge {fr!r}→{to!r} addresses unknown port "
                    f"{port!r}; available variants: {variants}"
                )
                continue
            src_ast = sum_variant_type(src_output_ast, port)
            if src_ast is None:
                continue  # shouldn't happen given the check above
            consumed_ports[from_node].add(port)
        else:
            if sum_roles(src_output_ast):
                # The runtime routes a labelled sum's variant by its role, so an
                # unported edge from one never fires: it would read as consuming
                # every variant while carrying none, and a branch it "covers"
                # would be dropped silently at run time.
                errors.append(
                    f"{path.name}: edge {fr!r}→{to!r}: {from_node!r} emits a labelled "
                    f"sum, which is consumed by port; the runtime routes a variant by "
                    f"its role, so a whole-output edge never fires"
                )
                continue
            src_ast = src_output_ast

        # Target data-input resolution.
        tgt_data = _data_inputs(tgt_node, caps)
        if len(tgt_data) == 0:
            errors.append(f"{path.name}: edge {fr!r}→{to!r}: target node {to!r} has no data inputs")
            continue
        if len(tgt_data) > 1:
            errors.append(
                f"{path.name}: edge {fr!r}→{to!r}: target node {to!r} has multiple "
                f"data inputs ({tgt_data}); multi-input disambiguation is a "
                f"Phase 1 language-design question (see the paper's research agenda)"
            )
            continue

        tgt_ast = _try_parse(tgt_data[0], f"input of node {to!r}", path, errors)
        if tgt_ast is None:
            continue

        # Two independent obligations, kept apart on purpose. (1) Data
        # compatibility: the carried shapes, with any trust wrapper
        # stripped, must match. (2) Trust flow: the source's trust label
        # must flow to the target's under the lattice — no upward
        # coercion. Folding trust into the edge check this way is what
        # makes trust laundering a wiring error rather than a separate
        # side-condition (see _validate_node_trust_flow for the node-body
        # half of the same discipline).
        if strip_trust(src_ast) != strip_trust(tgt_ast):
            errors.append(
                f"{path.name}: edge {fr!r}→{to!r}: type mismatch.\n"
                f"      source emits: {unparse(src_ast)}\n"
                f"      target wants: {unparse(tgt_ast)}"
            )
        elif not trust_flows_to(trust_level(src_ast), trust_level(tgt_ast)):
            errors.append(
                f"{path.name}: edge {fr!r}→{to!r}: trust-lattice violation "
                f"(upward coercion).\n"
                f"      source emits: {unparse(src_ast)} (untrusted)\n"
                f"      target wants: {unparse(tgt_ast)} (trusted)\n"
                f"      `Untrusted<_>` does not flow to a clean requirement; "
                f"route it through a declared discharger first."
            )

    # The graphs run a single active path from boundary to terminal; a cycle
    # would run without bound (a reply node wired back to the entry sends a
    # reply per lap). Reject it rather than leave the runtime to loop.
    def _on_cycle(start: str) -> bool:
        stack, visited = [start], set()
        while stack:
            for nxt in successors.get(stack.pop(), ()):
                if nxt == start:
                    return True
                if nxt not in visited:
                    visited.add(nxt)
                    stack.append(nxt)
        return False

    cyclic = sorted(n for n in successors if _on_cycle(n))
    if cyclic:
        errors.append(
            f"{path.name}: the data edges form a cycle through {cyclic}; a signal graph is acyclic"
        )

    # Variant-completeness sweep: for every labelled sum output, every
    # declared variant must have at least one consuming edge on its own
    # port. (A whole-output edge from a labelled sum is rejected above: the
    # runtime never sends a variant along one, so it covers nothing.)
    for name, n in node_map.items():
        output_ast = _try_parse(n["output"], f"output of node {name!r}", path, errors)
        if output_ast is None:
            continue
        variants = sum_roles(output_ast)
        if not variants:
            continue
        unconsumed = [v for v in variants if v not in consumed_ports[name]]
        for role in unconsumed:
            errors.append(
                f"{path.name}: node {name!r} declares output variant "
                f"{role!r} but no edge consumes it; the variant is dead "
                f"code at the graph level."
            )


def _validate_node_trust_flow(
    path: Path,
    node_map: dict[str, dict],
    caps: list[str],
    errors: list[str],
) -> None:
    """The node-body half of the trust-lattice discipline (the edge
    half lives in `_validate_edges`). A node's body is itself a flow,
    from the meet of its input trust levels to its output level, and it
    is checked with the *same* `trust_flows_to` predicate: a node may
    not raise trust — emit an output more trusted than its least-trusted
    input — because that is upward coercion (trust laundering). The one
    exception is a node explicitly declared as a discharger, which is
    precisely the licence to make that upward move. Casting the check
    this way is what subsumes the old two-rule scheme (edge equality +
    a standalone `discharges_trust` presence test) into one lattice
    order applied uniformly to edges and node bodies."""
    for n in node_map.values():
        input_asts: list[Type] = []
        for inp in _data_inputs(n, caps):
            ast = _try_parse(inp, f"input of node {n['name']!r}", path, errors)
            if ast is not None:
                input_asts.append(ast)

        output_ast = _try_parse(n["output"], f"output of node {n['name']!r}", path, errors)
        if output_ast is None:
            continue

        # Inputs count `Untrusted<_>` anywhere inside them (under a type
        # constructor too), and the output is checked per variant: each
        # variant leaves on its own port, so a sum with one `Untrusted<_>`
        # variant must not let its other variants leave trusted.
        in_trust = trust_meet(deep_trust_level(t) for t in input_asts)
        discharges = bool(n.get("discharges_trust", False))

        # `raises_trust` is exactly the negation of the lattice flow
        # condition on the node body: some output variant demands more
        # trust than the inputs supply. Only a declared discharger may.
        raises_trust = any(
            not trust_flows_to(in_trust, level) for level in output_variant_levels(output_ast)
        )

        if raises_trust and not discharges:
            errors.append(
                f"{path.name}: node {n['name']!r} raises trust without "
                f"discharging: it consumes an `Untrusted<_>` input but emits "
                f"a non-`Untrusted` output, yet is not a declared discharger "
                f'(`"discharges_trust": true`). Under the trust lattice this '
                f"is upward coercion — trust laundering — which the wiring "
                f"forbids."
            )
        if discharges and in_trust is not Trust.UNTRUSTED:
            errors.append(
                f"{path.name}: node {n['name']!r} declares "
                f"`discharges_trust: true` but has no `Untrusted<_>` input; "
                f"the annotation is unused."
            )

        # The sink rule. The lattice alone constrains *raising* trust, not
        # *consuming* untrusted data: a tool-capable node could take
        # `Untrusted<_>` input so long as its outputs stayed untrusted, or be
        # declared a discharger itself. The design's claim is stronger — no
        # untrusted source reaches a tool-capable LLM without transiting a
        # discharging type — so a node holding a tool-scoped `LLMClient<[...]>`
        # may neither consume `Untrusted<_>` nor be the discharger.
        if _holds_tool_scoped_llm(n, caps):
            if in_trust is Trust.UNTRUSTED:
                errors.append(
                    f"{path.name}: node {n['name']!r} holds a tool-scoped LLMClient "
                    f"but consumes an `Untrusted<_>` input. Untrusted data may reach "
                    f"a tool-capable node only after an upstream declared discharger "
                    f'(`"discharges_trust": true`); anything else is upward coercion '
                    f"into a privileged sink — trust laundering — which the wiring "
                    f"forbids."
                )
            if discharges:
                errors.append(
                    f"{path.name}: node {n['name']!r} holds a tool-scoped LLMClient "
                    f'and declares `"discharges_trust": true`. A tool-capable node '
                    f"cannot be its own discharger: declaring it one would license the "
                    f"upward coercion of its own input — trust laundering by "
                    f"relabelling the consumer."
                )


def _holds_tool_scoped_llm(node: dict, caps: list[str]) -> bool:
    """True if the node holds an `LLMClient<[...]>` whose scope is a non-empty
    tool list — a model that can act, not only infer."""
    for inp in node["inputs"]:
        if inp not in caps:
            continue
        try:
            ast = parse_type(inp)
        except ParseError:
            continue
        if _is_tool_scoped(ast):
            return True
    return False


def _is_tool_scoped(ast: Type) -> bool:
    """True if `ast` is an `LLMClient<[...]>` with a non-empty tool list."""
    return (
        isinstance(ast, TApp)
        and ast.head == "LLMClient"
        and bool(ast.args)
        and isinstance(ast.args[0], TList)
        and bool(ast.args[0].items)
    )


def _validate_layout(
    path: Path,
    node_map: dict[str, dict],
    layout: dict,
    errors: list[str],
) -> None:
    if not isinstance(layout, dict):
        return
    for pn in layout.get("positions", {}):
        if pn not in node_map:
            errors.append(f"{path.name}: layout.positions references unknown node: {pn!r}")
    for zname, z in layout.get("zones", {}).items():
        if not isinstance(z, dict):
            continue
        for zn in z.get("nodes", []):
            if zn not in node_map:
                errors.append(f"{path.name}: layout.zones.{zname} references unknown node: {zn!r}")


# ── Cross-graph check ──────────────────────────────────────────────


def _type_members(ast: Type) -> set[str]:
    """The set of types a type denotes, trust *kept*. A sum contributes one
    member per variant; any other type contributes itself. Used to compare a
    sub-graph node's declared output against the child graph's terminal types
    *structurally*, so `DeliveryConfirmation | EscalationTicket` is the same claim
    however its variants are ordered or labelled. Trust is part of the member: a
    child terminal emitting `Untrusted<X>` must be declared as `Untrusted<X>` at
    the boundary, or the parent would receive untrusted data labelled clean — the
    same upward coercion the edge and node-body checks forbid inside one graph."""
    if isinstance(ast, TSum):
        return {unparse(v.inner) for v in ast.variants}
    return {unparse(ast)}


def _terminal_output_members(graph: dict) -> set[str]:
    """The union of the data shapes a graph can emit at its boundary: the output
    types of its terminal nodes (those with no outgoing edge), trust kept.

    This is what a sub-graph's declared boundary output must honestly describe.
    Exactly one terminal is reached per run, so the boundary value is always a
    member of this set; the declared output type is the set's name."""
    sources = set()
    for e in graph.get("data_edges", []):
        if isinstance(e, dict) and isinstance(e.get("from"), str):
            sources.add(e["from"].rsplit(".", 1)[0] if "." in e["from"] else e["from"])
    members: set[str] = set()
    for node in graph["nodes"]:
        if not isinstance(node, dict) or node.get("name") in sources:
            continue
        out = node.get("output")
        if not isinstance(out, str):
            continue
        try:
            members |= _type_members(parse_type(out))
        except ParseError:
            continue  # a malformed terminal output is already flagged per-graph
    return members


def _validate_subgraph_output(
    path: Path,
    ref: str,
    node: dict,
    target: dict,
    errors: list[str],
) -> None:
    """The output half of the sub-graph signature check, dual to the input half.

    The vision left this unchecked: a sub-graph node could declare any boundary
    output and no analysis would object, so the union-alias convention
    (`ServiceOutcome = DeliveryConfirmation | EscalationTicket`) was asserted in the
    JSON and verified by nothing. The check is *structural, not nominal* — the
    graph spells the union rather than naming an alias the language cannot resolve,
    and here the declared output's member set must equal the union of the referenced
    graph's terminal output types. A mismatch means the boundary type misdescribes
    what the sub-graph emits."""
    declared = node.get("output")
    if not isinstance(declared, str):
        return  # already flagged by the per-graph node check
    try:
        declared_ast = parse_type(declared)
    except ParseError:
        return  # malformed output already flagged per-graph
    if sum_roles(declared_ast):
        # A boundary value is a terminal's output, never a routed variant, so a
        # labelled boundary type would give the parent ports that never fire.
        errors.append(
            f"{path.name}: node {ref!r} is used as a sub-graph but declares a labelled "
            f"boundary output ({declared!r}); its declared output must carry no role "
            f"labels, since a boundary value is never a variant and a port on it never fires"
        )
        return
    declared_members = _type_members(declared_ast)
    terminal_members = _terminal_output_members(target)
    if not terminal_members:
        return  # a graph with no discernible terminals is a separate structural fault
    if declared_members != terminal_members:
        errors.append(
            f"{path.name}: node {ref!r} is used as a sub-graph but its declared "
            f"output does not match the union of {ref!r}'s terminal output types.\n"
            f"      declared output:  {declared}  (members: {sorted(declared_members)})\n"
            f"      terminal outputs: {sorted(terminal_members)}\n"
            f"      A sub-graph's boundary output must honestly describe what its "
            f"terminals emit; spell the union so the analysis can check it."
        )


def _validate_cross_graph(
    graphs: dict[str, dict],
    graphs_path: dict[str, Path],
    errors: list[str],
) -> None:
    """A node whose name matches another graph's `name` is a sub-graph
    reference. Its input list must satisfy that graph's parameter list
    position-by-position: data inputs must match by equality; capability
    inputs may be provided with at least the authority the sub-graph
    declares (capability narrowing — see `type_parser.is_assignable`).
    Its declared *output* must, dually, equal the union of the referenced
    graph's terminal output types (`_validate_subgraph_output`)."""
    for gname, g in graphs.items():
        path = graphs_path[gname]
        for n in g["nodes"]:
            ref = n["name"]
            if ref == gname:
                # A node named after its own graph would be a sub-graph of
                # itself; skipping it would also skip every cross-graph check
                # a same-named canonical graph should have triggered.
                errors.append(
                    f"{path.name}: node {ref!r} has the name of its own graph; a "
                    f"graph cannot contain itself as a sub-graph"
                )
                continue
            if ref not in graphs:
                continue
            target = graphs[ref]
            provided = n["inputs"]
            expected = target["parameters"]
            target_caps = set(target["capabilities"])

            _validate_subgraph_output(path, ref, n, target, errors)

            if len(provided) != len(expected):
                errors.append(
                    f"{path.name}: node {ref!r} is used as a sub-graph but "
                    f"has arity {len(provided)} vs target's {len(expected)}.\n"
                    f"      node inputs:    {provided}\n"
                    f"      target params:  {expected}"
                )
                continue

            mismatches: list[str] = []
            for i, (p, e) in enumerate(zip(provided, expected, strict=True)):
                if p == e:
                    continue
                # Different strings: capability positions may still
                # satisfy via narrowing; data positions must match.
                is_capability_position = e in target_caps
                if not is_capability_position:
                    mismatches.append(
                        f"position {i}: data type {p!r} does not match expected {e!r}"
                    )
                    continue
                try:
                    pa = parse_type(p)
                    ea = parse_type(e)
                except ParseError as pe:
                    mismatches.append(f"position {i}: cannot parse types ({pe})")
                    continue
                if not is_assignable(pa, ea):
                    mismatches.append(
                        f"position {i}: provided capability {p!r} is not "
                        f"assignable to expected {e!r} under the subtyping "
                        f"rules"
                    )
                elif _is_tool_scoped(pa) and not _is_tool_scoped(ea):
                    # Narrowing is checked, not enforced: the handle is routed
                    # whole. A tool client routed into an inference-only slot
                    # would make every child node holding that slot a node that
                    # holds a tool-scoped LLMClient the sink rule never saw.
                    mismatches.append(
                        f"position {i}: provided {p!r} is tool-scoped but {e!r} is "
                        f"inference-only; a tool client may not be routed into an "
                        f"inference-only slot, out of the sink rule's sight"
                    )

            if mismatches:
                bullet = "\n      - ".join(mismatches)
                errors.append(
                    f"{path.name}: node {ref!r} is used as a sub-graph but "
                    f"its inputs do not satisfy that graph's parameters:\n"
                    f"      - {bullet}"
                )


# ── Public entry point ─────────────────────────────────────────────


# A field path: dot-separated segments, each starting with a letter, so no
# private or dunder attribute (mirrors `_PATH` in poc/contracts.py).
_CONTRACT_PATH = r"[A-Za-z][A-Za-z0-9_]*(?:\.[A-Za-z][A-Za-z0-9_]*)*"

_CONTRACT_FORMS = (
    re.compile(rf"^len\(\s*{_CONTRACT_PATH}\s*\)\s*(==|!=|>=|<=|>|<)\s*-?\d+$"),
    re.compile(rf"^{_CONTRACT_PATH}\s+in\s+\[.*\]$"),
    re.compile(rf"^present\(\s*{_CONTRACT_PATH}\s*\)$"),
    re.compile(rf"^{_CONTRACT_PATH}\s*(==|!=|>=|<=|>|<)\s*.+$"),
)


def _contract_syntax_error(node: dict) -> str | None:
    """A node's `requires`/`ensures` must be lists of predicates in the closed
    vocabulary. Mirrors poc/contracts.py's grammar deliberately: the runtime parses
    for real, this only rejects what could never parse, so an unevaluatable contract
    fails at validation rather than part-way through a run."""
    for key in ("requires", "ensures"):
        if key not in node:
            continue
        clauses = node[key]
        if not isinstance(clauses, list) or not all(
            isinstance(c, str) and c.strip() for c in clauses
        ):
            return f"`{key}` must be a list of non-empty predicate strings"
        for clause in clauses:
            if not any(form.match(clause.strip()) for form in _CONTRACT_FORMS):
                return (
                    f"`{key}` predicate {clause!r} is outside the contract vocabulary "
                    f"(permitted: `path <op> literal`, `path in [a, b]`, `present(path)`, "
                    f"`len(path) <op> integer`)"
                )
    return None


def validate_files(files: Iterable[Path]) -> list[str]:
    """Validate a set of graph JSON files. Returns a list of error
    messages; the list is empty iff every graph is valid."""
    errors: list[str] = []
    graphs: dict[str, dict] = {}
    graphs_path: dict[str, Path] = {}

    for f in files:
        try:
            graph = json.loads(f.read_text())
        except json.JSONDecodeError as e:
            errors.append(f"{f.name}: invalid JSON: {e}")
            continue

        if not _validate_structure(graph, f, errors):
            continue

        _validate_semantic(graph, f, errors)
        if graph["name"] in graphs:
            # Graphs are resolved by name, so two graphs sharing one would let
            # the second silently replace the first and skip every cross-graph
            # check against it.
            errors.append(
                f"{f.name}: graph name {graph['name']!r} is already declared by "
                f"{graphs_path[graph['name']].name}; graph names must be unique"
            )
            continue
        graphs[graph["name"]] = graph
        graphs_path[graph["name"]] = f

    _validate_cross_graph(graphs, graphs_path, errors)
    return errors
