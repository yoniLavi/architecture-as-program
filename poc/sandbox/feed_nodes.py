"""Component-tier adapters for the feed-triage graphs' capability-holding nodes.

The same job as `poc/sandbox/nodes.py`, for the nine nodes of
`graphs/feed-triage.json` and `graphs/triage-item.json` that hold a capability.
Each adapter lowers the node's input into WIT records, links the component
against exactly the interfaces its `with` clause maps to — closures over the same
Python handle objects the host tier uses — runs it, and lifts the result back.

Two things here that the customer-support adapters did not need:

* **State.** `state-read` and `state-rw` are bound to a `StateHandle`'s methods.
  `get` returns `option<string>`, which crosses as `None` or a `str`.
* **A join.** `ComposeDigest` takes two data inputs; its adapter takes them as two
  leading arguments and passes two parameters to the component's export. A join
  needs no encoding at the boundary — positions are just parameters.

`Untrusted<_>` is unwrapped on the way in and re-applied on the way out by the
adapter of each node whose graph type says so. WIT carries the payload; the label
is the validator's and the runtime's, and an adapter that dropped it would make
the trace disagree with the graph (the tier-equality test compares exactly that).
"""

from __future__ import annotations

from ..feed_values import (
    Category,
    ClassifiedItem,
    Digest,
    DroppedItem,
    FeedBatch,
    FeedDocument,
    FeedItem,
    FetchFailure,
    Importance,
    ItemVerdict,
    PublishedDigest,
    RunInfo,
    RunReport,
    Selection,
    SubscriptionList,
    Tick,
)
from ..handles import (
    Clock,
    HTTPClient,
    InferenceLLM,
    Notifier,
    ReadStateHandle,
    ReadWriteStateHandle,
)
from ..values import Untrusted, Variant
from .host import Sandbox, record
from .interfaces import CLOCK, HTTP_CLIENT, INFERENCE_LLM, NOTIFIER, STATE_READ, STATE_RW

# ── Lowering and lifting ─────────────────────────────────────────────
#
# WIT enum cases are kebab-case (`must-read`); the domain enums' values are
# snake_case (`must_read`), which is also what a contract literal compares against.


def _enum_out(member: Category | Importance) -> str:
    return member.value.replace("_", "-")


def _item_out(item: FeedItem):
    return record(
        id=item.id,
        feed=item.feed,
        title=item.title,
        link=item.link,
        published=item.published,
        text=item.text,
    )


def _item_in(wit) -> FeedItem:
    return FeedItem(
        id=wit.id,
        feed=wit.feed,
        title=wit.title,
        link=wit.link,
        published=wit.published,
        text=wit.text,
    )


def _verdict_out(v: ItemVerdict):
    return record(
        id=v.id,
        feed=v.feed,
        title=v.title,
        link=v.link,
        category=_enum_out(v.category),
        importance=_enum_out(v.importance),
        summary=v.summary,
        kept=v.kept,
    )


def _verdict_in(wit) -> ItemVerdict:
    return ItemVerdict(
        id=wit.id,
        feed=wit.feed,
        title=wit.title,
        link=wit.link,
        category=Category(wit.category.replace("-", "_")),
        importance=Importance(wit.importance.replace("-", "_")),
        summary=wit.summary,
        kept=wit.kept,
    )


def _infer(llm: InferenceLLM):
    def infer(system: str, prompt: str, task: str) -> str:
        return llm.infer(system=system, prompt=prompt, task=task)

    return {INFERENCE_LLM: {"infer": infer}}


# ── FeedTriage ───────────────────────────────────────────────────────


def start_run_sandbox(tick: Tick, clock: Clock) -> RunInfo:
    """`StartRun`: imports exactly `wasi:clocks/wall-clock`, satisfied by the
    host's `Clock` handle rather than by any WASI runtime context."""

    def now():
        t = clock.now()
        return record(seconds=t.seconds, nanoseconds=t.nanoseconds)

    out = Sandbox("node_start_run", {CLOCK: {"now": now}}).call("run", record(reason=tick.reason))
    return RunInfo(date=out.date, started=out.started)


def load_subscriptions_sandbox(run: RunInfo, subscriptions: ReadStateHandle) -> SubscriptionList:
    """`LoadSubscriptions`: imports exactly `state-read`."""
    sandbox = Sandbox("node_load_subscriptions", {STATE_READ: {"get": subscriptions.get}})
    out = sandbox.call("run", record(date=run.date, started=run.started))
    return SubscriptionList(urls=tuple(out.urls))


def fetch_feeds_sandbox(subs: SubscriptionList, http: HTTPClient) -> Untrusted[FeedBatch]:
    """`FetchFeeds`: imports exactly `http-client`.

    `fetch` returns a `result<string, string>`: a transport failure is the `err`
    case, a value the component records. A request outside the allowlist is not —
    the handle raises `CapabilityError`, which crosses the boundary as a trap."""
    from wasmtime.component import Variant as WitVariant

    def fetch(url: str):
        result = http.fetch(url)
        return WitVariant("ok", result.body) if result.ok else WitVariant("err", result.error)

    def get(url: str) -> str:
        return http.get(url)

    sandbox = Sandbox("node_fetch_feeds", {HTTP_CLIENT: {"fetch": fetch, "get": get}})
    out = sandbox.call("run", record(urls=list(subs.urls)))
    return Untrusted(
        FeedBatch(
            documents=tuple(FeedDocument(url=d.url, body=d.body) for d in out.documents),
            failures=tuple(FetchFailure(url=f.url, error=f.error) for f in out.failures),
        )
    )


