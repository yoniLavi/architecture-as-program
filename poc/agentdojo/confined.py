"""The node library on the confined tier: each authority-holding entry as a WASM
component (task 3.4).

One component per family (`poc/sandbox/rust/lib_*`), each world importing exactly
the interface its entry's capability kind maps to. Values and parameters cross as
JSON. The host binds the interface to the same handle objects the host tier uses,
so a payment outside the handle's scope traps at the crossing, exactly as an
off-allowlist fetch does, before the bank's tool runs.

The pure entries — `Start`, the selectors, `Compose` — hold no capability and have
no component: they run on the host tier (design, task 3.4). `CONFINABLE` names the
entries that do.

Needs `wasmtime` (the `poc` group).
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from ..bank import BankError
from ..sandbox.host import Sandbox, record
from ..sandbox.interfaces import (
    INFERENCE_LLM,
    KB_READ,
    PAYMENTS,
    PAYMENTS_RECURRING,
    RESPONSE_CHANNEL,
    SCHEDULED_PAYMENTS,
    USER_PROFILE,
)
from ..values import DeliveryConfirmation
from .library import CATALOGUE, READER, RESPOND, LibraryError, compact

# Library entry → the component that is its body on the confined tier.
COMPONENTS: dict[str, str] = {
    **{name: "lib_read" for name, e in CATALOGUE.items() if e.family == READER},
    "SendMoney": "lib_send_money",
    "ScheduleTransaction": "lib_schedule_transaction",
    "UpdateScheduledTransaction": "lib_update_scheduled",
    "UpdateUserInfo": "lib_update_user_info",
    "Respond": "lib_respond",
    "Extract": "lib_extract",
}
CONFINABLE = frozenset(COMPONENTS)


def _result(call: Callable[[], Any]) -> Any:
    """A bank operation as a WIT `result`: a refusal by the bank is the `err` case.
    A scope refusal (`CapabilityError`) is not caught: it traps at the crossing."""
    from wasmtime.component import Variant as WitVariant

    try:
        return WitVariant("ok", compact(call()))
    except BankError as e:
        return WitVariant("err", str(e))


def _caps(entry: str, handle: Any) -> dict[str, dict[str, Callable[..., Any]]]:
    if CATALOGUE[entry].family == READER:
        return {KB_READ: {"lookup": handle.read}}
    if entry == "SendMoney":
        return {PAYMENTS: {"send": lambda r, a, s, d: _result(lambda: handle.send(r, a, s, d))}}
    if entry == "ScheduleTransaction":

        def schedule(r: str, a: float, s: str, d: str, rec: bool) -> Any:
            return _result(lambda: handle.schedule(r, a, s, d, rec))

        return {PAYMENTS_RECURRING: {"schedule": schedule}}
    if entry == "UpdateScheduledTransaction":

        def update(id: int, recipient, amount, subject, date, recurring) -> Any:
            changes = dict(
                recipient=recipient, amount=amount, subject=subject, date=date, recurring=recurring
            )
            return _result(lambda: handle.update(id, **changes))

        return {SCHEDULED_PAYMENTS: {"update": update}}
    if entry == "UpdateUserInfo":

        def update_user(first_name, last_name, street, city) -> Any:
            changes = dict(first_name=first_name, last_name=last_name, street=street, city=city)
            return _result(lambda: handle.update(**changes))

        return {USER_PROFILE: {"update": update_user}}
    if entry == "Respond":

        def send(text: str) -> Any:
            c = handle.send(text)
            return record(session=c.session_id, delivered=c.delivered)

        return {RESPONSE_CHANNEL: {"send": send}}
    if entry == "Extract":

        def infer(system: str, prompt: str, task: str) -> str:
            return handle.infer(system=system, prompt=prompt, task=task)

        return {INFERENCE_LLM: {"infer": infer}}
    raise LibraryError(f"{entry} has no component")


def body(node: dict) -> Callable[..., Any]:
    """The confined body of a library node: its component, linked to its handle."""
    entry = CATALOGUE[node["uses"]]
    component = COMPONENTS.get(entry.name)
    if component is None:
        raise LibraryError(f"{entry.name} holds no capability and has no component")
    params = compact({**node.get("params", {}), "entry": entry.name, "node": node["name"]})

    def run(*args: Any) -> Any:
        *data, handle = args
        out = Sandbox(component, _caps(entry.name, handle)).call(
            "run", params, [compact(d) for d in data]
        )
        if out.tag == "err":
            raise LibraryError(f"{node['name']} ({component}): {out.payload}")
        value = json.loads(out.payload)
        if entry.family == RESPOND:
            return DeliveryConfirmation(session_id=value["session"], delivered=value["delivered"])
        return value

    return run
