"""The banking capability handles, and the bank they are bound to.

A bank tool is coarser than banking's threats: AgentDojo's `send_money` pays anyone
any amount. So the banking kinds narrow on their *arguments*, and the scope lives
in the handle, checked at the crossing before the bank is touched — the shape of
an HTTP allowlist (`poc/handles.py`). A request outside the scope raises
`CapabilityError`; what the bank itself refuses (an order that does not exist)
comes back as an error value, because that is a failed operation, not a reach for
authority.

* `PaymentsHandle`          (`Payments<[payees], cap>`)            — send once.
* `RecurringPaymentsHandle` (`Payments<[payees], cap, recurring>`) — schedule an order.
* `ScheduledPaymentsHandle` (`ScheduledPayments<[orders], [fields]>`) — change orders.
* `UserProfileHandle`       (`UserProfile<[fields]>`)              — change profile fields.
* `BankReadHandle`          (`DBHandle<scope, read>`, bank-backed)  — read one collection.

`Credentials` has no handle: no graph is granted it (the validator refuses), and
`provision` refuses it too, so the refusal does not rest on the validator alone.

`Bank` is the boundary to whatever holds the accounts. `MemoryBank` is the one the
tests run against; `poc/agentdojo/adapter.py` backs it with AgentDojo's
`FunctionsRuntime.run_function`, so that the benchmark's own environment changes and
its own scorer reads the result. This module never imports AgentDojo.

Fidelity: host discipline, like every host-tier handle. A hostile host-tier body
could reach the bank object behind the handle; the confined tier is what makes the
handle the only route (`poc/sandbox/`).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Protocol

from type_parser import PaymentsScope, ScheduledScope

from .handles import CapabilityError

# The read collections a bank-backed `DBHandle<scope, read>` may name. A file is
# named by its path after `file:`, so a node can be granted one file and no other.
READ_SCOPES = frozenset({"transactions", "scheduled-transactions", "balance", "iban", "user-info"})
FILE_SCOPE_PREFIX = "file:"


def is_bank_scope(scope: str) -> bool:
    return scope in READ_SCOPES or (
        scope.startswith(FILE_SCOPE_PREFIX) and len(scope) > len(FILE_SCOPE_PREFIX)
    )


class Bank(Protocol):
    """What the banking handles call. Methods mirror AgentDojo's banking tools;
    each write returns the tool's result, or raises `BankError` for a refusal by
    the bank itself."""

    def read(self, scope: str) -> Any: ...

    # What a scope check reads. Not a node's operation, so a bank that records the
    # agent's tool calls (AgentDojo's) must not record it as one.
    def inspect(self, scope: str) -> Any: ...
    def send_money(self, recipient: str, amount: float, subject: str, date: str) -> Any: ...
    def schedule_transaction(
        self, recipient: str, amount: float, subject: str, date: str, recurring: bool
    ) -> Any: ...
    def update_scheduled_transaction(self, id: int, **changes: Any) -> Any: ...
    def update_user_info(self, **changes: Any) -> Any: ...


class BankError(RuntimeError):
    """The bank refused an operation its handle was entitled to ask for."""


def _within_cap(amount: float, cap: Decimal | None) -> bool:
    return cap is None or Decimal(str(amount)) <= cap


def inbound_senders(bank: Bank) -> frozenset[str]:
    """Senders of payments *into* this account: the environment-read payee set.
    A payment in names the account by IBAN, or as 'me' in AgentDojo's data."""
    own = bank.inspect("iban")
    return frozenset(
        t["sender"]
        for t in bank.inspect("transactions")
        if t["recipient"] in (own, "me") and t["sender"] not in (own, "me")
    )


def _check_payment(scope: PaymentsScope, bank: Bank, recipient: str, amount: float) -> None:
    if not isinstance(amount, int | float) or amount <= 0:
        raise CapabilityError(f"payment amount {amount!r} is not a positive number")
    if not _within_cap(amount, scope.cap):
        raise CapabilityError(f"payment of {amount} exceeds the handle's cap of {scope.cap}")
    if "any" in scope.dynamic or recipient in scope.literal:
        return
    if "inbound-senders" in scope.dynamic and recipient in inbound_senders(bank):
        return
    raise CapabilityError(
        f"payee {recipient!r} is outside the handle's payees "
        f"{sorted(scope.literal | scope.dynamic)}"
    )


@dataclass
class PaymentsHandle:
    """`Payments<[payees], cap>`: one payment, to a payee in scope, up to the cap."""

    scope: PaymentsScope
    _bank: Bank = field(repr=False)

    def send(self, recipient: str, amount: float, subject: str, date: str) -> Any:
        _check_payment(self.scope, self._bank, recipient, amount)
        return self._bank.send_money(recipient, amount, subject, date)


@dataclass
class RecurringPaymentsHandle:
    """`Payments<[payees], cap, recurring>`: schedule an order, the cap per payment."""

    scope: PaymentsScope
    _bank: Bank = field(repr=False)

    def schedule(
        self, recipient: str, amount: float, subject: str, date: str, recurring: bool
    ) -> Any:
        _check_payment(self.scope, self._bank, recipient, amount)
        return self._bank.schedule_transaction(recipient, amount, subject, date, recurring)


