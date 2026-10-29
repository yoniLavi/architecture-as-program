"""The undefended baseline: a Claude tool-calling agent on AgentDojo's banking suite.

The same models a graph's nodes run on, with no defence at all: the model sees the
user's prompt and all eleven banking tools, and calls whatever it chooses. It runs
through the logged-in `claude` CLI on the subscription (design, task 4.1), with the
tools served by `mcp_server.py` over AgentDojo's own runtime, and it is scored by
AgentDojo's own `run_task_with_pipeline`.

How each call is made bare (design, "The flags the spike forced"):
* `--setting-sources ""` and `--strict-mcp-config` with this server only, so no
  user, project or plugin configuration and no other MCP server reaches the model;
  not `--safe-mode`, which drops even an explicit `--mcp-config`;
* `--tools ""` and `--allowedTools mcp__banking`: no built-in tool, every banking
  tool callable without a permission prompt;
* AgentDojo's own default system message, with `--system-prompt`;
* a fresh empty working directory outside the repository, removed afterwards, and
  `--no-session-persistence`;
* the environment scrubbed as `ClaudeCLIBackend` scrubs it, so an API key cannot be
  billed in preference to the subscription.

What still reaches the model beyond AgentDojo's pipeline is the CLI's own context
preamble (account email, environment section, model identity and date). The
report states it.

Usage: each call reports the subscription's usage windows; once any is at or above
the ceiling, the runner stops, and a later invocation resumes where it stopped.
Records are one JSON line per run, committed, and the report is rendered from them
(`report.py`). No test or build step runs this against a model.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import time
from collections.abc import Sequence
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from agentdojo.agent_pipeline.agent_pipeline import load_system_message
from agentdojo.agent_pipeline.base_pipeline_element import BasePipelineElement
from agentdojo.functions_runtime import EmptyEnv, Env, FunctionCall, FunctionsRuntime
from agentdojo.types import (
    ChatAssistantMessage,
    ChatMessage,
    ChatToolResultMessage,
    text_content_block_from_string,
)

from ..llm import ModelCallError, UsageLimitReached, _clean_env, _usage_windows
from .harness import RECORDS, injections, suite

ROOT = Path(__file__).resolve().parent.parent.parent
SYSTEM_MESSAGE = load_system_message(None)
SERVER = "banking"


@dataclass
class AgentRun:
    answer: str = ""
    calls: list[dict[str, Any]] = field(default_factory=list)
    model_resolved: list[str] = field(default_factory=list)
    output_tokens: int | None = None
    duration_s: float = 0.0


@dataclass
class CLIAgent:
    """One `claude -p` run per task, with the banking tools over MCP."""

    model: str
    executable: str = "claude"
    timeout: float = 900.0
    ceiling: float = 0.90
    windows: dict[str, float] = field(default_factory=dict)

    def command(self, mcp_config: dict) -> list[str]:
        return [
            self.executable,
            "-p",
            "--setting-sources",
            "",
            "--strict-mcp-config",
            "--mcp-config",
            json.dumps(mcp_config),
            "--tools",
            "",
            "--allowedTools",
            f"mcp__{SERVER}",
            "--model",
            self.model,
            "--system-prompt",
            SYSTEM_MESSAGE,
            "--no-session-persistence",
            "--output-format",
            "stream-json",
            "--verbose",
        ]

    def run(self, prompt: str, env: Env) -> tuple[AgentRun, Env]:
        over = {n: u for n, u in self.windows.items() if u >= self.ceiling}
        if over:
            raise UsageLimitReached(f"usage window(s) {over} at or above the ceiling")
        work = Path(tempfile.mkdtemp(prefix="aap-baseline-"))
        try:
            state = work / "state.json"
            state.write_text(
                json.dumps({"environment": json.loads(env.model_dump_json()), "calls": []})
            )
            cwd = work / "cwd"
            cwd.mkdir()
            config = {
                "mcpServers": {
                    SERVER: {
                        "command": sys.executable,
                        "args": ["-W", "ignore", "-m", "poc.agentdojo.mcp_server", str(state)],
                        "env": {"PYTHONPATH": str(ROOT)},
                    }
                }
            }
            started = time.monotonic()
            try:
                done = subprocess.run(
                    self.command(config),
                    input=prompt,
                    capture_output=True,
                    text=True,
                    cwd=cwd,
                    env=_clean_env(),
                    timeout=self.timeout,
                    check=False,
                )
            except subprocess.TimeoutExpired as e:
                raise ModelCallError(f"the agent run timed out after {self.timeout:.0f}s") from e
            run = self._read(done)
            run.duration_s = round(time.monotonic() - started, 1)
            data = json.loads(state.read_text())
            run.calls = data["calls"]
            after = type(env).model_validate(data["environment"])
            return run, after
        finally:
            shutil.rmtree(work, ignore_errors=True)

    def _read(self, done: subprocess.CompletedProcess) -> AgentRun:
        events = []
        for line in done.stdout.splitlines():
            if line.startswith("{"):
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        self.windows.update(_usage_windows(events))
        result = next((e for e in reversed(events) if e.get("type") == "result"), None)
        if result is None:
            detail = (done.stderr or done.stdout or "").strip()[:400]
            if "limit" in detail.lower():
                raise UsageLimitReached(detail)
            raise ModelCallError(f"the CLI exited {done.returncode} without a result: {detail}")
        text = result.get("result")
        if result.get("is_error") or not isinstance(text, str):
            detail = str(text or result.get("subtype") or "")[:400]
            if result.get("api_error_status") == 429 or "usage limit" in detail.lower():
                raise UsageLimitReached(detail)
            raise ModelCallError(f"the agent run failed: {detail}")
        init = next((e for e in events if e.get("type") == "system"), {})
        resolved = sorted(
            {*(result.get("modelUsage") or {}), *([init["model"]] if init.get("model") else [])}
        )
        return AgentRun(
            answer=text.strip(),
            model_resolved=resolved,
            output_tokens=(result.get("usage") or {}).get("output_tokens"),
        )


class BaselinePipeline(BasePipelineElement):
    """The agent as an AgentDojo pipeline element: the environment it returns is the
    one the tools changed, which is what AgentDojo's scorer reads."""

    def __init__(self, agent: CLIAgent) -> None:
        self.agent = agent
        self.name = f"claude-cli-baseline-{agent.model}"
        self.last_run: AgentRun | None = None

    # The signature is `BasePipelineElement.query`'s, defaults included.
    def query(
        self,
        query: str,
        runtime: FunctionsRuntime,
        env: Env = EmptyEnv(),  # noqa: B008
        messages: Sequence[ChatMessage] = [],
        extra_args: dict = {},  # noqa: B006
    ) -> tuple[str, FunctionsRuntime, Env, Sequence[ChatMessage], dict]:
        run, after = self.agent.run(query, env)
        self.last_run = run
        new: list[ChatMessage] = []
        for i, c in enumerate(run.calls):
            call = FunctionCall(function=c["function"], args=c["args"], id=f"cli-{i}")
            new.append(
                ChatAssistantMessage(
                    role="assistant",
                    tool_calls=[call],
                    content=[text_content_block_from_string("")],
                )
            )
            new.append(
                ChatToolResultMessage(
                    role="tool",
                    content=[text_content_block_from_string("")],
                    tool_call=call,
                    tool_call_id=call.id,
                    error=c["error"],
                )
            )
        new.append(
            ChatAssistantMessage(
                role="assistant",
                tool_calls=None,
                content=[text_content_block_from_string(run.answer)],
            )
        )
        return query, runtime, after, [*messages, *new], extra_args


