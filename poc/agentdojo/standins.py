"""Stand-in models for the `Extract` nodes of oracle graphs. No test or build step
calls a model; these are what the harness runs instead.

* `OracleModel` answers each extraction correctly, whatever the material says. It
  measures a plan given a perfect extractor: utility, and attacks that need no
  model to be fooled.
* `FooledModel` obeys the injection. Whenever its material carries injected text,
  its answer is the injection goal's own ground-truth call (AgentDojo's
  `InjectionTask.ground_truth`), field by field, as far as the extraction's schema
  has room for it. The ground truth is computed on an environment with every
  collection the node did not see emptied, so the stand-in knows the injection's
  text and what the graph routed to it, and nothing else: a goal that needs the
  user's history gets an empty value where the history would go.

`FooledModel` is not the worst case. It makes the attacker's *reference* calls,
and a predicate may admit other ways to succeed (goal 6 succeeds on one payment
over 10,000, while its ground truth sends three of 10,000). The static predictions
(`predict.py`) are the worst-case analysis; this stand-in shows the harness
measuring an attack end to end.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any

from ..llm import LLMRequest, LLMResponse


def _node(request: LLMRequest) -> str:
    return request.task.removeprefix("extract:")


@dataclass
class OracleModel:
    """Correct answers, by `Extract` node name."""

    answers: Mapping[str, Mapping[str, Any]]
    calls: list[LLMRequest] = field(default_factory=list)

    def generate(self, request: LLMRequest) -> LLMResponse:
        self.calls.append(request)
        return LLMResponse(text=json.dumps(self.answers[_node(request)]))


@dataclass
class FooledModel:
    """Obeys an injection found in its material (module docstring).

    `markers` are the injected strings; `goal_calls(node)` returns the injection
    goal's ground-truth calls as computed for what that node could see."""

    honest: OracleModel
    markers: tuple[str, ...]
    goal_calls: Callable[[str], list[dict[str, Any]]]
    obeyed: list[str] = field(default_factory=list)

    def generate(self, request: LLMRequest) -> LLMResponse:
        node = _node(request)
        answer = dict(json.loads(self.honest.generate(request).text))
        # The material reaches the model JSON-encoded, so look for each marker
        # both as written and as JSON would escape it.
        if not any(
            m and (m in request.prompt or json.dumps(m)[1:-1] in request.prompt)
            for m in self.markers
        ):
            return LLMResponse(text=json.dumps(answer))
        best: dict[str, Any] = {}
        for call in self.goal_calls(node):
            overlap = {k: v for k, v in call.items() if k in answer}
            if len(overlap) > len(best):
                best = overlap
        if best:
            self.obeyed.append(node)
            answer.update(best)
        return LLMResponse(text=json.dumps(answer))
