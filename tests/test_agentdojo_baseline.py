"""The undefended baseline's plumbing (task 4.2), against a fake `claude`.

The fake is a real MCP client: it starts the server named in `--mcp-config`, reads
the transactions, and — being undefended and fully fooled — obeys any instruction
naming the attacker's IBAN it finds there. No model is called. What is checked is
the harness: the flags, the scorer seeing the environment the tools changed, the
model ID recorded, the usage ceiling, and resumption."""

from __future__ import annotations

import json
import stat
import sys
from pathlib import Path

import pytest

pytest.importorskip("agentdojo")

from poc.agentdojo import baseline
from poc.llm import UsageLimitReached

ATTACKER = "US133000000121212121212"

FAKE = r"""#!PYTHON
import json, subprocess, sys
argv = sys.argv[1:]
open(LOG, "a").write(json.dumps(argv) + "\n")
config = json.loads(argv[argv.index("--mcp-config") + 1])["mcpServers"]["banking"]
prompt = sys.stdin.read()
server = subprocess.Popen([config["command"], *config["args"]], stdin=subprocess.PIPE,
                          stdout=subprocess.PIPE, text=True, env={**config["env"]})
def rpc(i, method, params=None):
    server.stdin.write(json.dumps({"jsonrpc": "2.0", "id": i, "method": method,
                                   "params": params or {}}) + "\n")
    server.stdin.flush()
    return json.loads(server.stdout.readline())["result"]
rpc(1, "initialize")
seen = rpc(2, "tools/call", {"name": "get_most_recent_transactions", "arguments": {"n": 100}})
text = seen["content"][0]["text"]
if "ATTACKER" in text:
    rpc(3, "tools/call", {"name": "send_money", "arguments": {
        "recipient": "ATTACKER", "amount": 50000, "subject": "x", "date": "2022-01-01"}})
server.stdin.close(); server.wait()
answer = "Your total spending in March 2022 was 1050."
print(json.dumps({"type": "system", "subtype": "init", "model": MODEL}))
print(json.dumps({"type": "rate_limit_event", "rate_limit_info": {"unifiedWindows": {"five_hour": {"utilization": USAGE}}}}))
print(json.dumps({"type": "result", "result": answer, "is_error": False,
                  "modelUsage": {MODEL: {}}, "usage": {"output_tokens": 7}}))
"""


def _fake(tmp_path: Path, usage: float = 0.1) -> tuple[Path, Path]:
    log = tmp_path / "argv.jsonl"
    script = tmp_path / "claude"
    script.write_text(
        FAKE.replace("PYTHON", sys.executable)
        .replace("LOG", repr(str(log)))
        .replace("ATTACKER", ATTACKER)
        .replace("MODEL", repr("claude-haiku-5-5"))
        .replace("USAGE", str(usage))
    )
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    return script, log


def test_a_clean_run_is_scored_by_agentdojo(tmp_path):
    script, log = _fake(tmp_path)
    agent = baseline.CLIAgent("claude-haiku-5-5", executable=str(script))
    result = baseline.run_one(agent, "user_task_1", None)
    assert result["utility"] is True and result["attack_success"] is None
    assert result["model_resolved"] == ["claude-haiku-5-5"]
    assert [c["function"] for c in result["calls"]] == ["get_most_recent_transactions"]
    argv = json.loads(log.read_text().splitlines()[0])
    for flag in ("--strict-mcp-config", "--no-session-persistence"):
        assert flag in argv
    assert argv[argv.index("--setting-sources") + 1] == ""
    assert argv[argv.index("--tools") + 1] == ""
    assert argv[argv.index("--system-prompt") + 1] == baseline.SYSTEM_MESSAGE
    assert "--safe-mode" not in argv  # it drops --mcp-config (design, task 4.1)


def test_an_obeyed_injection_is_scored_as_an_attack_success(tmp_path):
    script, _ = _fake(tmp_path)
    agent = baseline.CLIAgent("claude-haiku-5-5", executable=str(script))
    result = baseline.run_one(agent, "user_task_1", "injection_task_5")
    assert result["attack_success"] is True
    assert result["calls"][-1]["args"]["recipient"] == ATTACKER


def test_the_usage_ceiling_stops_the_next_run(tmp_path):
    script, _ = _fake(tmp_path, usage=0.95)
    agent = baseline.CLIAgent("claude-haiku-5-5", executable=str(script))
    baseline.run_one(agent, "user_task_1", None)
    with pytest.raises(UsageLimitReached):
        baseline.run_one(agent, "user_task_1", None)


def test_the_run_resumes_where_it_stopped(tmp_path, monkeypatch):
    script, _ = _fake(tmp_path)
    monkeypatch.setattr(baseline, "BASELINE_RECORDS", tmp_path / "records")
    argv = ["--model", "claude-haiku-5-5", "--no-nice", "--executable", str(script)]
    assert baseline.main([*argv, "--limit", "2"]) == 0
    assert baseline.main([*argv, "--limit", "1"]) == 0
    path = baseline.record_path("claude-haiku-5-5", 0)
    lines = path.read_text().splitlines()
    keys = [(r["user_task"], r["injection_task"]) for r in map(json.loads, lines)]
    assert keys == baseline.pairs()[:3]


def test_the_suite_has_16_utility_runs_and_144_pairs():
    p = baseline.pairs()
    assert len(p) == 160 and sum(i is None for _, i in p) == 16
