"""The banking validation corpus: graphs the validator must accept or reject, pinned.

Each case pins its verdict *and* the reason class that must catch it, by the
validator's own message, as Paper 2's mutation corpus does (`poc/evaluate.py`). A
pass/fail pin would stay green if a case came to be rejected for some other
reason. This corpus is separate from Paper 2's so that no figure there can move.
"""

from __future__ import annotations

import copy
from collections.abc import Callable
from dataclasses import dataclass

from ..graph import validate_graph_dicts

ACCEPTED = "accepted"
REJECTED = "rejected"

# Reason classes, each with the message fragments that identify it.
REASON_CREDENTIALS = "never-granted kind"
REASON_NARROWING = "capability narrowing"
REASON_SCOPE = "unreadable scope"
REASON_MERGE = "merge exclusivity"
REASON_SIGNATURES: dict[str, tuple[str, ...]] = {
    REASON_CREDENTIALS: ("a capability kind no graph may hold",),
    REASON_NARROWING: ("is not assignable to expected",),
    REASON_SCOPE: ("has a scope this kind cannot read",),
    REASON_MERGE: ("which are not exclusive branches of one sum",),
}

PAY = "Payments<['GB29NWBK60161331926819'], '10.00'>"


def refund_graph() -> dict:
    """A two-node graph that refunds a fixed payee: the corpus's base."""
    return {
        "name": "Refund",
        "parameters": ["TaskRequest", PAY],
        "capabilities": [PAY],
        "nodes": [
            {"name": "PlanRefund", "inputs": ["TaskRequest"], "output": "PaymentOrder"},
            {"name": "SendRefund", "inputs": ["PaymentOrder", PAY], "output": "PaymentReceipt"},
        ],
        "data_edges": [{"from": "PlanRefund", "to": "SendRefund"}],
    }


def _grant(graph: dict, cap: str, node: str) -> dict:
    graph["parameters"].append(cap)
    graph["capabilities"].append(cap)
    for n in graph["nodes"]:
        if n["name"] == node:
            n["inputs"].append(cap)
    return graph


def _compose(parent_cap: str, child_cap: str) -> list[dict]:
    """A parent routing `parent_cap` into the refund graph declaring `child_cap`."""
    child = refund_graph()
    child["parameters"][1] = child["capabilities"][0] = child_cap
    child["nodes"][1]["inputs"][1] = child_cap
    parent = {
        "name": "Platform",
        "parameters": ["TaskRequest", parent_cap],
        "capabilities": [parent_cap],
        "nodes": [
            {"name": "Refund", "inputs": ["TaskRequest", parent_cap], "output": "PaymentReceipt"}
        ],
        "data_edges": [],
    }
    return [parent, child]


def lookup_graph(*, exclusive: bool = True) -> dict:
    """The spike's task-15 shape: a lookup that may fail, rejoining a report.

    `FindRefund` emits `found` or `none`; the refund is sent on `found` and skipped
    on `none`, and both outcomes reach position 1 of `Report`, a join that also
    takes an acknowledgement. With `exclusive=False`, `SkipRefund` hangs off the
    request instead of the `none` branch, so both outcomes could arrive."""
    return {
        "name": "RefundIfFound",
        "parameters": ["TaskRequest", "Payments<[inbound-senders], '10.00'>"],
        "capabilities": ["Payments<[inbound-senders], '10.00'>"],
        "nodes": [
            {"name": "Start", "inputs": ["TaskRequest"], "output": "TaskRequest"},
            {
                "name": "FindRefund",
                "inputs": ["TaskRequest"],
                "output": "found: PaymentOrder | none: NoRefund",
            },
            {
                "name": "SendRefund",
                "inputs": ["PaymentOrder", "Payments<[inbound-senders], '10.00'>"],
                "output": "RefundOutcome",
            },
            {
                "name": "SkipRefund",
                "inputs": ["NoRefund" if exclusive else "TaskRequest"],
                "output": "RefundOutcome",
            },
            {"name": "Acknowledge", "inputs": ["TaskRequest"], "output": "Ack"},
            {
                "name": "Report",
                "inputs": ["Ack", "RefundOutcome"],
                "output": "Reply",
                "merge": True,
            },
        ],
        "data_edges": [
            {"from": "Start", "to": "FindRefund"},
            {"from": "Start", "to": "Acknowledge"},
            {"from": "FindRefund.found", "to": "SendRefund"},
            {"from": "FindRefund.none" if exclusive else "Start", "to": "SkipRefund"},
            {"from": "Acknowledge", "to": "Report", "to_input": 0},
            {"from": "SendRefund", "to": "Report", "to_input": 1},
            {"from": "SkipRefund", "to": "Report", "to_input": 1},
        ],
    }


