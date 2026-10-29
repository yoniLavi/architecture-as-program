"""The banking capability kinds: types, narrowing, the never-granted kind, and the
scope checks at the crossing (Paper 4's AgentDojo harness, tasks 1.1 to 1.3).

None of this needs AgentDojo: the handles are tested over `MemoryBank`."""

from __future__ import annotations

import pytest
from type_parser import CAPABILITY_HEADS, is_assignable, parse_type

from poc.agentdojo import corpus
from poc.bank import (
    BankError,
    BankReadHandle,
    MemoryBank,
    PaymentsHandle,
    RecurringPaymentsHandle,
    ScheduledPaymentsHandle,
    UserProfileHandle,
)
from poc.handles import CapabilityError, World, provision
from poc.llm import StubLLM
from poc.sandbox.interfaces import (
    BANKING_INTERFACES,
    BANKING_KINDS,
    CAPABILITY_INTERFACES,
    CAPABILITY_KINDS,
    CREDENTIALS,
    PAPER2_INTERFACES,
    PAPER2_KINDS,
    PAYMENTS,
    PAYMENTS_RECURRING,
    SCHEDULED_PAYMENTS,
    USER_PROFILE,
    interface_for,
)

FRIEND = "GB29NWBK60161331926819"
ATTACKER = "US133000000121212121212"


def _assignable(actual: str, target: str) -> bool:
    return is_assignable(parse_type(actual), parse_type(target))


# ── 1.1 The kinds, full vocabulary only ──────────────────────────────


def test_the_banking_kinds_are_capabilities_in_the_full_vocabulary_only():
    assert set(BANKING_KINDS) <= CAPABILITY_HEADS
    assert set(BANKING_KINDS) <= set(CAPABILITY_KINDS)
    assert not set(BANKING_KINDS) & set(PAPER2_KINDS)
    assert BANKING_INTERFACES <= CAPABILITY_INTERFACES
    assert not BANKING_INTERFACES & PAPER2_INTERFACES
    # Paper 2 counts seven kinds and eight interfaces, and still does.
    assert len(PAPER2_KINDS) == 7 and len(PAPER2_INTERFACES) == 8


@pytest.mark.parametrize(
    ("cap", "iface"),
    [
        (f"Payments<['{FRIEND}'], '10.00'>", PAYMENTS),
        (f"Payments<['{FRIEND}'], '10.00', recurring>", PAYMENTS_RECURRING),
        ("Payments<[inbound-senders], uncapped>", PAYMENTS),
        ("ScheduledPayments<['Rent'], [recipient, amount]>", SCHEDULED_PAYMENTS),
        ("UserProfile<[street, city]>", USER_PROFILE),
        ("Credentials", CREDENTIALS),
    ],
)
def test_each_kind_maps_to_its_interface(cap, iface):
    assert interface_for(cap) == iface


@pytest.mark.parametrize(
    "cap",
    [
        "Payments<'outgoing'>",  # the spike's unnarrowed form: no payees, no cap
        f"Payments<['{FRIEND}']>",
        f"Payments<['{FRIEND}'], '-1'>",
        f"Payments<['{FRIEND}'], 'ten'>",
        "Payments<[everyone], '10.00'>",
        f"Payments<['{FRIEND}'], '10.00', monthly>",
        "ScheduledPayments<['Rent'], [password]>",
        "ScheduledPayments<[], [amount]>",
        "UserProfile<[password]>",
        "UserProfile<[]>",
    ],
)
def test_an_unreadable_scope_is_rejected_by_the_validator(cap):
    graph = corpus.refund_graph()
    graph["parameters"].append(cap)
    graph["capabilities"].append(cap)
    graph["nodes"][1]["inputs"].append(cap)
    errors = corpus.validate_graph_dicts([graph])
    assert any("has a scope this kind cannot read" in e for e in errors), errors


# ── 1.2 Narrowing at composition ─────────────────────────────────────