def drop_seen_sandbox(
    items: tuple[Untrusted[FeedItem], ...], seen: ReadStateHandle
) -> tuple[Untrusted[FeedItem], ...]:
    """`DropSeen`: imports exactly `state-read`. The component has `get` and no
    `put`, so it cannot record an item however it is asked to."""
    sandbox = Sandbox("node_drop_seen", {STATE_READ: {"get": seen.get}})
    out = sandbox.call("run", [_item_out(i.value) for i in items])
    return tuple(Untrusted(_item_in(i)) for i in out)


def compose_digest_sandbox(selection: Selection, run: RunInfo, llm: InferenceLLM) -> Digest:
    """`ComposeDigest`: a join. Two data inputs, two export parameters."""
    out = Sandbox("node_compose_digest", _infer(llm)).call(
        "run",
        record(
            entries=[_verdict_out(v) for v in selection.entries],
            considered=list(selection.considered),
        ),
        record(date=run.date, started=run.started),
    )
    return Digest(
        date=out.date,
        overview=out.overview,
        entries=tuple(_verdict_in(v) for v in out.entries),
        considered=tuple(out.considered),
    )


def publish_digest_sandbox(digest: Digest, notifier: Notifier) -> PublishedDigest:
    """`PublishDigest`: imports exactly `notifier`."""

    def notify(message: str) -> bool:
        notifier.notify(message)
        return True

    out = Sandbox("node_publish_digest", {NOTIFIER: {"notify": notify}}).call(
        "run",
        record(
            date=digest.date,
            overview=digest.overview,
            entries=[_verdict_out(v) for v in digest.entries],
            considered=list(digest.considered),
        ),
    )
    return PublishedDigest(date=out.date, considered=tuple(out.considered), published=out.published)


def record_seen_sandbox(published: PublishedDigest, seen: ReadWriteStateHandle) -> RunReport:
    """`RecordSeen`: imports exactly `state-rw` — the only component that does."""
    sandbox = Sandbox(
        "node_record_seen",
        {STATE_RW: {"get": seen.get, "put": seen.put, "delete": seen.delete}},
    )
    out = sandbox.call(
        "run",
        record(
            date=published.date,
            considered=list(published.considered),
            published=published.published,
        ),
    )
    return RunReport(date=out.date, recorded=out.recorded)


# ── TriageItem ───────────────────────────────────────────────────────


def classify_item_sandbox(item: Untrusted[FeedItem], llm: InferenceLLM) -> Variant:
    """`ClassifyItem`: imports exactly `inference-llm`. The verdict comes back as
    a WIT `variant` whose cases (`keep`, `drop`) are the ports the graph routes on."""
    out = Sandbox("node_classify_item", _infer(llm)).call("run", _item_out(item.value))
    category = Category(out.payload.category.replace("-", "_"))
    feed_item = _item_in(out.payload.item)
    if out.tag == "keep":
        importance = Importance(out.payload.importance.replace("-", "_"))
        return Variant(
            "keep", ClassifiedItem(item=feed_item, category=category, importance=importance)
        )
    return Variant("drop", DroppedItem(item=feed_item, category=category))


def summarise_item_sandbox(classified: ClassifiedItem, llm: InferenceLLM) -> ItemVerdict:
    """`SummariseItem`: imports exactly `inference-llm`."""
    out = Sandbox("node_summarise_item", _infer(llm)).call(
        "run",
        record(
            item=_item_out(classified.item),
            category=_enum_out(classified.category),
            importance=_enum_out(classified.importance),
        ),
    )
    return _verdict_in(out)


# The feed-triage graphs' component ports, by node name: the confined-tier
# analogue of `poc.feed_nodes.FEED_REGISTRY`, and the map from node to artifact
# the feed evaluation's derivation reads. Kept apart from `SANDBOX_REGISTRY`,
# which is the set of ports Paper 2 reports on.
FEED_SANDBOX_REGISTRY = {
    "StartRun": start_run_sandbox,
    "LoadSubscriptions": load_subscriptions_sandbox,
    "FetchFeeds": fetch_feeds_sandbox,
    "DropSeen": drop_seen_sandbox,
    "ComposeDigest": compose_digest_sandbox,
    "PublishDigest": publish_digest_sandbox,
    "RecordSeen": record_seen_sandbox,
    "ClassifyItem": classify_item_sandbox,
    "SummariseItem": summarise_item_sandbox,
}

# node name → (graph file stem, component artifact).
FEED_COMPONENTS: dict[str, tuple[str, str]] = {
    "StartRun": ("feed-triage", "node_start_run"),
    "LoadSubscriptions": ("feed-triage", "node_load_subscriptions"),
    "FetchFeeds": ("feed-triage", "node_fetch_feeds"),
    "DropSeen": ("feed-triage", "node_drop_seen"),
    "ComposeDigest": ("feed-triage", "node_compose_digest"),
    "PublishDigest": ("feed-triage", "node_publish_digest"),
    "RecordSeen": ("feed-triage", "node_record_seen"),
    "ClassifyItem": ("triage-item", "node_classify_item"),
    "SummariseItem": ("triage-item", "node_summarise_item"),
}
