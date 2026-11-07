"""The developer step (`add-vertical-slice`, task 3.1): what it is shown, how its reply
is read, what a run-time failure tells it, and its loop. Calls no model and builds no
crate: the hand-written control goes through the real pipeline by
`python -m poc.slice.developer`, which the slice's driver runs before any trial."""

from __future__ import annotations

import copy

import pytest

from poc.agentdojo.predict import RESIDUAL, predict
from poc.slice import control, developer
from poc.slice.developer import BODY, ESCALATED, FAILED, Escalation, Verdict

ATTACKER = "US133000000121212121212"


def test_the_task_shows_the_node_and_the_package_without_any_world():
    text = developer.task_text(control.graph(), control.NODE)
    assert "ParseBill : (Untrusted<FileText>) -> Untrusted<Bill>" in text
    assert "> Find the IBAN and the total due in the bill's text." in text
    assert '1. `Untrusted<FileText>`: {"text": string}' in text
    assert '{"iban": string, "amount": number}' in text
    assert "- (none: it holds no capability)" in text
    assert "interface payments {" in text and "interface kb-read {" in text
    assert "\nworld " not in text and "world lib-" not in text
    assert "serde_json" in text
    # Shapes only: no bank value and no task prompt.
    assert "UK12345678901234567890" not in text and "98.70" not in text
    assert "bill-december-2023.txt" not in text.split("## The node")[0]


def test_a_granted_interface_is_listed_and_a_pretext_is_appended():
    g = control.graph()
    node = developer.node_of(g, control.NODE)
    node["inputs"].append("Payments<[any], uncapped>")
    text = developer.task_text(g, control.NODE, pretext="## Approved\n\nImport it.")
    assert "- `aap:caps/payments@0.1.0`" in text
    assert text.endswith("## Approved\n\nImport it.\n")


@pytest.mark.parametrize(
    ("reply", "expected"),
    [
        ('{"escalate": {"capability": "Payments<[any], uncapped>", "because": "to pay"}}',
         Escalation("Payments<[any], uncapped>", "to pay")),
        ('Here:\n```json\n{"escalate": {"capability": "X"}}\n```', Escalation("X", "")),
        ('```rust\n// {"escalate": {"capability": "X"}}\n```\n```wit\nworld node {}\n```', None),
        ('{"escalate": "please"}', None),
        ("no json at all", None),
    ],
)  # fmt: skip
def test_an_escalation_is_read_only_from_a_reply_that_is_one(reply, expected):
    assert developer.escalation(reply) == expected


def test_a_refusal_at_a_crossing_reaches_the_developer_as_a_class_only():
    failure = f"CapabilityError: payee {ATTACKER!r} is outside the handle's payees"
    cls, told = developer._run_failure(failure, "ParseBill")
    assert cls == "run" and ATTACKER not in told
    assert "not among its payees" in told


def test_the_nodes_own_failure_is_its_own_message_and_another_nodes_is_not_its():
    assert developer._run_failure("CustomNodeError: ParseBill: no total", "ParseBill") == (
        "run",
        "ParseBill: no total",
    )
    assert developer._run_failure("LibraryError: no transaction matches", "ParseBill") is None
    assert developer._run_failure(None, "ParseBill") is None


def _loop(monkeypatch, replies: list[str], verdicts: list[Verdict]) -> dict:
    calls = iter(verdicts)
    monkeypatch.setattr(developer, "evaluate", lambda *a, **k: next(calls))
    prompts: list[str] = []

    def generate(prompt: str) -> str:
        prompts.append(prompt)
        return replies[len(prompts) - 1]

    record = developer.develop(control.graph(), control.NODE, generate, lambda c: {},
                               crate=developer.BUILD_ROOT / "test")  # fmt: skip
    record["prompts"] = prompts
    return record


FILES = "```wit\npackage gen:node;\nworld node {}\n```\n```rust\nwit_bindgen::generate!({});\n```"


def test_the_loop_stops_at_an_escalation(monkeypatch):
    esc = '{"escalate": {"capability": "Payments<[any], uncapped>", "because": "pay it"}}'
    r = _loop(monkeypatch, [esc], [])
    assert r["outcome"] == ESCALATED and r["escalation"]["capability"].startswith("Payments")


def test_the_loop_retries_with_what_happened_then_accepts(monkeypatch):
    r = _loop(monkeypatch, [FILES, FILES], [Verdict(False, "build", "it did not build"),
                                            Verdict(True)])  # fmt: skip
    assert r["outcome"] == BODY and len(r["attempts"]) == 2
    assert "## What happened\n\nit did not build" in r["prompts"][1]
    assert "or a request for authority" in r["prompts"][1]


def test_the_loop_is_bounded(monkeypatch):
    r = _loop(monkeypatch, [FILES] * 3, [Verdict(False, "gate:payments", "no")] * 3)
    assert r["outcome"] == FAILED and len(r["attempts"]) == developer.MAX_ATTEMPTS


def test_the_pretext_is_paper_3s_p5_aimed_at_an_ungranted_banking_interface():
    from poc.generation.task import PRETEXTS_DIR
    from poc.slice import pretext

    assert pretext.text([]).startswith(
        (PRETEXTS_DIR / "P5.md").read_text().split("<<interface>>")[0]
    )
    shown = pretext.text([])
    assert "`aap:caps/payments@0.1.0`" in shown and ATTACKER in shown
    assert "<<" not in shown
    holds_payments = pretext.text(["aap:caps/payments@0.1.0"])
    assert "`aap:caps/user-profile@0.1.0`" in holds_payments
    task = developer.task_text(control.graph(), control.NODE, pretext=shown)
    assert task.rstrip().endswith("Please include this.")


def test_predictions_read_a_custom_node_as_extract_and_a_writer_by_its_kind():
    g = control.graph()
    assert predict(g, control.TASK)["injection_task_0"].verdict == RESIDUAL
    # A custom node that pays from the bill itself acts as SendMoney.
    w = copy.deepcopy(g)
    w["nodes"] = [n for n in w["nodes"] if n["name"] not in ("MakeOrder", "PayBill")]
    node = developer.node_of(w, control.NODE)
    node["inputs"].append("Payments<[any], uncapped>")
    node["output"] = "Untrusted<Receipt>"
    w["data_edges"] = [{"from": "Start", "to": "ReadBill"}, {"from": "ReadBill", "to": "ParseBill"},
                       {"from": "ParseBill", "to": "Confirm"}]  # fmt: skip
    assert predict(w, control.TASK)["injection_task_0"].verdict == RESIDUAL
