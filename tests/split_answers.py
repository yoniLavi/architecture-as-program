"""The two hand-written split answers to the slice's D2 (add-split-escalation).

The proposal measured both at `fba71d2` with a read-only replay in a session
scratchpad: today's `no_wider` rejected each. They are rebuilt here as fixtures, from
the same hand-built D2 the slice and the bind re-run used (`poc.slice.run.hand_built`),
so the tests that now pass them judge the graphs the proposal's table names.

* `custom_pays()`: an `Extract {iban, total}` inserted before `PayBill`, which stays
  `Custom` and holds `Payments<[any], uncapped>` bound to `in0.iban`, `in0.total`, once.
* `library_pays()`: an `Extract`, then a `Compose` whose `recipient` is `=in0.iban` and
  `amount` is `=in0.total`, then a library `SendMoney` bound to `in0.recipient`,
  `in0.amount`, once. `PayBill` is gone.

In `custom_pays` the writer reads the extractor's untrusted output, and its bind is
labelled `untrusted`. In `library_pays` the library's `SendMoney` takes a trusted
`PaymentOrder` only, so the `Compose` must declare `discharges_trust`, as the control
graph's does: the bind is then labelled `trusted`, although its values come from the
bill. The label follows the declaration, not the values' source.
"""

from __future__ import annotations

import copy

from poc.slice.run import PAY_QUOTE, hand_built

PAY = "Payments<[any], uncapped>"
LLM = "LLMClient<inference>"
FIELDS = {"iban": "string", "total": "number"}
BIND = {"payee": "in0.iban", "amount": "in0.total", "uses": 1}
REQUEST = {"capability": PAY, "split": {"fields": dict(FIELDS)}, "bind": dict(BIND),
           "because": "input 0 carries only the bill's text; no field names the payee"}  # fmt: skip


def before() -> dict:
    """D2 as hand-built: `PayBill` (`Custom`) reads the bill's text and holds no payment."""
    return hand_built("D2")


def _grant(g: dict, *caps: str) -> None:
    for cap in caps:
        if cap not in g["capabilities"]:
            g["capabilities"].append(cap)
            g["parameters"].append(cap)


def request(payee: str = "iban", amount: str = "total") -> dict:
    """The split request, with its fields named `payee` and `amount`."""
    return {**REQUEST, "split": {"fields": {payee: "string", amount: "number"}},
            "bind": {"payee": f"in0.{payee}", "amount": f"in0.{amount}", "uses": 1}}  # fmt: skip


def _extract(fields: dict[str, str] = FIELDS) -> dict:
    return {"name": "ExtractBill", "uses": "Extract",
            "params": {"instruction": "Find the IBAN to pay and the total due in the bill.",
                       "fields": dict(fields)},
            "inputs": ["Untrusted<FileText>", LLM], "output": "Untrusted<BillDue>",
            "because": {LLM: PAY_QUOTE}}  # fmt: skip


def custom_pays(bind: dict | None = BIND) -> dict:
    g = copy.deepcopy(before())
    _grant(g, LLM, PAY)
    i = next(k for k, n in enumerate(g["nodes"]) if n["name"] == "PayBill")
    g["nodes"].insert(i, _extract())
    pay = g["nodes"][i + 1]
    pay["inputs"] = ["Untrusted<BillDue>", PAY]
    pay["because"] = {PAY: PAY_QUOTE}
    if bind is not None:
        pay["bind"] = {PAY: dict(bind)}
    g["data_edges"] = [{"from": "Start", "to": "ReadBill"},
                       {"from": "ReadBill", "to": "ExtractBill"},
                       {"from": "ExtractBill", "to": "PayBill"},
                       {"from": "PayBill", "to": "Confirm"}]  # fmt: skip
    return g


def library_pays(amount: str = "=in0.total", bind: dict | None = None,
                 names: tuple[str, str] = ("iban", "total")) -> dict:  # fmt: skip
    """`names` are the extractor's two fields (the request's), payee then amount."""
    g = copy.deepcopy(before())
    _grant(g, LLM, PAY)
    i = next(k for k, n in enumerate(g["nodes"]) if n["name"] == "PayBill")
    payee_f, amount_f = names
    amount = amount.replace("in0.total", f"in0.{amount_f}")
    g["nodes"][i : i + 1] = [
        _extract({payee_f: "string", amount_f: "number"}),
        {"name": "MakeOrder", "uses": "Compose",
         "params": {"fields": {"recipient": f"=in0.{payee_f}", "amount": amount,
                               "subject": "Bill", "date": "2022-04-01"}},
         "inputs": ["Untrusted<BillDue>"], "output": "PaymentOrder",
         "discharges_trust": True},
        {"name": "PayBill", "uses": "SendMoney",
         "inputs": ["PaymentOrder", PAY], "output": "Receipt",
         "because": {PAY: PAY_QUOTE},
         "bind": {PAY: dict(bind or {"payee": "in0.recipient", "amount": "in0.amount",
                                     "uses": 1})}},
    ]  # fmt: skip
    confirm = next(n for n in g["nodes"] if n["name"] == "Confirm")
    confirm["inputs"][0] = "Receipt"
    del confirm["discharges_trust"]  # nothing untrusted reaches it now
    g["data_edges"] = [{"from": "Start", "to": "ReadBill"},
                       {"from": "ReadBill", "to": "ExtractBill"},
                       {"from": "ExtractBill", "to": "MakeOrder"},
                       {"from": "MakeOrder", "to": "PayBill"},
                       {"from": "PayBill", "to": "Confirm"}]  # fmt: skip
    return g
