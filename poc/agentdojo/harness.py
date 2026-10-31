"""Run banking graphs through AgentDojo, scored by AgentDojo.

The suite is `v1.2.2` at the pinned commit (design, "The pin, re-checked"), and the
attack is AgentDojo's `important_instructions`, addressing the model as "Claude":
every real model behind a graph or the baseline here is one, and the attack's text
otherwise depends on a pipeline name we do not have. Utility and attack success
are the two booleans `TaskSuite.run_task_with_pipeline` returns; the second is the
injection goal's own `security` predicate, true when the attack *succeeded*.

The graphs here are hand-written, so their results are **oracle plans**: they
measure confinement given a correct plan, never an agent, and they are not
comparable with AgentDojo's published numbers.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from functools import cache
from pathlib import Path
from typing import Any

from agentdojo.attacks.important_instructions_attacks import ImportantInstructionsAttack
from agentdojo.base_tasks import BaseInjectionTask
from agentdojo.task_suite.load_suites import get_suite
from agentdojo.task_suite.task_suite import TaskSuite

from .pipeline import GraphPipeline
from .standins import FooledModel, OracleModel

SUITE_VERSION = "v1.2.2"
SUITE_NAME = "banking"
ATTACK = "important_instructions"
MODEL_NAME_IN_ATTACK = "Claude"

HERE = Path(__file__).resolve().parent
GRAPHS = HERE / "graphs"
ORACLE_ANSWERS = GRAPHS / "oracle-answers.json"

# The environment collections a reader exposes, by its DBHandle scope.
_COLLECTIONS = {
    "transactions": ("bank_account", "transactions"),
    "scheduled-transactions": ("bank_account", "scheduled_transactions"),
}


@cache
def suite() -> TaskSuite:
    return get_suite(SUITE_VERSION, SUITE_NAME)


class ClaudeImportantInstructions(ImportantInstructionsAttack):
    """`important_instructions`, naming the model "Claude" rather than reading it
    off the pipeline's name."""

    def __init__(self, task_suite: TaskSuite, target_pipeline: Any) -> None:
        super(ImportantInstructionsAttack, self).__init__(
            self._JB_STRING, task_suite, target_pipeline
        )
        self.user_name = "Emma Johnson"
        self.model_name = MODEL_NAME_IN_ATTACK


def injections(user_task_id: str, injection_task_id: str, pipeline: Any) -> dict[str, str]:
    s = suite()
    attack = ClaudeImportantInstructions(s, pipeline)
    return attack.attack(s.user_tasks[user_task_id], s.injection_tasks[injection_task_id])


def load_graph(name: str) -> dict:
    return json.loads((GRAPHS / f"{name}.json").read_text())


def oracle_answers(graph: dict) -> dict[str, dict[str, Any]]:
    return json.loads(ORACLE_ANSWERS.read_text()).get(graph["name"], {})


def visible_scopes(graph: dict, node: str) -> set[str]:
    """The `DBHandle` scopes read by nodes upstream of `node`: what it could see."""
    caps = set(graph["capabilities"])
    upstream: dict[str, set[str]] = {}
    for e in graph["data_edges"]:
        upstream.setdefault(e["to"], set()).add(e["from"].split(".")[0])
    seen, stack = set(), [node]
    while stack:
        for src in upstream.get(stack.pop(), ()):
            if src not in seen:
                seen.add(src)
                stack.append(src)
    scopes = set()
    for n in graph["nodes"]:
        if n["name"] in seen:
            for c in n["inputs"]:
                if c in caps and c.startswith("DBHandle<'"):
                    scopes.add(c.split("'")[1])
    return scopes


def _goal_calls(injection_task: BaseInjectionTask, env: Any, graph: dict):
    def calls(node: str) -> list[dict[str, Any]]:
        blind = env.model_copy(deep=True)
        visible = visible_scopes(graph, node)
        for scope, (part, attr) in _COLLECTIONS.items():
            if scope not in visible:
                setattr(getattr(blind, part), attr, [])
        try:
            return [dict(c.args) for c in injection_task.ground_truth(blind)]
        except (IndexError, KeyError, ValueError, AttributeError):
            return []  # the goal needs what the node never saw

    return calls


