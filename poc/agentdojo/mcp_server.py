"""AgentDojo's banking tools as an MCP server, for the undefended baseline.

`claude -p` starts this as a subprocess (stdio, newline-delimited JSON-RPC) and
calls the tools the model chooses. Each tool runs through AgentDojo's own
`FunctionsRuntime.run_function` on the task's environment, and returns what
AgentDojo's own tool-calling pipeline would show a model: `tool_result_to_str`
(YAML) of the result, or the runtime's error string. The tool names, descriptions
and argument schemas are AgentDojo's, from the same `Function` objects.

State lives in one JSON file, written by the baseline before the run and read back
after it: the environment (rewritten after every call, so the scorer sees what the
tools did) and the log of calls. Stdlib-only apart from AgentDojo, and small on
purpose: it is part of the harness the baseline's numbers rest on.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from agentdojo.agent_pipeline.tool_execution import tool_result_to_str
from agentdojo.functions_runtime import FunctionsRuntime

from .harness import suite

PROTOCOL = "2025-06-18"


class State:
    def __init__(self, path: Path) -> None:
        self.path = path
        data = json.loads(path.read_text())
        s = suite()
        self.env = s.environment_type.model_validate(data["environment"])
        self.runtime = FunctionsRuntime(s.tools)
        self.data = data

    def call(self, name: str, args: dict[str, Any]) -> tuple[str, bool]:
        result, error = self.runtime.run_function(self.env, name, args)
        self.data["calls"].append({"function": name, "args": args, "error": error})
        self.data["environment"] = json.loads(self.env.model_dump_json())
        self.path.write_text(json.dumps(self.data))
        return (error, True) if error is not None else (tool_result_to_str(result), False)


def tools() -> list[dict[str, Any]]:
    return [
        {
            "name": f.name,
            "description": f.description,
            "inputSchema": f.parameters.model_json_schema(),
        }
        for f in FunctionsRuntime(suite().tools).functions.values()
    ]


def handle(state: State, message: dict[str, Any]) -> dict[str, Any] | None:
    method, mid = message.get("method"), message.get("id")
    if mid is None:
        return None  # a notification
    if method == "initialize":
        result: dict[str, Any] = {
            "protocolVersion": message.get("params", {}).get("protocolVersion", PROTOCOL),
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "agentdojo-banking", "version": "1"},
        }
    elif method == "tools/list":
        result = {"tools": tools()}
    elif method == "tools/call":
        params = message.get("params", {})
        text, is_error = state.call(params.get("name", ""), params.get("arguments") or {})
        result = {"content": [{"type": "text", "text": text}], "isError": is_error}
    elif method == "ping":
        result = {}
    else:
        return {"jsonrpc": "2.0", "id": mid, "error": {"code": -32601, "message": method}}
    return {"jsonrpc": "2.0", "id": mid, "result": result}


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    state = State(Path(args[0]))
    for line in sys.stdin:
        if not line.strip():
            continue
        reply = handle(state, json.loads(line))
        if reply is not None:
            sys.stdout.write(json.dumps(reply) + "\n")
            sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
