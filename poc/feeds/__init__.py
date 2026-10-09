"""Parse RSS 2.0, RSS 1.0 and Atom documents into bounded `FeedItem`s.

This is the first code in the service to touch what the outside world sent, and
it is the least confined: `ParseFeeds` is a pure node — it holds no capability —
and it runs on the host tier. So the parser is written defensively rather than
conveniently, and each defence is a limit with a number on it.

* **No DTD, so no entities.** The XML is read by `pyexpat` directly, with handlers
  that refuse a document type declaration the moment one starts. Without a DTD
  there are only the five predefined entities and numeric character references:
  no internal entity to expand a billion times, no external one to fetch a file
  or a URL. A feed that declares a DOCTYPE is rejected whole — a few very old
  RSS 0.91 feeds do, and losing them is the accepted cost.
* **Bounded input.** A document over `MAX_DOCUMENT_BYTES`, deeper than
  `MAX_DEPTH`, or with more than `MAX_ELEMENTS` elements is rejected before or
  while it is read, not after.
* **Bounded output.** At most `MAX_ITEMS` items per feed, each field truncated to
  a fixed length, markup stripped from the text, and a link kept only if it is
  plainly `http` or `https`.
* **An id the feed did not choose.** `FeedItem.id` is a SHA-256 digest of the
  feed's URL and the entry's own identifier, so it is safe as a store key.

What this does not do is make the text trustworthy. A parsed item is exactly as
adversarial as the bytes it came from; it is merely small and well-formed.
"""

from __future__ import annotations

import hashlib
import html
import re
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from urllib.parse import urlsplit
from xml.parsers import expat

from ..feed_values import FeedItem

MAX_DOCUMENT_BYTES = 5 * 1024 * 1024
MAX_DEPTH = 64
MAX_ELEMENTS = 200_000
MAX_ITEMS = 200
MAX_TITLE = 300
MAX_TEXT = 2000
MAX_LINK = 2000
MAX_PUBLISHED = 64


class FeedError(ValueError):
    """A document that is not a feed this parser will read: malformed XML, a
    declared DOCTYPE, or one of the size limits exceeded."""


# ── XML, without a DTD ─────────────────────────────────────────────


def _local(name: str) -> str:
    """An element's local name, lower-cased, namespace dropped. Feed formats
    disagree about namespaces far more than about names."""
    return name.rsplit("}", 1)[-1].lower()


def parse_xml(body: str) -> ET.Element:
    """Parse `body` into an element tree, refusing any document type declaration.

    Returns the root element; tags and attribute names are bare local names."""
    if len(body.encode("utf-8", errors="replace")) > MAX_DOCUMENT_BYTES:
        raise FeedError(f"document exceeds {MAX_DOCUMENT_BYTES} bytes")

    builder = ET.TreeBuilder()
    depth = 0
    elements = 0

    def forbid(*_args: object) -> None:
        raise FeedError(
            "document declares a DOCTYPE; entity declarations are not read, "
            "so the document is refused"
        )

    def forbid_external(*_args: object) -> int:
        forbid()
        return 0

    def start(name: str, attrs: dict[str, str]) -> None:
        nonlocal depth, elements
        depth += 1
        elements += 1
        if depth > MAX_DEPTH:
            raise FeedError(f"document nests deeper than {MAX_DEPTH} elements")
        if elements > MAX_ELEMENTS:
            raise FeedError(f"document has more than {MAX_ELEMENTS} elements")
        builder.start(_local(name), {_local(k): v for k, v in attrs.items()})

    def end(name: str) -> None:
        nonlocal depth
        depth -= 1
        builder.end(_local(name))

    parser = expat.ParserCreate(namespace_separator="}")
    parser.buffer_text = True
    parser.StartDoctypeDeclHandler = forbid
    parser.EntityDeclHandler = forbid
    parser.UnparsedEntityDeclHandler = forbid
    parser.ExternalEntityRefHandler = forbid_external
    parser.StartElementHandler = start
    parser.EndElementHandler = end
    parser.CharacterDataHandler = builder.data
    try:
        parser.Parse(body, True)
        root = builder.close()
    except expat.ExpatError as e:
        raise FeedError(f"malformed XML: {e}") from e
    except AssertionError as e:  # TreeBuilder: missing or unbalanced elements
        raise FeedError(f"malformed XML: {e}") from e
    return root