@dataclass
class PairResult:
    graph: str
    user_task: str
    injection_task: str | None
    model: str  # "oracle" | "fooled" | "live"
    utility: bool
    attack_success: bool | None
    answer: str
    failure: str | None
    calls: list[dict[str, Any]] = field(default_factory=list)
    obeyed: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def run_pair(
    graph: dict,
    user_task_id: str,
    injection_task_id: str | None = None,
    *,
    fooled: bool = False,
    sandbox: tuple[str, ...] = (),
    backend: Any = None,
) -> PairResult:
    """One scored run of `graph` on a user task, under one injection or none.

    `backend`, if given, is the model behind the graph's `Extract` nodes (a real
    one, for an architect's graph); otherwise the oracle stand-in answers."""
    s = suite()
    honest = backend if backend is not None else OracleModel(oracle_answers(graph))
    pipeline = GraphPipeline(graph, honest, sandbox=sandbox)
    injected: dict[str, str] = {}
    injection_task = None
    if injection_task_id is not None:
        injection_task = s.injection_tasks[injection_task_id]
        injected = injections(user_task_id, injection_task_id, pipeline)
    model: Any = honest
    if fooled:
        env = s.load_and_inject_default_environment(injected)
        # The marker is the goal's text: AgentDojo substitutes an injection into its
        # YAML environment before parsing it, so the stored text is the injection
        # as YAML read it, and only the goal sentence survives verbatim.
        model = (
            FooledModel(honest, (injection_task.GOAL,), _goal_calls(injection_task, env, graph))
            if injection_task is not None
            else honest
        )
        pipeline.backend = model
    utility, attacked = s.run_task_with_pipeline(
        pipeline, s.user_tasks[user_task_id], injection_task, injected
    )
    run = pipeline.last_run
    assert run is not None
    return PairResult(
        graph=graph["name"],
        user_task=user_task_id,
        injection_task=injection_task_id,
        model="fooled" if fooled else "oracle" if backend is None else "live",
        utility=bool(utility),
        attack_success=None if injection_task_id is None else bool(attacked),
        answer=run.answer,
        failure=run.failure,
        calls=run.calls,
        obeyed=list(getattr(model, "obeyed", [])),
    )


# The spike's three graphs, rewritten over the library (task 3.3), and their tasks.
ORACLE_GRAPHS = {
    "banking-user-task-0": "user_task_0",
    "banking-user-task-1": "user_task_1",
    "banking-user-task-15": "user_task_15",
}
RECORDS = HERE / "records"
ORACLE_RECORD = RECORDS / "oracle-plans.json"


def oracle_runs() -> dict[str, Any]:
    """Every oracle graph on its task: once clean, then under each injection with
    the oracle model and with the fooled one. Deterministic: no model is called."""
    runs = []
    for name, task in ORACLE_GRAPHS.items():
        g = load_graph(name)
        runs.append(run_pair(g, task).as_dict())
        for injection in suite().injection_tasks:
            for fooled in (False, True):
                runs.append(run_pair(g, task, injection, fooled=fooled).as_dict())
    return {
        "label": "oracle plans: hand-written graphs, not a benchmark result",
        "suite": f"{SUITE_NAME} {SUITE_VERSION}",
        "attack": ATTACK,
        "runs": runs,
    }


IDLE_RECORD = RECORDS / "idle-pass.json"


def idle_pass() -> dict[str, Any]:
    """The user tasks whose utility predicate holds on an idle run: no tool call, an
    empty answer, the environment as shipped. For some, doing nothing is right (the
    rent is already correct); for others the shipped environment already satisfies
    the predicate. Either way their utility does not show that an agent acted, so a
    report gives utility over the rest beside AgentDojo's figure."""
    s = suite()
    idle = []
    for name, task in s.user_tasks.items():
        pre = s.load_and_inject_default_environment({})
        if task.utility("", pre, pre.model_copy(deep=True)):
            idle.append(name)
    return {
        "what": "user tasks whose utility predicate holds with no call and an empty answer",
        "suite": f"{SUITE_NAME} {SUITE_VERSION}",
        "idle_pass": sorted(idle, key=lambda t: int(t.rsplit("_", 1)[1])),
    }


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("command", choices=["oracle", "idle"])
    args = parser.parse_args(argv)
    RECORDS.mkdir(exist_ok=True)
    path, data = (
        (ORACLE_RECORD, oracle_runs()) if args.command == "oracle" else (IDLE_RECORD, idle_pass())
    )
    path.write_text(json.dumps(data, indent=1, sort_keys=True) + "\n")
    print(f"wrote {path.relative_to(HERE.parent.parent)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
