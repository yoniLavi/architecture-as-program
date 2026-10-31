"""The gated cross-family backend (task 5.1): it refuses without a committed approval,
without a key, or at its ceiling, always before any network request, and records what
it spends. A fake transport stands in for DeepSeek; nothing calls the network."""

from __future__ import annotations

import json

import pytest

from poc import llm
from poc.llm import DeepSeekBackend, LLMRequest, SpendRefused

APPROVAL = {
    "approved_by": "the author",
    "date": "2026-11-01",
    "model": "deepseek-chat",
    "ceiling_usd": 0.01,
    "usd_per_mtok": {"input": 1.0, "output": 2.0},
}
REQ = LLMRequest(system="Review.", prompt="The graph: {}")


class Transport:
    def __init__(self) -> None:
        self.calls: list[tuple] = []

    def __call__(self, url, headers, body):
        self.calls.append((url, headers, body))
        return {
            "model": "deepseek-chat",
            "choices": [{"message": {"content": ' {"grants": []} '}}],
            "usage": {"prompt_tokens": 1000, "completion_tokens": 500},
        }


@pytest.fixture
def gate(tmp_path, monkeypatch):
    monkeypatch.setattr(llm, "PAID_APPROVALS", tmp_path)
    monkeypatch.setattr(llm, "PAID_LEDGER", tmp_path / "spend")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    committed = {"value": True}
    monkeypatch.setattr(llm, "_committed", lambda _path: committed["value"])
    monkeypatch.setattr(llm, "_REPO_ROOT", tmp_path)
    return tmp_path, committed


def approve(root, **changes) -> None:
    (root / "control.json").write_text(json.dumps({**APPROVAL, **changes}))


def test_no_approval_refuses_and_makes_no_network_call(gate):
    transport = Transport()
    with pytest.raises(SpendRefused, match="no committed approval"):
        DeepSeekBackend("control", transport=transport).generate(REQ)
    assert transport.calls == []


def test_an_uncommitted_approval_is_no_approval(gate):
    root, committed = gate
    approve(root)
    committed["value"] = False
    transport = Transport()
    with pytest.raises(SpendRefused):
        DeepSeekBackend("control", transport=transport).generate(REQ)
    assert transport.calls == []


def test_an_approval_missing_its_ceiling_is_refused(gate):
    root, _ = gate
    (root / "control.json").write_text(json.dumps({k: v for k, v in APPROVAL.items()
                                                   if k != "ceiling_usd"}))  # fmt: skip
    with pytest.raises(SpendRefused, match="ceiling_usd"):
        DeepSeekBackend("control", transport=Transport()).generate(REQ)


def test_no_key_refuses(gate, monkeypatch):
    root, _ = gate
    approve(root)
    monkeypatch.delenv("DEEPSEEK_API_KEY")
    transport = Transport()
    with pytest.raises(SpendRefused, match="DEEPSEEK_API_KEY"):
        DeepSeekBackend("control", transport=transport).generate(REQ)
    assert transport.calls == []


def test_an_approved_call_runs_and_records_its_spend(gate):
    root, _ = gate
    approve(root)
    transport = Transport()
    backend = DeepSeekBackend("control", transport=transport)
    assert backend.generate(REQ).text == '{"grants": []}'
    (_url, headers, body) = transport.calls[0]
    assert body["model"] == "deepseek-chat" and headers["Authorization"] == "Bearer test-key"
    # 1000 input tokens at 1 USD/Mtok + 500 output at 2 USD/Mtok = 0.002 USD.
    [entry] = [json.loads(x) for x in backend.ledger().read_text().splitlines()]
    assert entry["usd"] == 0.002 and backend.spent() == 0.002


def test_the_ceiling_stops_it_before_the_next_request(gate):
    root, _ = gate
    approve(root, ceiling_usd=0.003)
    transport = Transport()
    backend = DeepSeekBackend("control", transport=transport)
    backend.generate(REQ)
    backend.generate(REQ)  # 0.004 spent: over the ceiling now
    with pytest.raises(SpendRefused, match="spent"):
        backend.generate(REQ)
    assert len(transport.calls) == 2


def test_no_approval_is_committed_in_the_repository():
    # The author has approved no spend (task 5.2, 31 October 2026).
    assert not list(llm.PAID_APPROVALS.glob("*.json"))