def test_payments_narrow_by_payee_inclusion_and_cap():
    wide = f"Payments<['{FRIEND}', 'CH9300762011623852957'], '100.00'>"
    assert _assignable(wide, f"Payments<['{FRIEND}'], '10.00'>")
    assert _assignable(wide, f"Payments<['{FRIEND}'], '100'>")  # 100 == 100.00
    assert not _assignable(f"Payments<['{FRIEND}'], '10.00'>", wide)
    assert not _assignable(f"Payments<['{FRIEND}'], '10.00'>", f"Payments<['{FRIEND}'], '10.01'>")


def test_any_and_uncapped_are_the_top_of_their_orders():
    assert _assignable("Payments<[any], uncapped>", f"Payments<['{FRIEND}'], '10.00'>")
    assert _assignable("Payments<[any], uncapped>", "Payments<[inbound-senders], '5'>")
    assert not _assignable(f"Payments<['{FRIEND}'], uncapped>", "Payments<[any], '1'>")
    assert not _assignable("Payments<[any], '10.00'>", "Payments<[any], uncapped>")


def test_a_dynamic_payee_set_is_not_covered_by_literals():
    # Which payees `inbound-senders` names is known only at run time.
    assert not _assignable(f"Payments<['{FRIEND}'], '10'>", "Payments<[inbound-senders], '10'>")


def test_recurring_and_once_are_incomparable():
    once, rec = f"Payments<['{FRIEND}'], '10'>", f"Payments<['{FRIEND}'], '10', recurring>"
    assert not _assignable(once, rec) and not _assignable(rec, once)


def test_scheduled_payments_and_profile_narrow_by_set_inclusion():
    both = "ScheduledPayments<['Rent', 'Spotify Premium'], [recipient, amount]>"
    assert _assignable(both, "ScheduledPayments<['rent'], [amount]>")  # subjects ignore case
    assert not _assignable("ScheduledPayments<['Rent'], [amount]>", both)
    assert _assignable("UserProfile<[street, city]>", "UserProfile<[street]>")
    assert not _assignable("UserProfile<[street]>", "UserProfile<[street, city]>")


@pytest.mark.parametrize("case", corpus.CASES, ids=lambda c: c.name)
def test_the_banking_corpus_holds_its_pins(case):
    (outcome,) = corpus.run((case,))
    assert outcome.verdict == case.verdict, outcome.errors
    assert outcome.caught_by, (case.reason, outcome.errors)


def test_every_reason_class_is_exercised():
    assert {c.reason for c in corpus.CASES if c.reason} == set(corpus.REASON_SIGNATURES)


# ── 1.3 Scope at the crossing ────────────────────────────────────────


@pytest.fixture
def bank() -> MemoryBank:
    return MemoryBank(
        transactions=[
            {
                "id": 1,
                "sender": "me",
                "recipient": "CH93",
                "amount": 100.0,
                "subject": "Pizza",
                "date": "2022-01-01",
                "recurring": False,
            },
            {
                "id": 5,
                "sender": FRIEND,
                "recipient": "me",
                "amount": 10.0,
                "subject": "Sushi",
                "date": "2022-03-07",
                "recurring": False,
            },
        ],
        scheduled=[
            {
                "id": 6,
                "sender": "DE89",
                "recipient": "SE35",
                "amount": 50.0,
                "subject": "Spotify Premium",
                "date": "2022-04-01",
                "recurring": True,
            },
            {
                "id": 7,
                "sender": "DE89",
                "recipient": "US12",
                "amount": 1100.0,
                "subject": "Rent",
                "date": "2022-04-04",
                "recurring": False,
            },
        ],
        user={
            "first_name": "Emma",
            "last_name": "Johnson",
            "street": "Apple Street 1",
            "city": "Cupertino",
            "password": "password123",
        },
        files={"bill.txt": "pay me"},
    )


def _handle(cap: str, bank: MemoryBank):
    return provision(cap, backend=StubLLM(), stores={}, world=World(bank=bank))


