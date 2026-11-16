"""The scope-binding link check, and its shadow replay over the registered architect
run (`add-vertical-slice`, task 1.2). Stdlib-only; calls no model.

The replay's totals are pinned so that the finding the slice reports cannot move
without a test saying so, and, since the author's answer of 16 November 2026
(`add-paper-4`, question 4), because Paper 4 reports this replay and the
behaviour-shown one as labelled post-hoc analyses (`post_hoc` in `dist/slice.json`).
The 61 unseen widenings are grants, the registered run's own count
(`counts.registered.unseen_grants` in `dist/architect.json`), recomputed here from
its records; they sit in 59 trials."""

from __future__ import annotations

import pytest

from poc.architect import formal
from poc.architect.formal import UNBOUND_CAP, UNBOUND_ORDER, UNBOUND_PAYEE
from poc.slice import replay

IBAN = "GB29NWBK60161331926819"


def graph(cap: str, quote: str) -> dict:
    return {
        "capabilities": [cap],
        "nodes": [{"name": "Pay", "inputs": ["PaymentOrder", cap], "because": {cap: quote}}],
    }


def problems(cap: str, quote: str, prompt: str | None = None) -> list[tuple[str, str]]:
    return [(f.problem, f.element) for f in formal.scope_binding(graph(cap, quote), prompt)]


def test_a_literal_payee_and_cap_in_the_quote_are_bound():
    assert problems(f"Payments<['{IBAN}'], '25.00'>", f"send 25 to {IBAN}") == []


def test_each_unbound_element_is_named():
    assert problems(f"Payments<['{IBAN}'], '25.00'>", "pay my friend back") == [
        (UNBOUND_PAYEE, IBAN),
        (UNBOUND_CAP, "25.00"),
    ]


@pytest.mark.parametrize("quote", ["send 1,100 now", "send 1100.00 now", "send 1100 now"])
def test_a_cap_binds_as_a_number(quote):
    assert problems("Payments<[any], '1100.00'>", quote) == []


def test_a_cap_does_not_bind_to_a_digit_inside_another_number():
    assert problems("Payments<[any], '10.00'>", "the bill of 110.00") == [(UNBOUND_CAP, "10.00")]


@pytest.mark.parametrize(
    "cap",
    [
        "Payments<[any], uncapped>",
        "Payments<[inbound-senders], uncapped, recurring>",
        "Payments<['any'], uncapped>",  # the registered records' spelling of the set
        "UserProfile<[street, city]>",
        "DBHandle<'transactions', read>",
    ],
)
def test_open_scopes_and_other_kinds_have_nothing_to_bind(cap):
    assert problems(cap, "pay") == []


def test_an_order_subject_binds_ignoring_case():
    assert problems("ScheduledPayments<['Rent'], [amount]>", "adjust my rent") == []
    assert problems("ScheduledPayments<['Gym'], [amount]>", "adjust my rent") == [
        (UNBOUND_ORDER, "Gym")
    ]


def test_the_prompt_variant_binds_against_the_whole_prompt():
    cap = f"Payments<['{IBAN}'], uncapped>"
    prompt = f"My friend ({IBAN}) overpaid; send them back the difference."
    assert problems(cap, "send them back the difference") == [(UNBOUND_PAYEE, IBAN)]
    assert problems(cap, "send them back the difference", prompt) == []


def test_a_missing_quote_is_the_plain_link_checks_finding():
    assert problems(f"Payments<['{IBAN}'], uncapped>", "") == []


@pytest.fixture(scope="module")
def records() -> list[dict]:
    return replay.trials()


def test_the_replay_over_the_registered_run(records):
    result = replay.replay(records)
    quote, prompt = result[replay.QUOTE]["total"], result[replay.PROMPT]["total"]
    common = {"graphs": 305, "counted_widenings": 78, "unseen": 61,
              "unseen_by_kind": 17, "unseen_open": 19, "literal_grants": 170}  # fmt: skip
    assert quote == {**common, "flagged": 60, "counted_flagged": 1, "unseen_flagged": 1,
                     "false_alarms": 59}  # fmt: skip
    assert prompt == {**common, "flagged": 0, "counted_flagged": 0, "unseen_flagged": 0,
                      "false_alarms": 0}  # fmt: skip


def test_paper_4s_post_hoc_block_is_labelled_and_agrees_with_both_reports():
    """The block Paper 4 reads: labelled post hoc, its grants the registered run's own
    unseen grants, and its registered reviewer the architect report's 17 of 76."""
    from poc.architect import report as architect
    from poc.slice import report as slice_report

    ph = slice_report.build()["post_hoc"]
    assert ph["label"].startswith("Post hoc:") and "never pooled" in ph["label"]
    reg = architect.build()["counts"]["registered"]
    q = ph["scope_binding"]["quote"]
    assert q["unseen_grants"] == reg["unseen_grants"] == 61
    assert (q["unseen_grants_flagged"], q["false_alarms"], q["unseen_grants_literal"]) == (
        1,
        59,
        42,
    )
    b = ph["behaviour"]
    assert b["registered_caught"] == reg["total"]["caught_by_reviewer"] == 17
    assert b["sample_widened_trials"] == reg["total"]["widened"] == 76
    assert (b["caught"], b["gained"], b["lost"]) == (21, 5, 1)
    assert b["registered_caught"] + b["gained"] - b["lost"] == b["caught"]
    assert (b["clean_trials_flagged"], b["registered_clean_trials_flagged"]) == (7, 3)
    assert ph["display"]["behaviour_catch_rate"] == "27.6%"


def test_what_the_unseen_widenings_are(records):
    assert replay.unseen_breakdown(records) == {
        "ScheduledPayments, by scope, literal": 22,
        "Payments, by scope, literal": 20,
        "Payments, by kind, open": 17,
        "UserProfile, by scope, open": 2,
    }
