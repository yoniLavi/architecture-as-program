"""The feed-triage service's own structural invariants.

The graph validator checks what must hold of *any* signal graph: edges type-check,
trust is never raised undeclared, a join's positions are each fed once. It has no
opinion on where a graph puts its network access. A graph that fetched a URL
*after* asking a model what to fetch would validate — plenty of useful agent
graphs do exactly that.

The feed-triage service's security argument is that this one does not. So the
argument is written down here as checks over the graph's structure, and run in
three places: by the driver before every tick (a graph that breaks one is not
run), by the feed evaluation (each is a pinned corpus case), and by the tests.

What these are, stated plainly: checks written for one service, over two named
graphs. They are not a general analysis and they are not part of the validator.
The honest reading of "a wiring that puts HTTP downstream of a model is rejected"
is that *this service's* check rejects it — which is what makes the third
invariant below worth having. The validator accepts a graph whose fetch node
declares its output clean, because trust is declared, not inferred; only this
service's own check notices that the label is missing.
"""

from __future__ import annotations

from type_parser import TApp, TList, TName, parse_type

# Every message begins with this, so the evaluation can tell a rejection by this
# module from one by the validator.
MARK = "feed-triage shape:"


def _head(cap: str) -> str:
    ast = parse_type(cap)
    if isinstance(ast, TApp):
        return ast.head
    return ast.name if isinstance(ast, TName) else ""


def _holds(node: dict, caps: set[str], head: str) -> list[str]:
    return [i for i in node["inputs"] if i in caps and _head(i) == head]


def _upstream(graph: dict, node: str) -> set[str]:
    """Every node with a data path to `node`."""
    parents: dict[str, set[str]] = {}
    for edge in graph["data_edges"]:
        parents.setdefault(edge["to"], set()).add(edge["from"].split(".")[0])
    found: set[str] = set()
    frontier = [node]
    while frontier:
        for parent in parents.get(frontier.pop(), ()):
            if parent not in found:
                found.add(parent)
                frontier.append(parent)
    return found


def _tool_scoped(cap: str) -> bool:
    ast = parse_type(cap)
    return (
        isinstance(ast, TApp)
        and ast.head == "LLMClient"
        and bool(ast.args)
        and isinstance(ast.args[0], TList)
        and bool(ast.args[0].items)
    )


def problems(parent: dict, child: dict) -> list[str]:
    """Violations of the service's invariants by `parent` (FeedTriage) and `child`
    (TriageItem). Empty means the shape the security argument rests on is intact."""
    found: list[str] = []
    parent_caps, child_caps = set(parent["capabilities"]), set(child["capabilities"])

    # 1. Exactly one node, in either graph, holds outbound HTTP.
    http = [n["name"] for n in parent["nodes"] if _holds(n, parent_caps, "HTTPClient")]
    http += [
        f"{child['name']}.{n['name']}"
        for n in child["nodes"]
        if _holds(n, child_caps, "HTTPClient")
    ]
    if len(http) != 1:
        found.append(
            f"{MARK} exactly one node may hold HTTPClient, but {len(http)} do ({http}); "
            f"every fetch the service makes must be decided in one place"
        )

    # 2. No model is at or upstream of a node holding HTTP: no model output can
    #    reach a fetch. A sub-graph node holding an LLMClient counts as a model.
    models = {n["name"] for n in parent["nodes"] if _holds(n, parent_caps, "LLMClient")}
    for holder in (n["name"] for n in parent["nodes"] if _holds(n, parent_caps, "HTTPClient")):
        tainted = sorted(models & (_upstream(parent, holder) | {holder}))
        if tainted:
            found.append(
                f"{MARK} {holder!r} holds HTTPClient at or downstream of model-holding "
                f"node(s) {tainted}; a model's output could then reach a fetch"
            )

    # 3. What the HTTP-holding node emits is labelled untrusted where it enters.
    for node in parent["nodes"]:
        if _holds(node, parent_caps, "HTTPClient") and not node["output"].startswith("Untrusted<"):
            found.append(
                f"{MARK} {node['name']!r} holds HTTPClient but declares its output "
                f"{node['output']!r} clean; fetched content must enter labelled `Untrusted<_>`"
            )

    # 4. No model holds a tool.
    for graph in (parent, child):
        for cap in graph["capabilities"]:
            if _tool_scoped(cap):
                found.append(
                    f"{MARK} {graph['name']} declares the tool-scoped {cap!r}; every model "
                    f"in the service is inference-only"
                )
    return found