def test_a_payment_in_scope_reaches_the_bank(bank):
    handle = _handle(f"Payments<['{FRIEND}'], '10.00'>", bank)
    assert isinstance(handle, PaymentsHandle) and not hasattr(handle, "schedule")
    handle.send(FRIEND, 10.0, "Refund", "2022-04-01")
    assert bank.writes == [
        (
            "send_money",
            {"recipient": FRIEND, "amount": 10.0, "subject": "Refund", "date": "2022-04-01"},
        )
    ]


def test_an_off_list_payee_is_refused_before_the_bank(bank):
    handle = _handle(f"Payments<['{FRIEND}'], '10.00'>", bank)
    with pytest.raises(CapabilityError, match="outside the handle's payees"):
        handle.send(ATTACKER, 1.0, "x", "2022-04-01")
    assert bank.writes == []


def test_an_over_cap_amount_is_refused_before_the_bank(bank):
    handle = _handle(f"Payments<['{FRIEND}'], '10.00'>", bank)
    with pytest.raises(CapabilityError, match="exceeds the handle's cap"):
        handle.send(FRIEND, 10.01, "x", "2022-04-01")
    with pytest.raises(CapabilityError, match="not a positive number"):
        handle.send(FRIEND, -5.0, "x", "2022-04-01")
    assert bank.writes == []


def test_inbound_senders_is_read_from_the_environment(bank):
    handle = _handle("Payments<[inbound-senders], '10.00'>", bank)
    handle.send(FRIEND, 10.0, "Refund", "2022-04-01")
    with pytest.raises(CapabilityError, match="outside the handle's payees"):
        handle.send("CH93", 1.0, "x", "2022-04-01")  # paid by us, never paid us
    assert len(bank.writes) == 1


def test_recurring_mode_schedules_and_cannot_send(bank):
    handle = _handle(f"Payments<['{FRIEND}'], '50', recurring>", bank)
    assert isinstance(handle, RecurringPaymentsHandle) and not hasattr(handle, "send")
    handle.schedule(FRIEND, 50.0, "Sub", "2022-04-01", True)
    with pytest.raises(CapabilityError):
        handle.schedule(ATTACKER, 50.0, "Sub", "2022-04-01", True)
    assert [w[0] for w in bank.writes] == ["schedule_transaction"]


def test_a_scheduled_update_is_checked_against_the_orders_subject_and_fields(bank):
    handle = _handle("ScheduledPayments<['rent'], [amount]>", bank)
    assert isinstance(handle, ScheduledPaymentsHandle)
    handle.update(7, amount=1200.0)
    with pytest.raises(CapabilityError, match="outside the handle's orders"):
        handle.update(6, amount=1.0)  # Spotify, reached by naming its id
    with pytest.raises(CapabilityError, match="outside the handle's fields"):
        handle.update(7, recipient=ATTACKER)
    with pytest.raises(BankError):
        handle.update(99, amount=1.0)
    assert bank.writes == [("update_scheduled_transaction", {"id": 7, "amount": 1200.0})]


def test_a_profile_update_is_checked_against_its_fields(bank):
    handle = _handle("UserProfile<[street, city]>", bank)
    assert isinstance(handle, UserProfileHandle)
    handle.update(street="Elm Street", city="New York")
    with pytest.raises(CapabilityError, match="outside the handle's fields"):
        handle.update(first_name="Mallory")
    assert bank.user["first_name"] == "Emma"


def test_a_bank_read_handle_reads_one_collection_and_hides_the_password(bank):
    handle = _handle("DBHandle<'user-info', read>", bank)
    assert isinstance(handle, BankReadHandle) and not hasattr(handle, "write")
    assert "password" not in handle.read()[0]
    assert _handle("DBHandle<'file:bill.txt', read>", bank).read() == ["pay me"]


def test_credentials_has_no_handle_and_a_bankless_world_has_no_banking():
    with pytest.raises(ValueError, match="never granted"):
        provision("Credentials", backend=StubLLM(), stores={}, world=World(bank=MemoryBank()))
    with pytest.raises(ValueError, match="needs a bank"):
        provision(f"Payments<['{FRIEND}'], '10'>", backend=StubLLM(), stores={}, world=World())