@dataclass
class ScheduledPaymentsHandle:
    """`ScheduledPayments<[orders], [fields]>`: change only the named fields of the
    standing orders whose subject is named. The order is looked up by id in the
    bank, and its subject is what the scope is checked against, so a node cannot
    reach another order by naming its id."""

    scope: ScheduledScope
    _bank: Bank = field(repr=False)

    def update(self, id: int, **changes: Any) -> Any:
        changes = {k: v for k, v in changes.items() if v is not None}
        if not changes:
            raise CapabilityError("an update must change at least one field")
        outside = sorted(set(changes) - self.scope.fields)
        if outside:
            raise CapabilityError(
                f"fields {outside} are outside the handle's fields {sorted(self.scope.fields)}"
            )
        scheduled = self._bank.inspect("scheduled-transactions")
        order = next((t for t in scheduled if t["id"] == id), None)
        if order is None:
            raise BankError(f"no scheduled transaction with id {id}")
        if order["subject"].lower() not in self.scope.orders:
            raise CapabilityError(
                f"scheduled transaction {id} ({order['subject']!r}) is outside the "
                f"handle's orders {sorted(self.scope.orders)}"
            )
        if "amount" in changes and not isinstance(changes["amount"], int | float):
            raise CapabilityError(f"amount {changes['amount']!r} is not a number")
        if "recipient" in changes and not isinstance(changes["recipient"], str):
            raise CapabilityError(f"recipient {changes['recipient']!r} is not a string")
        return self._bank.update_scheduled_transaction(id, **changes)


@dataclass
class UserProfileHandle:
    """`UserProfile<[fields]>`: change only the named profile fields."""

    fields: frozenset[str]
    _bank: Bank = field(repr=False)

    def update(self, **changes: Any) -> Any:
        changes = {k: v for k, v in changes.items() if v is not None}
        if not changes:
            raise CapabilityError("an update must change at least one field")
        outside = sorted(set(changes) - self.fields)
        if outside:
            raise CapabilityError(
                f"fields {outside} are outside the handle's fields {sorted(self.fields)}"
            )
        return self._bank.update_user_info(**changes)


@dataclass
class BankReadHandle:
    """`DBHandle<scope, read>` bound to the bank: reads one collection, or one file.
    The same surface as `ReadDBHandle`, so a node cannot tell the two apart; each
    record comes back as one JSON string."""

    scope: str
    _bank: Bank = field(repr=False)

    def read(self, key: str = "") -> list[str]:
        value = self._bank.read(self.scope)
        items = value if isinstance(value, list) else [value]
        return [json.dumps(v, sort_keys=True) if not isinstance(v, str) else v for v in items]


# ── An in-memory bank, for tests ────────────────────────────────────


@dataclass
class MemoryBank:
    """A bank in a dict, with AgentDojo's data shapes. Records every write."""

    iban: str = "DE89370400440532013000"
    balance: float = 1810.0
    transactions: list[dict] = field(default_factory=list)
    scheduled: list[dict] = field(default_factory=list)
    user: dict = field(default_factory=dict)
    files: dict[str, str] = field(default_factory=dict)
    writes: list[tuple[str, dict]] = field(default_factory=list)

    def read(self, scope: str) -> Any:
        if scope.startswith(FILE_SCOPE_PREFIX):
            return self.files.get(scope[len(FILE_SCOPE_PREFIX) :], "")
        return {
            "transactions": lambda: [dict(t) for t in self.transactions],
            "scheduled-transactions": lambda: [dict(t) for t in self.scheduled],
            "balance": lambda: self.balance,
            "iban": lambda: self.iban,
            "user-info": lambda: {k: v for k, v in self.user.items() if k != "password"},
        }[scope]()

    inspect = read

    def _next_id(self) -> int:
        return max((t["id"] for t in [*self.transactions, *self.scheduled]), default=0) + 1

    def send_money(self, recipient: str, amount: float, subject: str, date: str) -> Any:
        record = dict(recipient=recipient, amount=amount, subject=subject, date=date)
        self.writes.append(("send_money", record))
        self.transactions.append(
            {"id": self._next_id(), "sender": self.iban, "recurring": False, **record}
        )
        return {"message": f"Transaction to {recipient} for {amount} sent."}

    def schedule_transaction(
        self, recipient: str, amount: float, subject: str, date: str, recurring: bool
    ) -> Any:
        record = dict(recipient=recipient, amount=amount, subject=subject, date=date)
        self.writes.append(("schedule_transaction", {**record, "recurring": recurring}))
        self.scheduled.append(
            {"id": self._next_id(), "sender": self.iban, "recurring": recurring, **record}
        )
        return {"message": f"Transaction to {recipient} for {amount} scheduled."}

    def update_scheduled_transaction(self, id: int, **changes: Any) -> Any:
        order = next((t for t in self.scheduled if t["id"] == id), None)
        if order is None:
            raise BankError(f"Transaction with ID {id} not found.")
        self.writes.append(("update_scheduled_transaction", {"id": id, **changes}))
        order.update(changes)
        return {"message": f"Transaction with ID {id} updated."}

    def update_user_info(self, **changes: Any) -> Any:
        self.writes.append(("update_user_info", dict(changes)))
        self.user.update(changes)
        return {k: v for k, v in self.user.items() if k != "password"}
