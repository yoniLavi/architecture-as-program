"""A signal graph as an AgentDojo pipeline element.

Modelled on AgentDojo's `GroundTruthPipeline` (`agent_pipeline/ground_truth_pipeline.py`
at the pin): it drives the task's `FunctionsRuntime` directly and ends with a final
assistant message. Here what drives the runtime is a graph, run by the repository's
own `assemble`/`execute`, with every handle backed by that runtime
(`adapter.AgentDojoBank`) and its scope checked first (`poc/bank.py`). Scoring is
AgentDojo's own: `TaskSuite.run_task_with_pipeline` reads the post-run environment
and the final message, unchanged.

A run that fails — the validator or the library check rejects the graph, a scope
check refuses a request, a contract or a node body fails — still ends with a final
assistant message, saying so. AgentDojo re-runs a pipeline whose output is empty,
on the environment the failed run left behind, which would turn one refusal into
three attempts. The failure is kept on `last_run` for the report.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from typing import Any

from agentdojo.agent_pipeline.base_pipeline_element import BasePipelineElement
from agentdojo.agent_pipeline.tool_execution import tool_result_to_str
from agentdojo.functions_runtime import EmptyEnv, Env, FunctionsRuntime
from agentdojo.types import (
    ChatAssistantMessage,
    ChatMessage,
    ChatToolResultMessage,
    text_content_block_from_string,
)

from ..graph import assemble
from ..handles import ResponseChannel, World
from ..llm import LLMBackend
from ..runtime import execute
from .adapter import AgentDojoBank
from .library import bodies, check_graph


@dataclass
class RunRecord:
    """What one graph run did, beside what AgentDojo scores."""

    answer: str = ""
    failure: str | None = None  # "<ExceptionType>: message", or None
    order: list[str] = field(default_factory=list)
    calls: list[dict[str, Any]] = field(default_factory=list)


class LibraryGraphError(ValueError):
    """The graph does not compose correctly from the node library."""


class GraphPipeline(BasePipelineElement):
    """Runs one library-composed banking graph against an AgentDojo task."""

    name = "signal-graph"

    def __init__(self, graph: dict, backend: LLMBackend, *, sandbox: Iterable[str] = ()) -> None:
        self.graph = graph
        self.backend = backend
        self.sandbox = tuple(sandbox)
        self.last_run: RunRecord | None = None

    def _run(self, query: str, bank: AgentDojoBank) -> RunRecord:
        record = RunRecord()
        # The validator first (assembly validates), so a graph's authority is judged
        # by the analyses the paper reports before the library's own bookkeeping.
        assembled = assemble(
            self.graph, backend=self.backend, world=World(bank=bank), sandbox=self.sandbox
        )
        problems = check_graph(self.graph)
        if problems:
            raise LibraryGraphError("; ".join(problems))
        try:
            result = execute(assembled, {"prompt": query}, impls=bodies(self.graph))
            record.order = list(result.order)
        finally:
            channels = [
                h
                for h in [*assembled.handles.values(), *assembled.instances.values()]
                if isinstance(h, ResponseChannel)
            ]
            record.answer = "\n".join(t for c in channels for t in c.sent)
        return record

    # The signature is `BasePipelineElement.query`'s, defaults included.
    def query(
        self,
        query: str,
        runtime: FunctionsRuntime,
        env: Env = EmptyEnv(),  # noqa: B008
        messages: Sequence[ChatMessage] = [],
        extra_args: dict = {},  # noqa: B006
    ) -> tuple[str, FunctionsRuntime, Env, Sequence[ChatMessage], dict]:
        bank = AgentDojoBank(runtime, env)  # type: ignore[arg-type]
        try:
            record = self._run(query, bank)
        except Exception as e:  # every failure is reported, none escapes into the scorer
            record = RunRecord(failure=f"{type(e).__name__}: {e}")
        record.calls = [
            {"function": c.function, "args": dict(c.args), "error": err}
            for c, _result, err in bank.calls
        ]
        self.last_run = record

        new_messages: list[ChatMessage] = []
        for call, result, error in bank.calls:
            new_messages.append(
                ChatAssistantMessage(
                    role="assistant",
                    tool_calls=[call],
                    content=[text_content_block_from_string("")],
                )
            )
            new_messages.append(
                ChatToolResultMessage(
                    role="tool",
                    content=[text_content_block_from_string(tool_result_to_str(result))],
                    tool_call=call,
                    tool_call_id=call.id,
                    error=error,
                )
            )
        final = record.answer or f"The graph did not complete: {record.failure}"
        new_messages.append(
            ChatAssistantMessage(
                role="assistant",
                content=[text_content_block_from_string(final)],
                tool_calls=None,
            )
        )
        return query, runtime, env, [*messages, *new_messages], extra_args