# ── Text, without markup ───────────────────────────────────────────


class _TextOnly(HTMLParser):
    """Collect an HTML fragment's text, dropping tags, scripts and styles."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._skipping = 0

    def handle_starttag(self, tag: str, attrs: object) -> None:
        if tag in ("script", "style"):
            self._skipping += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in ("script", "style") and self._skipping:
            self._skipping -= 1

    def handle_data(self, data: str) -> None:
        if not self._skipping:
            self.parts.append(data)


_WHITESPACE = re.compile(r"\s+")


def plain_text(fragment: str, limit: int) -> str:
    """A fragment's visible text: markup removed, whitespace collapsed, truncated."""
    stripper = _TextOnly()
    try:
        stripper.feed(fragment)
        stripper.close()
        text = "".join(stripper.parts)
    except Exception:  # an unparseable fragment is still just text
        text = html.unescape(re.sub(r"<[^>]*>", " ", fragment))
    return _WHITESPACE.sub(" ", text).strip()[:limit]


def _http_link(candidate: str) -> str:
    """`candidate` if it is plainly an http(s) URL, else the empty string."""
    candidate = candidate.strip()
    if len(candidate) > MAX_LINK or any(c.isspace() or c in "<>\"'\\" for c in candidate):
        return ""
    parts = urlsplit(candidate)
    if parts.scheme not in ("http", "https") or not parts.hostname:
        return ""
    return candidate


# ── Items ──────────────────────────────────────────────────────────


def _child_text(entry: ET.Element, *names: str) -> str:
    """The text of the first direct child with one of `names`, descendants' text
    included (an Atom `content type="xhtml"` nests its markup as elements)."""
    for name in names:
        for child in entry:
            if child.tag == name:
                return "".join(child.itertext())
    return ""


def _entry_link(entry: ET.Element) -> str:
    # Atom: <link href="..." rel="alternate">; a link with no rel is an alternate.
    for child in entry:
        is_link = child.tag == "link" and child.get("href")
        if is_link and child.get("rel", "alternate") == "alternate":
            return _http_link(child.get("href", ""))
    # RSS: <link>text</link>.
    return _http_link(_child_text(entry, "link"))


def item_id(feed_url: str, key: str) -> str:
    """The id a `FeedItem` carries: a digest of where it came from and what the
    feed called it. 32 hex characters; no feed chooses any of them."""
    return hashlib.sha256(f"{feed_url}\n{key}".encode()).hexdigest()[:32]


def parse_feed(feed_url: str, body: str, *, max_items: int = MAX_ITEMS) -> list[FeedItem]:
    """The items of one feed document, in document order, at most `max_items`.

    Raises `FeedError` if the document is refused. An entry with neither a title
    nor any text is skipped: there is nothing to triage."""
    root = parse_xml(body)
    items: list[FeedItem] = []
    for entry in root.iter():
        if entry.tag not in ("item", "entry"):
            continue
        if len(items) >= max_items:
            break
        title = plain_text(_child_text(entry, "title"), MAX_TITLE)
        text = plain_text(
            _child_text(entry, "encoded", "content", "description", "summary"), MAX_TEXT
        )
        if not title and not text:
            continue
        link = _entry_link(entry)
        key = _child_text(entry, "guid", "id").strip() or link or title
        published = plain_text(
            _child_text(entry, "pubdate", "published", "updated", "date"), MAX_PUBLISHED
        )
        items.append(
            FeedItem(
                id=item_id(feed_url, key),
                feed=feed_url,
                title=title,
                link=link,
                published=published,
                text=text,
            )
        )
    return items