@dataclass(frozen=True)
class Case:
    name: str
    build: Callable[[], list[dict]]
    verdict: str
    reason: str | None = None
    note: str = ""


CASES: tuple[Case, ...] = (
    Case("refund", lambda: [refund_graph()], ACCEPTED, note="the base graph"),
    Case(
        "grant_credentials",
        lambda: [_grant(refund_graph(), "Credentials", "SendRefund")],
        REJECTED,
        REASON_CREDENTIALS,
        "update_password's kind, granted",
    ),
    Case(
        "payments_without_cap",
        lambda: [_grant(refund_graph(), "Payments<['GB29NWBK60161331926819']>", "SendRefund")],
        REJECTED,
        REASON_SCOPE,
        "a Payments type with no cap",
    ),
    Case(
        "quoted_dynamic_payee",
        lambda: [_grant(refund_graph(), "Payments<['any'], '10.00'>", "SendRefund")],
        REJECTED,
        REASON_SCOPE,
        "'any' quoted is a literal payee named any, not the set; found by the architect's run",
    ),
    Case(
        "route_wider_payments",
        lambda: _compose(
            "Payments<['GB29NWBK60161331926819', 'CH9300762011623852957'], '100.00'>", PAY
        ),
        ACCEPTED,
        note="a parent may route more payees and a higher cap",
    ),
    Case(
        "route_higher_cap_to_lower",
        lambda: _compose(PAY, "Payments<['GB29NWBK60161331926819'], '100.00'>"),
        REJECTED,
        REASON_NARROWING,
        "the child declares a cap above what the parent holds",
    ),
    Case(
        "route_other_payee",
        lambda: _compose(PAY, "Payments<['US133000000121212121212'], '10.00'>"),
        REJECTED,
        REASON_NARROWING,
        "the child declares a payee the parent's handle does not cover",
    ),
    Case(
        "route_once_to_recurring",
        lambda: _compose(PAY, "Payments<['GB29NWBK60161331926819'], '10.00', recurring>"),
        REJECTED,
        REASON_NARROWING,
        "the two modes are incomparable",
    ),
    Case(
        "merge_exclusive_branches",
        lambda: [lookup_graph()],
        ACCEPTED,
        note="found and none rejoin one position; at most one arrives",
    ),
    Case(
        "merge_overlapping_branches",
        lambda: [lookup_graph(exclusive=False)],
        REJECTED,
        REASON_MERGE,
        "the skip branch fires on every run, so two values could arrive",
    ),
)


@dataclass(frozen=True)
class Outcome:
    case: Case
    errors: tuple[str, ...]

    @property
    def verdict(self) -> str:
        return REJECTED if self.errors else ACCEPTED

    @property
    def caught_by(self) -> bool:
        """True if a pinned reason class is among the errors (present, not unique)."""
        if self.case.reason is None:
            return not self.errors
        return any(sig in e for e in self.errors for sig in REASON_SIGNATURES[self.case.reason])


def run(cases: tuple[Case, ...] = CASES) -> list[Outcome]:
    return [Outcome(c, tuple(validate_graph_dicts(copy.deepcopy(c.build())))) for c in cases]
