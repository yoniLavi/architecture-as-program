"""The feed parser: bounded items out of documents anyone could have written.

`poc/feeds` is the least confined code in the service — a pure node, on the host
tier, reading attacker-controlled XML — so what matters here is less that it
parses a feed than what it refuses to do with one.
"""

from __future__ import annotations

import pytest

from poc.feeds import (
    MAX_DEPTH,
    MAX_ITEMS,
    MAX_TEXT,
    MAX_TITLE,
    FeedError,
    item_id,
    parse_feed,
    parse_xml,
    plain_text,
)
from tests.feed_fixtures import ATOM, BILLION_LAUGHS, EXTERNAL_ENTITY, RSS

URL = "https://feeds.example.com/rss"


def _rss(items: str) -> str:
    return f'<?xml version="1.0"?><rss version="2.0"><channel>{items}</channel></rss>'


# ── The two formats ──────────────────────────────────────────────────


def test_rss_items_are_parsed_in_document_order():
    items = parse_feed(URL, RSS)
    assert [i.title for i in items] == [
        "A capability model for WebAssembly components",
        "Version 2.0 released",
        "Weekend photos",
    ]
    first = items[0]
    assert first.link == "https://feeds.example.com/posts/wasm-capabilities"
    assert first.feed == URL
    assert first.published == "Thu, 08 Oct 2026 09:00:00 GMT"
    assert first.text == "We propose a capability model for WASM."  # markup stripped


def test_atom_entries_are_parsed_with_their_alternate_link():
    items = parse_feed("https://blog.example.net/atom", ATOM)
    assert [i.title for i in items] == [
        "Prompt injection in coding agents",
        "Thoughts on gardening",
    ]
    assert items[0].link == "https://blog.example.net/injection"  # not the rel="self" link
    assert items[1].link == "https://blog.example.net/garden"  # a link with no rel is alternate
    assert items[1].text == "Opinion: tomatoes are fine."  # xhtml content, flattened
    assert items[0].published == "2026-10-08T10:00:00Z"


def test_an_entry_with_nothing_to_triage_is_skipped():
    assert parse_feed(URL, _rss("<item><link>https://a.example/</link></item>")) == []


# ── The id ───────────────────────────────────────────────────────────


def test_the_id_is_a_digest_the_feed_did_not_choose():
    hostile = _rss("<item><title>t</title><guid>../../state/seen</guid></item>")
    (item,) = parse_feed(URL, hostile)
    assert item.id == item_id(URL, "../../state/seen")
    assert len(item.id) == 32 and all(c in "0123456789abcdef" for c in item.id)


def test_the_id_is_stable_and_scoped_to_its_feed():
    assert parse_feed(URL, RSS)[0].id == parse_feed(URL, RSS)[0].id
    assert parse_feed(URL, RSS)[0].id != parse_feed("https://other.example/rss", RSS)[0].id


# ── What it refuses ──────────────────────────────────────────────────


def test_entity_expansion_is_refused_not_performed():
    """A billion laughs: the document is rejected at its DOCTYPE, before any
    entity is defined, let alone expanded."""
    with pytest.raises(FeedError, match="DOCTYPE"):
        parse_feed(URL, BILLION_LAUGHS)


def test_an_external_entity_is_refused_not_fetched():
    with pytest.raises(FeedError, match="DOCTYPE"):
        parse_feed(URL, EXTERNAL_ENTITY)


def test_any_doctype_is_refused_even_a_harmless_one():
    doc = '<?xml version="1.0"?><!DOCTYPE rss><rss><channel/></rss>'
    with pytest.raises(FeedError, match="DOCTYPE"):
        parse_feed(URL, doc)


def test_an_undeclared_entity_is_malformed_not_empty():
    with pytest.raises(FeedError, match="malformed"):
        parse_feed(URL, _rss("<item><title>&undeclared;</title></item>"))


@pytest.mark.parametrize("doc", ["", "not xml", "<rss><channel>", "<a></b>", "\x00\x01"])
def test_malformed_xml_is_a_feed_error(doc):
    with pytest.raises(FeedError):
        parse_feed(URL, doc)


def test_an_oversized_document_is_refused_before_parsing(monkeypatch):
    monkeypatch.setattr("poc.feeds.MAX_DOCUMENT_BYTES", 100)
    with pytest.raises(FeedError, match="exceeds"):
        parse_feed(URL, RSS)


def test_a_deeply_nested_document_is_refused():
    deep = "<a>" * (MAX_DEPTH + 1) + "</a>" * (MAX_DEPTH + 1)
    with pytest.raises(FeedError, match="nests deeper"):
        parse_xml(deep)


def test_a_document_with_too_many_elements_is_refused(monkeypatch):
    monkeypatch.setattr("poc.feeds.MAX_ELEMENTS", 10)
    with pytest.raises(FeedError, match="more than 10 elements"):
        parse_feed(URL, RSS)


# ── What it bounds ───────────────────────────────────────────────────


def test_the_item_count_is_capped():
    many = _rss("".join(f"<item><title>t{i}</title><guid>{i}</guid></item>" for i in range(300)))
    assert len(parse_feed(URL, many)) == MAX_ITEMS
    assert len(parse_feed(URL, many, max_items=5)) == 5


def test_every_text_field_is_truncated():
    long = _rss(f"<item><title>{'T' * 5000}</title><description>{'d' * 50000}</description></item>")
    (item,) = parse_feed(URL, long)
    assert len(item.title) == MAX_TITLE and len(item.text) == MAX_TEXT


@pytest.mark.parametrize(
    "link",
    [
        "javascript:alert(1)",
        "data:text/html,x",
        "file:///etc/passwd",
        "https://a.example/ with space",
        'https://a.example/"x',
        "//no-scheme.example/",
    ],
)
def test_a_link_that_is_not_plainly_http_is_dropped(link):
    (item,) = parse_feed(URL, _rss(f"<item><title>t</title><link>{link}</link></item>"))
    assert item.link == ""


def test_scripts_and_styles_are_not_text():
    fragment = "<p>Hello</p><script>steal()</script><style>p{}</style> <b>world</b>"
    assert plain_text(fragment, 100) == "Hello world"


def test_whitespace_is_collapsed_so_an_item_is_one_line():
    (item,) = parse_feed(URL, _rss("<item><title>a\n\n# heading\n- list</title></item>"))
    assert "\n" not in item.title and item.title == "a # heading - list"
