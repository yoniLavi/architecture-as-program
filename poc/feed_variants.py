"""Unsafe — and, twice, deliberately safe — rewirings of the feed-triage graphs.

The counterpart of `poc/variants.py` for the service. Each function takes a graph
dict and returns a rewired copy; the feed evaluation (`poc/evaluate_feed.py`) pins
what each must produce, and by which check.

They cover what the customer-support corpus could not, because that graph had
none of it: a join, a per-item map, and network access whose *position* in the
graph is the security argument.

A mutation is written to carry one fault. Where a change to one node would leave
an edge ill-typed, the neighbouring declarations are changed with it, so that
what is rejected is the fault the case is named for and not its side effects —
the evaluation enforces this by refusing a rejection that carries a reason class
the case did not declare.
"""

from __future__ import annotations

import copy

HTTP = "HTTPClient<['simonwillison.net', 'rss.arxiv.org', 'bytecodealliance.org', 'lobste.rs']>"


def _node(graph: dict, name: str) -> dict:
    return next(n for n in graph["nodes"] if n["name"] == name)


# ── The join ─────────────────────────────────────────────────────────


def join_missing_position(parent: dict) -> dict:
    """Drop the edge that feeds `ComposeDigest`'s second position.

    The join would hold the selection for ever, waiting for a run date that no
    edge delivers. Rejected: each position of a join takes exactly one edge."""
    g = copy.deepcopy(parent)
    g["data_edges"] = [
        e for e in g["data_edges"] if not (e["from"] == "StartRun" and e["to"] == "ComposeDigest")
    ]
    return g


def join_on_exclusive_branches(parent: dict) -> dict:
    """Feed `ComposeDigest`'s two positions from the two variants of one sum.

    `SelectItems` is made to emit *either* a selection *or* the run's metadata,
    each wired to its own position. Every edge type-checks. But a node emits one
    variant per run, so both positions can never hold a value at once: the join
    could never fire. Rejected as a join across mutually exclusive branches."""
    g = copy.deepcopy(parent)
    _node(g, "SelectItems")["output"] = "chosen: Selection | quiet: RunInfo"
    _node(g, "SelectItems").pop("ensures", None)
    edges = []
    for e in g["data_edges"]:
        if e["to"] == "ComposeDigest":
            continue
        edges.append(e)
    edges += [
        {"from": "SelectItems.chosen", "to": "ComposeDigest", "to_input": 0},
        {"from": "SelectItems.quiet", "to": "ComposeDigest", "to_input": 1},
    ]
    g["data_edges"] = edges
    return g


def join_launders_one_tainted_input(parent: dict) -> dict:
    """Give the join one untrusted input among clean ones, and a clean output.

    `SelectItems` is relabelled to emit `Untrusted<Selection>` (a node may always
    forget trust), and `ComposeDigest` takes it beside the clean `RunInfo` while
    still declaring a clean `Digest`. The join's inputs meet at untrusted, so a
    clean output raises trust, and the node is no declared discharger. Rejected by
    the trust lattice — the meet, exercised rather than asserted."""
    g = copy.deepcopy(parent)
    _node(g, "SelectItems")["output"] = "Untrusted<Selection>"
    _node(g, "SelectItems").pop("ensures", None)
    compose = _node(g, "ComposeDigest")
    compose["inputs"] = [
        "Untrusted<Selection>" if i == "Selection" else i for i in compose["inputs"]
    ]
    return g


def join_carries_taint_through(parent: dict) -> dict:
    """The same tainted join, with the taint honestly carried to the end.

    Every node downstream of the join declares what it now handles as untrusted.
    No node raises trust, so nothing is laundered. **Accepted** — the control for
    the case above: it is the clean output that is refused, not the tainted input."""
    g = join_launders_one_tainted_input(parent)
    compose, publish, record = (
        _node(g, n) for n in ("ComposeDigest", "PublishDigest", "RecordSeen")
    )
    compose["output"] = "Untrusted<Digest>"
    publish["inputs"] = ["Untrusted<Digest>" if i == "Digest" else i for i in publish["inputs"]]
    publish["output"] = "Untrusted<PublishedDigest>"
    record["inputs"] = [
        "Untrusted<PublishedDigest>" if i == "PublishedDigest" else i for i in record["inputs"]
    ]
    record["output"] = "Untrusted<RunReport>"
    for node in (compose, publish, record):
        node.pop("ensures", None)
        node.pop("requires", None)
    return g


