"""The baseline's MCP server: AgentDojo's banking tools over stdio (task 4.1).

Checks the protocol, and that a model sees what AgentDojo's own tool-calling
pipeline would show it: the same tools, the same argument schemas, the same
formatted results, and the environment written back for the scorer. Needs the
`agentdojo` group; calls no model."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

pytest.importorskip("agentdojo")

from agentdojo.agent_pipeline.tool_execution import tool_result_to_str
from agentdojo.functions_runtime import FunctionsRuntime

from poc.agentdojo.harness import suite

ROOT = Path(__file__).resolve().parent.parent


def _serve(tmp_path: Path, messages: list[dict]) -> tuple[list[dict], dict]:
    env = suite().load_and_inject_default_environment({})
    state = tmp_path / "state.json"
    state.write_text(json.dumps({"environment": json.loads(env.model_dump_json()), "calls": []}))
    out = subprocess.run(
        [sys.executable, "-W", "ignore", "-m", "poc.agentdojo.mcp_server", str(state)],
        input="".join(json.dumps(m) + "\n" for m in messages),
        capture_output=True,
        text=True,
        cwd=ROOT,
        check=True,
    )
    return [json.loads(line) for line in out.stdout.splitlines()], json.loads(state.read_text())


def _call(i: int, name: str, args: dict) -> dict:
    return {"jsonrpc": "2.0", "id": i, "method": "tools/call",
            "params": {"name": name, "arguments": args}}  # fmt: skip


def test_the_server_offers_agentdojos_own_tools(tmp_path):
    replies, _ = _serve(
        tmp_path,
        [
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
        ],
    )
    assert [r["id"] for r in replies] == [1, 2]  # no reply to a notification
    offered = {t["name"]: t for t in replies[1]["result"]["tools"]}
    functions = FunctionsRuntime(suite().tools).functions
    assert set(offered) == set(functions) and len(offered) == 11
    for name, f in functions.items():
        assert offered[name]["inputSchema"] == f.parameters.model_json_schema()


def test_a_call_runs_agentdojos_runtime_and_writes_the_environment_back(tmp_path):
    args = {"recipient": "US133000000121212121212", "amount": 5, "subject": "s",
            "date": "2022-01-01"}  # fmt: skip
    replies, state = _serve(
        tmp_path,
        [_call(1, "get_most_recent_transactions", {"n": 2}), _call(2, "send_money", args)],
    )
    env = suite().load_and_inject_default_environment({})
    expected, _ = FunctionsRuntime(suite().tools).run_function(
        env, "get_most_recent_transactions", {"n": 2}
    )
    assert replies[0]["result"]["content"][0]["text"] == tool_result_to_str(expected)
    assert [c["function"] for c in state["calls"]] == ["get_most_recent_transactions", "send_money"]
    assert (
        state["environment"]["bank_account"]["transactions"][-1]["recipient"] == args["recipient"]
    )


def test_a_tool_error_is_returned_as_an_error_result(tmp_path):
    replies, state = _serve(tmp_path, [_call(1, "update_scheduled_transaction", {"id": 999})])
    result = replies[0]["result"]
    assert result["isError"] and "999" in result["content"][0]["text"]
    assert state["calls"][0]["error"]
