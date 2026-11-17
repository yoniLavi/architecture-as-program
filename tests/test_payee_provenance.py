"""`known-payees` across the tiers, under a bind, and on the pinned cases
(add-payee-provenance, tasks 1.3 to 2.5).

The rule's host-side cases are in `tests/test_banking_kinds.py`. Here:

* **1.3** the confined banking adapter enforces the class: no WIT changes, because
  the scope lives in the handle the component calls;
* **1.4** a bound `[known-payees]` grant refuses a bound new payee, and the reason the
  architect would see is the fixed payee line, with no IBAN in it.

Needs the `poc` and `agentdojo` groups; skipped without them.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

pytest.importorskip("wasmtime")
pytest.importorskip("agentdojo")

from poc.agentdojo import harness
from poc.agentdojo.harness import (
    ANY_GRANT,
    KNOWN_GRANT,
    rewrite_known_payees,
    run_pair,
)
from poc.agentdojo.library import confinable
from poc.agentdojo.standins import OracleModel

ROOT = Path(__file__).resolve().parent.parent
BANKING_WIT_SHA256 = "e4eecc77c5d7c3b36a7161eab59a826d651ac03529335bf2a1b0ede7a7da2e2f"
CAPS_WIT_SHA256 = "9856904d96e7f9ee0988dd1bb0bac1120bf46a0a88af6421ec868cb1ddf8b5b9"
ATTACKER = "US133000000121212121212"
BILL_PAYEE = "UK12345678901234567890"
KNOWN = "CH9300762011623852957"  # paid in the default history ("Pizza party")
APPLE = "US122000000121212121212"  # paid in the default history; two digits from ATTACKER
PAYEE_LINE = "a Payments grant refused it: the payee is not among its payees"


def _plan(recipient: str) -> OracleModel:
    """Task 0's extractor, answering with `recipient` and the bill's other fields."""
    return OracleModel({"ExtractInvoice": {"recipient": recipient, "amount": 98.7,
                                           "subject": "Car Rental", "date": "2022-04-01"}})  # fmt: skip


def _task0(*, bound: bool) -> dict:
    g = harness.bound_graph() if bound else harness.load_graph(harness.BOUND_GRAPH)
    return rewrite_known_payees(g)


def _sends(calls: list[dict]) -> list[str]:
    return [c["args"]["recipient"] for c in calls if c["function"] == "send_money"]


# ── 1.3 the confined tier ────────────────────────────────────────────


def test_the_wit_is_unchanged():
    for name, sha in (("banking.wit", BANKING_WIT_SHA256), ("caps.wit", CAPS_WIT_SHA256)):
        path = ROOT / "poc" / "sandbox" / "wit" / name
        assert hashlib.sha256(path.read_bytes()).hexdigest() == sha, name


@pytest.mark.parametrize("bound", [False, True], ids=["unbound", "bound"])
def test_the_confined_adapter_pays_a_known_payee_and_refuses_a_new_one(bound):
    g = _task0(bound=bound)
    sandbox = tuple(confinable(g))
    assert "PayBill" in sandbox  # the writer is its component, not a host body
    known = run_pair(g, "user_task_0", backend=_plan(KNOWN), sandbox=sandbox)
    assert known.failure is None and _sends(known.calls) == [KNOWN]
    new = run_pair(g, "user_task_0", backend=_plan(ATTACKER), sandbox=sandbox)
    assert new.failure and "outside the handle's payees" in new.failure
    assert _sends(new.calls) == []


# ── 1.4 the bind, and the refusal the architect would see ────────────


def _spy_binds(monkeypatch) -> list[dict]:
    import poc.runtime as runtime

    seen: list[dict] = []
    real = runtime.bind_from

    def spy(handle, grant, spec, inputs):
        out = real(handle, grant, spec, inputs)
        seen.append({"grant": grant, "scope": out._scope})
        return out

    monkeypatch.setattr(runtime, "bind_from", spy)
    return seen


def test_a_bound_known_payee_grant_refuses_a_bound_new_payee(monkeypatch):
    """The bind is satisfied (the writer pays exactly its input), and the class
    refuses it: both must permit a payment."""
    seen = _spy_binds(monkeypatch)
    r = run_pair(_task0(bound=True), "user_task_0", backend=_plan(BILL_PAYEE))
    (bound,) = seen
    assert bound["grant"] == KNOWN_GRANT and bound["scope"].literal == frozenset({BILL_PAYEE})
    assert r.failure and "outside the handle's payees" in r.failure
    assert _sends(r.calls) == []


def test_a_bound_known_payee_is_paid(monkeypatch):
    seen = _spy_binds(monkeypatch)
    r = run_pair(_task0(bound=True), "user_task_0", backend=_plan(KNOWN))
    assert len(seen) == 1 and r.failure is None and _sends(r.calls) == [KNOWN]


def test_the_architects_reason_is_the_fixed_payee_line_with_no_iban():
    from poc.architect import measure

    r = run_pair(_task0(bound=True), "user_task_0", backend=_plan(ATTACKER))
    assert ATTACKER in (r.failure or "")  # the message names it; the reason must not
    reason = measure.refusal(r.failure)
    assert reason == measure.Reason(measure.REFUSED, PAYEE_LINE)
    assert ATTACKER not in repr(reason) and "US13" not in repr(reason)


# ── 2.1 the rewrite touches only the grant ───────────────────────────


def _case_graphs() -> dict[str, dict]:
    from tests import known_payee_cases

    return {c.name: c.graph for c in known_payee_cases.cases()}


def _diff(a, b, path=()) -> list[tuple]:
    """Every place `a` and `b` differ, as (path, a's, b's)."""
    if isinstance(a, dict) and isinstance(b, dict):
        out = []
        for k in sorted(set(a) | set(b), key=str):
            if k not in a or k not in b:
                out.append(((*path, k), k in a, k in b))
            else:
                out += _diff(a[k], b[k], (*path, k))
        return out
    if isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        return [
            d for i, (x, y) in enumerate(zip(a, b, strict=True)) for d in _diff(x, y, (*path, i))
        ]
    return [] if a == b else [(path, a, b)]


def test_the_rewrite_replaces_the_grant_and_nothing_else():
    from poc.agentdojo.library import check_graph

    graphs = _case_graphs()
    assert set(graphs) == {"task-0-bound", "split-answer", "d1-bound"}
    for name, before in graphs.items():
        after = rewrite_known_payees(before)
        check_graph(after)  # the validator accepts all three
        assert ANY_GRANT not in str(after), name
        changes = _diff(before, after)
        assert changes, name
        for path, old, new in changes:
            if path and path[-1] in (ANY_GRANT, KNOWN_GRANT):  # a re-keyed bind or `because`
                assert (old, new) in ((True, False), (False, True)), (name, path)
            else:
                assert (old, new) == (ANY_GRANT, KNOWN_GRANT), (name, path, old, new)
        # re-keying back gives the source exactly
        back = {KNOWN_GRANT: ANY_GRANT}
        assert _rekey(after, back) == before, name


def _rekey(value, table):
    if isinstance(value, dict):
        return {table.get(k, k): _rekey(v, table) for k, v in value.items()}
    if isinstance(value, list):
        return [_rekey(v, table) for v in value]
    return table.get(value, value) if isinstance(value, str) else value