# ── The per-item map ─────────────────────────────────────────────────


def map_child_takes_another_type(child: dict) -> dict:
    """Make the child graph take a `FeedDocument` where the parent maps `FeedItem`s.

    The parent still supplies `List<Untrusted<FeedItem>>`. The element-wise check
    requires the list's element type to *be* the child's boundary input, so the
    composition is rejected as a cross-graph signature mismatch."""
    g = copy.deepcopy(child)
    old, new = "Untrusted<FeedItem>", "Untrusted<FeedDocument>"
    g["parameters"] = [new if p == old else p for p in g["parameters"]]
    classify = _node(g, "ClassifyItem")
    classify["inputs"] = [new if i == old else i for i in classify["inputs"]]
    return g


def map_launders_trust_past_child(child: dict) -> dict:
    """Remove the child's discharger, and let the parent go on calling its
    elements clean.

    The child is rewritten to carry `Untrusted<_>` from its input to its
    terminals: nothing in it raises trust, so on its own it is a valid graph. The
    parent still declares `List<ItemVerdict>`. A per-item node's output elements
    must be what the child's terminals emit, trust label included, so the only
    place an element's trust can rise is a discharger *inside* the child — and
    there is none. Rejected as a cross-graph signature mismatch."""
    g = copy.deepcopy(child)
    classify, summarise, skip = (_node(g, n) for n in ("ClassifyItem", "SummariseItem", "SkipItem"))
    classify.pop("discharges_trust")
    classify["output"] = "keep: Untrusted<ClassifiedItem> | drop: Untrusted<DroppedItem>"
    summarise["inputs"] = [
        "Untrusted<ClassifiedItem>" if i == "ClassifiedItem" else i for i in summarise["inputs"]
    ]
    summarise["output"] = "Untrusted<ItemVerdict>"
    skip["inputs"] = ["Untrusted<DroppedItem>"]
    skip["output"] = "Untrusted<ItemVerdict>"
    for node in (summarise, skip):
        node.pop("ensures", None)
    return g


# ── Where the network sits ───────────────────────────────────────────


def http_downstream_of_a_model(parent: dict) -> dict:
    """Give `ComposeDigest` — a model-holding node, downstream of every model —
    the HTTP client.

    A digest writer that can fetch is the exfiltration channel the graph's shape
    exists to rule out. The *validator accepts this*: nothing about edges, trust
    or joins is wrong, and a general analysis has no opinion on where a graph
    fetches. It is rejected by the service's own shape check."""
    g = copy.deepcopy(parent)
    compose = _node(g, "ComposeDigest")
    compose["inputs"] = [*compose["inputs"], HTTP]
    return g


def fetched_content_unlabelled(parent: dict) -> dict:
    """Declare `FetchFeeds`'s output clean: `FeedBatch`, not `Untrusted<FeedBatch>`.

    The edge into `ParseFeeds` still type-checks, because a trusted value may
    stand where an untrusted one is wanted. So the *validator accepts this too*,
    and that is the limit worth seeing: trust enters where a node declares it, and
    nothing infers that what an HTTP handle returned came from outside. It is
    rejected by the service's own shape check, which is a check written for this
    graph."""
    g = copy.deepcopy(parent)
    _node(g, "FetchFeeds")["output"] = "FeedBatch"
    return g


# name → (which graph it rewrites, the rewiring). The evaluation pins each.
FEED_VARIANTS = {
    "join_missing_position": ("feed-triage", join_missing_position),
    "join_on_exclusive_branches": ("feed-triage", join_on_exclusive_branches),
    "join_launders_one_tainted_input": ("feed-triage", join_launders_one_tainted_input),
    "join_carries_taint_through": ("feed-triage", join_carries_taint_through),
    "map_child_takes_another_type": ("triage-item", map_child_takes_another_type),
    "map_launders_trust_past_child": ("triage-item", map_launders_trust_past_child),
    "http_downstream_of_a_model": ("feed-triage", http_downstream_of_a_model),
    "fetched_content_unlabelled": ("feed-triage", fetched_content_unlabelled),
}
