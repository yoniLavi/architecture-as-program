"""Shared fixtures for the feed-triage tests: sample feeds and a local server.

No test touches the network. A test that needs real HTTP semantics — a redirect,
an oversized body, a slow response — gets them from `serving(...)`, an HTTP
server bound to 127.0.0.1 on an ephemeral port for the duration of a `with`.

Everything here lives in the `poc.feeds` package, because the feed evaluation (a
build step) uses the same server and the same hostile documents; this module is
the test suite's one import for them.
"""

from __future__ import annotations

from poc.feeds.corpus import HERE as _CORPUS
from poc.feeds.fixture_server import Server, ok, redirect, serving, slow
from poc.feeds.samples import ATOM, RSS

# The classic entity-expansion bomb, and an entity naming a local file.
BILLION_LAUGHS = (_CORPUS / "entity_expansion.xml").read_text()
EXTERNAL_ENTITY = (_CORPUS / "external_entity.xml").read_text()

__all__ = [
    "ATOM",
    "BILLION_LAUGHS",
    "EXTERNAL_ENTITY",
    "RSS",
    "Server",
    "ok",
    "redirect",
    "serving",
    "slow",
]
