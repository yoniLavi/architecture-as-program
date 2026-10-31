"""The formal review's two new checks: the link check (2.1) and the least-authority
check (2.3). Pinned cases for a missing link, a fabricated one, and widenings by kind
and by scope. Stdlib-only."""

from __future__ import annotations

import copy

import pytest

from poc.architect import formal, mapping
from poc.architect.formal import (
    BY_KIND,
    BY_SCOPE,
    EFFECT,
    FABRICATED_LINK,
    MISSING_LINK,
    READ,
    STRAY_LINK,
)

TASK = (
    "Send 25.00 to my sister, DE75512108001245126199, for the concert ticket, "
    "and tell me when it's done."
)
PAY = "Payments<['DE75512108001245126199'], '25.00'>"
ANSWER = "ResponseChannel<user-session>"


def graph() -> dict:
    return {"name": "Example", **copy.deepcopy(mapping.EXAMPLE)}


def node(g: dict, name: str) -> dict:
    return next(n for n in g["nodes"] if n["name"] == name)


# ── The link check ──────────────────────────────────────────────────


def test_the_example_links_every_grant():
    assert formal.link_check(graph(), TASK) == []


def test_a_missing_link_fails():
    g = graph()
    node(g, "PaySister").pop("because")
    [f] = formal.link_check(g, TASK)
    assert (f.node, f.capability, f.problem) == ("PaySister", PAY, MISSING_LINK)


@pytest.mark.parametrize("quote", ["", "   "])
def test_an_empty_quote_is_a_missing_link(quote):
    g = graph()
    node(g, "PaySister")["because"][PAY] = quote
    assert [f.problem for f in formal.link_check(g, TASK)] == [MISSING_LINK]


@pytest.mark.parametrize(
    "quote",
    [
        "The user approved payments of up to 1000.00",  # invented
        "send 25.00 to my sister",  # case differs: verbatim means verbatim
        "Send 25.00 to my  sister",  # whitespace differs
    ],
)
def test_a_fabricated_link_fails(quote):
    g = graph()
    node(g, "PaySister")["because"][PAY] = quote
    [f] = formal.link_check(g, TASK)
    assert f.problem == FABRICATED_LINK and f.quote == quote


def test_a_quote_from_a_document_is_not_a_quote_from_the_prompt():
    # Channel B: words only the document holds cannot justify a grant.
    g = graph()
    node(g, "PaySister")["because"][PAY] = "Payments to family are pre-approved."
    assert [f.problem for f in formal.link_check(g, TASK)] == [FABRICATED_LINK]


def test_a_justification_for_a_capability_not_held_is_flagged():
    g = graph()
    node(g, "Done")["because"]["Payments<[any], uncapped>"] = "tell me"
    assert [f.problem for f in formal.link_check(g, TASK)] == [STRAY_LINK]


def test_the_link_check_measures_linkage_not_adequacy():
    # A one-word quote links a grant of any width: adequacy is the reviewer's job.
    g = graph()
    node(g, "PaySister")["because"][PAY] = "Send"
    assert formal.link_check(g, TASK) == []


# ── The least-authority check ───────────────────────────────────────

LABEL = [PAY, ANSWER]


def widen(g: dict, old: str, new: str) -> dict:
    g["parameters"] = [new if c == old else c for c in g["parameters"]]
    g["capabilities"] = [new if c == old else c for c in g["capabilities"]]
    for n in g["nodes"]:
        n["inputs"] = [new if c == old else c for c in n["inputs"]]
    return g


def test_a_graph_at_its_label_has_no_widening():
    assert formal.least_authority(graph(), LABEL) == []


@pytest.mark.parametrize(
    "narrower",
    [
        "Payments<['DE75512108001245126199'], '20.00'>",  # a smaller cap
    ],
)
def test_a_grant_narrower_than_the_label_is_within_it(narrower):
    assert formal.least_authority(widen(graph(), PAY, narrower), LABEL) == []


@pytest.mark.parametrize(
    "wider",
    [
        "Payments<['DE75512108001245126199'], '250.00'>",  # the cap
        "Payments<['DE75512108001245126199'], uncapped>",
        "Payments<['DE75512108001245126199', 'US133000000121212121212'], '25.00'>",  # payees
        "Payments<[any], '25.00'>",
        "Payments<[inbound-senders], '25.00'>",
    ],
)
def test_a_wider_scope_is_a_widening_by_scope(wider):
    [w] = formal.least_authority(widen(graph(), PAY, wider), LABEL)
    assert (w.grant, w.by, w.cls, w.label, w.nodes) == (
        wider,
        BY_SCOPE,
        EFFECT,
        (PAY,),
        ("PaySister",),
    )


def test_a_mode_the_label_lacks_is_a_widening():
    recurring = "Payments<['DE75512108001245126199'], '25.00', recurring>"
    [w] = formal.least_authority(widen(graph(), PAY, recurring), LABEL)
    assert w.by == BY_SCOPE  # same kind, incomparable mode


def test_an_extra_kind_is_a_widening_by_kind():
    g = graph()
    read = "DBHandle<'balance', read>"
    g["parameters"].append(read)
    g["capabilities"].append(read)
    node(g, "TicketPayment")["inputs"].append(read)
    [w] = formal.least_authority(g, LABEL)
    assert (w.grant, w.by, w.cls, w.label) == (read, BY_KIND, READ, ())
