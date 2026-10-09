"""Domain value types that flow along the feed-triage signal graphs.

The runtime inhabitants of the types named in `graphs/feed-triage.json` and
`graphs/triage-item.json`, as `poc/values.py` is for the customer-support graph.
Plain frozen dataclasses; `poc/sandbox/wit/caps.wit` declares the same shapes for
the confined tier.

The security-relevant structure is the same as before, at a different scale. What
the outside world sends arrives as `Untrusted[FeedBatch]` and stays wrapped —
through parsing, de-duplication and batching — until `ClassifyItem`, the one
discharger, turns one `Untrusted[FeedItem]` into a `ClassifiedItem` or a
`DroppedItem`: a category and an importance from closed sets, and the item's own
bounded text. That text is the free-text residual. It is still whatever the feed's
author wrote, it still reaches the two model calls downstream, and no type removes
it. What the types do remove is everything else an item might have wanted: there is
no field through which it can name a URL to fetch, a store to write, or another
item to read.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

# ── The run ────────────────────────────────────────────────────────


@dataclass(frozen=True)
class Tick:
    """The boundary input: one firing of the driver's timer."""

    reason: str = "scheduled"


@dataclass(frozen=True)
class RunInfo:
    """What the run knows about itself, read from the clock once, by the only
    node that holds it. `date` is `YYYY-MM-DD` (UTC); `started` is epoch seconds."""

    date: str
    started: int


@dataclass(frozen=True)
class SubscriptionList:
    urls: tuple[str, ...]


# ── What the world sent ────────────────────────────────────────────


@dataclass(frozen=True)
class FeedDocument:
    """One fetched feed, unparsed."""

    url: str
    body: str


@dataclass(frozen=True)
class FetchFailure:
    """A feed that could not be fetched this run. Data, not an exception: one dead
    feed must not fail the tick, and the run record should say which it was."""

    url: str
    error: str


@dataclass(frozen=True)
class FeedBatch:
    """Everything fetched in one run. Always handled wrapped in `Untrusted[...]`."""

    documents: tuple[FeedDocument, ...]
    failures: tuple[FetchFailure, ...] = ()


@dataclass(frozen=True)
class FeedItem:
    """One entry of one feed. Always handled wrapped in `Untrusted[...]` until it
    is classified.

    `id` is a digest the parser computes, not a string the feed chose, so it is
    safe to use as a store key and to carry past the discharge. Every other field
    is the feed author's text, bounded in length by the parser and otherwise
    untouched."""

    id: str
    feed: str
    title: str
    link: str
    published: str
    text: str


# ── After classification ───────────────────────────────────────────


class Category(Enum):
    """The closed category set. A feed item cannot argue its way into a seventh."""

    RELEASE = "release"
    SECURITY = "security"
    RESEARCH = "research"
    TOOLING = "tooling"
    DISCUSSION = "discussion"
    OTHER = "other"


class Importance(Enum):
    """The closed importance set the selection sorts on."""

    MUST_READ = "must_read"
    WORTH_A_LOOK = "worth_a_look"
    SKIP = "skip"


@dataclass(frozen=True)
class ClassifiedItem:
    """An item the classifier kept. Trust is discharged here: the category and
    importance are closed-set values, and `item` carries the bounded residual."""

    item: FeedItem
    category: Category
    importance: Importance


@dataclass(frozen=True)
class DroppedItem:
    """An item the classifier judged not worth a summary."""

    item: FeedItem
    category: Category


@dataclass(frozen=True)
class ItemVerdict:
    """What one item's child run hands back: enough to list it, or to know it was
    considered and dropped."""

    id: str
    feed: str
    title: str
    link: str
    category: Category
    importance: Importance
    summary: str
    kept: bool


# ── The digest ─────────────────────────────────────────────────────


@dataclass(frozen=True)
class Selection:
    """The items that made the digest, most important first, and the id of every
    item considered — kept or not — so that all of them can be marked seen."""

    entries: tuple[ItemVerdict, ...]
    considered: tuple[str, ...]


@dataclass(frozen=True)
class Digest:
    date: str
    overview: str
    entries: tuple[ItemVerdict, ...]
    considered: tuple[str, ...]


@dataclass(frozen=True)
class PublishedDigest:
    """`published` is false for a quiet run: nothing was selected, so nothing was
    written, and the considered items are still marked seen."""

    date: str
    considered: tuple[str, ...]
    published: bool


@dataclass(frozen=True)
class RunReport:
    date: str
    recorded: int
