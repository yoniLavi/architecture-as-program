"""Every review rendering prints a bound grant with its bind and trust label
(value-bound grants, task 3.1).

One line, in the canonical graph the reviewers see, in the behaviour view and on the
human page: the static type, `bound`, each bound field and its path, the uses, and
the trust label. A graph with no bind renders exactly as before: the registered
reviewer's canonicalisation is replayed against the input hashes its records hold.
"""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

from poc.architect import reviewer
from poc.binds import render_bind
from poc.slice import behaviour, page
from poc.slice.replay import trials

PAY = "Payments<[any], uncapped>"
D2 = Path(__file__).resolve().parent.parent / "poc" / "slice" / "runs" / "slice"
TASK0 = Path(__file__).resolve().parent.parent / "poc" / "agentdojo" / "graphs"


def d2_bound() -> dict:
    """D2's final graph, its `Custom` PayBill bound to the bill's text. Rendering only:
    the library check would refuse an amount read from a string field."""
    g = json.loads((D2 / "user_task_0.D2.json").read_text())["final_graph"]
    g = copy.deepcopy(g)
    pay = next(n for n in g["nodes"] if n["name"] == "PayBill")
    pay["bind"] = {PAY: {"payee": "in0.text", "amount": "in0.text", "uses": 1}}
    return g


def task0_bound() -> dict:
    g = json.loads((TASK0 / "banking-user-task-0.json").read_text())
    pay = next(n for n in g["nodes"] if n["name"] == "PayBill")
    pay["bind"] = {PAY: {"payee": "in0.recipient", "amount": "in0.amount", "uses": 1}}
    return g


def _node(g: dict, name: str) -> dict:
    return next(n for n in g["nodes"] if n["name"] == name)


def test_an_untrusted_bind_renders_on_one_line():
    g = d2_bound()
    line = render_bind(g, _node(g, "PayBill"), PAY)
    assert line == f"{PAY} bound payee=in0.text, amount=in0.text, once; untrusted"
    assert "\n" not in line


def test_a_trusted_bind_after_a_declared_discharge_names_the_discharger():
    g = task0_bound()
    line = render_bind(g, _node(g, "PayBill"), PAY)
    assert line == (
        f"{PAY} bound payee=in0.recipient, amount=in0.amount, once; "
        "trusted (as declared: ExtractInvoice discharges trust)"
    )


def test_uses_and_a_claimed_trusted_render():
    g = task0_bound()
    _node(g, "PayBill")["bind"][PAY].update(uses=3, trusted=True)
    del _node(g, "PayBill")["bind"][PAY]["amount"]
    line = render_bind(g, _node(g, "PayBill"), PAY)
    assert line.startswith(f"{PAY} bound payee=in0.recipient, 3 uses; trusted")
    assert line.endswith(", claimed")


def test_the_canonical_graph_shows_the_bind_with_the_reviewers_names():
    g = task0_bound()
    shown = reviewer.canonical(g)
    (pay,) = [n for n in shown["nodes"] if n.get("bind")]
    assert pay["bind"] == [
        f"{PAY} bound payee=in0.recipient, amount=in0.amount, once; "
        "trusted (as declared: N3 discharges trust)"
    ]
    assert "ExtractInvoice" not in json.dumps(shown)


def test_the_behaviour_view_shows_the_bind():
    g = task0_bound()
    names = {old: f"N{i}" for i, old in enumerate(reviewer._order(g), start=1)}
    view = behaviour.render(g, names)
    assert (
        f"N4 holds it bound: {PAY} bound payee=in0.recipient, amount=in0.amount, once; "
        "trusted (as declared: N3 discharges trust)." in view
    )


def test_the_human_page_lists_the_bound_grant_on_one_line():
    g = d2_bound()
    listing = page._listing(g)
    assert f"    with {PAY} bound payee=in0.text, amount=in0.text, once; untrusted" in listing
    assert f"    with {PAY}\n" not in listing + "\n"


def test_a_graph_without_a_bind_renders_as_before():
    g = json.loads((TASK0 / "banking-user-task-0.json").read_text())
    assert "bind" not in json.dumps(reviewer.canonical(g))
    assert "bound" not in behaviour.render(g)
    assert "bound" not in page._listing(g)


# SHA-256 over `canonical(g)` and `canonical(g, keep_because=True)`, each as
# `json.dumps(…, indent=1)`, for every registered graph in `trials()` order (305 of
# them). Computed with `reviewer.py` as it stood before this change (`619cf35`),
# and equal to the tree's when the bind rendering landed.
CANONICAL_DIGEST = "96a4a6160422c23f0da6e431eaad23828df8bc94df5e070e86fd2df1329b0a0c"


def test_the_registered_reviewers_canonicalisation_is_byte_identical():
    """No registered graph binds, so its canonical view has not moved. (The records'
    own `inputs_sha256` cannot be the check: they hash the prompt as the run built
    it, and later edits to the task text already change that for every record.)"""
    digest = hashlib.sha256()
    records = trials()
    for record in records:
        g = record["architect"]["graph"]
        assert "bind" not in json.dumps(g)
        for keep in (False, True):
            digest.update(json.dumps(reviewer.canonical(g, keep_because=keep), indent=1).encode())
    assert len(records) == 305
    assert digest.hexdigest() == CANONICAL_DIGEST
