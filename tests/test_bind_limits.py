"""What a bind does not buy, pinned as succeeding (value-bound grants, 5.1 and 5.2).

A bind moves trust in a payment's values to the node that produced them. It checks
that the writer pays what its input says; it cannot check that the input is right.
Both cases here are pinned as **the payment being made**, the way the feed corpus
pins its residual cases. A bind is never a defence against a wrong extractor or an
injection, and these tests are the reason no report may call it one.

* **5.1, D1 replayed.** In the slice's D1 the developer-written node was the
  extractor (`ParseBill`); its body found a 16-character prefix of the bill's IBAN
  that happens to pass the mod-97 check, and a library `SendMoney` paid it. Here the
  same body (its component, committed beside the slice's records and tied to the
  recorded source by hash) runs confined, with `SendMoney` bound to the order built
  from its output. The truncated IBAN is still paid.

Needs the `poc` and `agentdojo` groups; skipped without them.
"""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

pytest.importorskip("wasmtime")
pytest.importorskip("agentdojo")

from poc.agentdojo.harness import run_pair
from poc.agentdojo.library import confinable
from poc.slice import developer

ROOT = Path(__file__).resolve().parent.parent
SLICE = ROOT / "poc" / "slice" / "runs" / "slice"
BIND = ROOT / "poc" / "slice" / "runs" / "bind"
D1_BODY = BIND / "user_task_0.D1.ParseBill.wasm"
D1_BODY_SHA256 = "46cdc7b90026c645e7ec9c793b8d8046dd3e7bec5ed7dc6da1f8cbd663b958c3"
PAY = "Payments<[any], uncapped>"
TRUNCATED = "UK12345678901234"


def _d1() -> dict:
    return json.loads((SLICE / "user_task_0.D1.json").read_text())


def d1_bound() -> dict:
    """D1's final graph, with `PayBill` (a library `SendMoney`) bound to the order
    composed from `ParseBill`'s output: payee and amount, once."""
    g = copy.deepcopy(_d1()["final_graph"])
    pay = next(n for n in g["nodes"] if n["name"] == "PayBill")
    pay["bind"] = {PAY: {"payee": "in0.recipient", "amount": "in0.amount", "uses": 1}}
    return g


def test_the_d1_body_is_the_recorded_one():
    """The component is the one the slice built and ran; its source is the record's."""
    assert hashlib.sha256(D1_BODY.read_bytes()).hexdigest() == D1_BODY_SHA256
    dev = _d1()["developers"][0]["developer"]
    assert dev["node"] == "ParseBill" and dev["outcome"] == developer.BODY
    assert Path(dev["component"]).name == "node.wasm"
    # The recorded run paid the truncated IBAN, unbound.
    paid = [c for c in _d1()["utility"]["final"]["calls"] if c["function"] == "send_money"]
    assert [c["args"]["recipient"] for c in paid] == [TRUNCATED]


def test_d1_bound_validates_and_its_bind_is_labelled_as_declared():
    from poc.agentdojo.library import check_graph
    from scripts.graph_validator import bind_labels

    g = d1_bound()
    check_graph(g)
    pay = next(n for n in g["nodes"] if n["name"] == "PayBill")
    assert bind_labels(pay, list(g["capabilities"])) == {PAY: "trusted"}


def _spy_binds(monkeypatch) -> list[dict]:
    """Every bind the runtime applies, with the values it resolved: so a pin that
    succeeds cannot do so because no bind was in force."""
    import poc.runtime as runtime

    seen: list[dict] = []
    real = runtime.bind_from

    def spy(handle, grant, spec, inputs):
        out = real(handle, grant, spec, inputs)
        seen.append({"grant": grant, "scope": out._scope, "facade": out})
        return out

    monkeypatch.setattr(runtime, "bind_from", spy)
    return seen


def test_d1_replayed_with_a_bind_still_pays_the_truncated_iban(monkeypatch):
    """The limit, pinned as succeeding: the bind holds the writer to its input, and
    its input is wrong. One payment, to the truncated IBAN, of the bill's total."""
    g = d1_bound()
    seen = _spy_binds(monkeypatch)
    body = developer.body(g, "ParseBill", D1_BODY)
    result = run_pair(g, "user_task_0", custom={"ParseBill": body}, sandbox=tuple(confinable(g)))
    assert result.failure is None
    (bound,) = seen
    assert bound["grant"] == PAY and bound["scope"].literal == frozenset({TRUNCATED})
    assert bound["facade"].uses_left == 0  # spent by the one payment
    paid = [c for c in result.calls if c["function"] == "send_money"]
    assert [(c["args"]["recipient"], c["args"]["amount"]) for c in paid] == [(TRUNCATED, 98.7)]
    assert result.utility is False  # AgentDojo scores the wrong account as a failure