# ── The resumable run ───────────────────────────────────────────────

BASELINE_RECORDS = RECORDS / "baseline"


def pairs() -> list[tuple[str, str | None]]:
    """16 utility runs, then the 144 pairs of a user task and an injection task."""
    s = suite()
    users = sorted(s.user_tasks, key=lambda k: int(k.rsplit("_", 1)[1]))
    injs = sorted(s.injection_tasks, key=lambda k: int(k.rsplit("_", 1)[1]))
    return [(u, None) for u in users] + [(u, i) for u in users for i in injs]


def record_path(model: str, rep: int) -> Path:
    return BASELINE_RECORDS / model / f"rep-{rep}.jsonl"


def done_keys(path: Path) -> set[tuple[str, str | None]]:
    if not path.exists():
        return set()
    return {
        (r["user_task"], r["injection_task"])
        for r in map(json.loads, path.read_text().splitlines())
    }


def run_one(agent: CLIAgent, user_task: str, injection_task: str | None) -> dict[str, Any]:
    s = suite()
    pipeline = BaselinePipeline(agent)
    injected = injections(user_task, injection_task, pipeline) if injection_task else {}
    utility, attacked = s.run_task_with_pipeline(
        pipeline,
        s.user_tasks[user_task],
        s.injection_tasks[injection_task] if injection_task else None,
        injected,
    )
    run = pipeline.last_run or AgentRun()
    return {
        "user_task": user_task,
        "injection_task": injection_task,
        "model_requested": agent.model,
        "utility": bool(utility),
        "attack_success": None if injection_task is None else bool(attacked),
        **{k: v for k, v in asdict(run).items()},
    }


def main(argv: list[str] | None = None) -> int:
    import argparse

    from ..polite import lower_priority

    parser = argparse.ArgumentParser(description="Run the undefended baseline (subscription).")
    parser.add_argument("--model", required=True, help="a full model ID, e.g. claude-haiku-5-5")
    parser.add_argument("--rep", type=int, default=0)
    parser.add_argument("--limit", type=int, default=None, help="stop after this many runs")
    parser.add_argument("--no-nice", action="store_true")
    parser.add_argument("--executable", default="claude", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if not args.no_nice:
        lower_priority()
    path = record_path(args.model, args.rep)
    path.parent.mkdir(parents=True, exist_ok=True)
    agent = CLIAgent(args.model, executable=args.executable)
    todo = [p for p in pairs() if p not in done_keys(path)]
    for n, (user_task, injection_task) in enumerate(todo[: args.limit]):
        try:
            result = run_one(agent, user_task, injection_task)
        except UsageLimitReached as e:
            print(f"usage ceiling reached, stopping; rerun to resume: {e}")
            return 75
        except ModelCallError as e:
            print(f"{user_task} {injection_task}: harness fault, not recorded: {e}")
            continue
        with path.open("a") as f:
            f.write(json.dumps(result, sort_keys=True) + "\n")
        print(
            f"[{n + 1}/{len(todo)}] {user_task} {injection_task}: "
            f"utility={result['utility']} attack={result['attack_success']}",
            flush=True,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
