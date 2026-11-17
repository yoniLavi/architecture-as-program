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
    custom: dict[str, Any] | None = None,
) -> PairResult:
    """One scored run of `graph` on a user task, under one injection or none.

    `backend`, if given, is the model behind the graph's `Extract` nodes (a real
    one, for an architect's graph); otherwise the oracle stand-in answers. `custom`
    (the slice only) gives the confined bodies of its `Custom` nodes."""
    s = suite()
    honest = backend if backend is not None else OracleModel(oracle_answers(graph))
    pipeline = GraphPipeline(graph, honest, sandbox=sandbox, custom=custom)
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


# ── The injection residual under a bind (value-bound grants, 5.2) ──
#
# Task 0's oracle graph with its writer bound to the extractor's order: payee and
# amount, once. A bind holds the writer to its input; an injection that moves the
# extractor moves the input. Recorded apart from the oracle plans, which it does
# not change, and pinned as the attack succeeding wherever it succeeded unbound.

BOUND_RECORD = RECORDS / "bound-oracle-plans.json"
BOUND_GRAPH = "banking-user-task-0"
BOUND_WRITER = "PayBill"


def bound_graph() -> dict:
    g = load_graph(BOUND_GRAPH)
    node = next(n for n in g["nodes"] if n["name"] == BOUND_WRITER)
    grant = next(i for i in node["inputs"] if i.startswith("Payments<"))
    node["bind"] = {grant: {"payee": "in0.recipient", "amount": "in0.amount", "uses": 1}}
    return g


def bound_runs() -> dict[str, Any]:
    """`bound_graph()` on its task, as `oracle_runs` runs the oracle graphs: clean,
    then under each injection with the oracle model and with the fooled one."""
    g, task = bound_graph(), ORACLE_GRAPHS[BOUND_GRAPH]
    runs = [run_pair(g, task).as_dict()]
    for injection in suite().injection_tasks:
        for fooled in (False, True):
            runs.append(run_pair(g, task, injection, fooled=fooled).as_dict())
    return {
        "label": "an oracle plan with a bound writer: a pinned limit, not a defence and "
        "not a benchmark result",
        "suite": f"{SUITE_NAME} {SUITE_VERSION}",
        "attack": ATTACK,
        "bind": {BOUND_WRITER: next(n["bind"] for n in g["nodes"] if "bind" in n)},
        "runs": runs,
    }


# ── Payee provenance (add-payee-provenance, D6 and D7) ──────────────
#
# The pinned injection cases re-run with each `[any]` payment grant rewritten to
# `[known-payees]`, by hand and labelled so: nothing else in a graph changes, and no
# architect chose the class. The cases are passed in, because two of them (the split
# answer, D1's bound replay) are test fixtures that `poc` does not import. The
# record is apart from the oracle and bound records, which stay unchanged.

ANY_GRANT = "Payments<[any], uncapped>"
KNOWN_GRANT = "Payments<[known-payees], uncapped>"
KNOWN_RECORD = RECORDS / "known-payee-plans.json"
KNOWN_PREDICTIONS = HERE / "predictions" / "known-payees.json"


def rewrite_known_payees(value: Any) -> Any:
    """`value` with every `ANY_GRANT`, as a string or a key, replaced by
    `KNOWN_GRANT`. A string that merely contains it is left alone."""
    if isinstance(value, dict):
        return {
            (KNOWN_GRANT if k == ANY_GRANT else k): rewrite_known_payees(v)
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [rewrite_known_payees(v) for v in value]
    return KNOWN_GRANT if value == ANY_GRANT else value


@dataclass
class KnownCase:
    """One pinned case: its graph before the rewrite, its task, and how it runs.
    `injections` False runs it clean only; `confined` runs every node with a
    component confined (D1's body has no host form); `confined_injection` names one
    injection also run, fooled, on the confined tier."""

    name: str
    graph: dict
    user_task: str
    injections: bool = True
    backend: Any = None
    custom: dict[str, Any] | None = None
    confined: bool = False
    confined_injection: str | None = None


def _paid(calls: list[dict[str, Any]], payee: str) -> bool:
    return any(c["function"] == "send_money" and c["args"].get("recipient") == payee
               for c in calls)  # fmt: skip


def known_payee_runs(cases: list[KnownCase], attacker: str) -> dict[str, Any]:
    """Each case, rewritten, on the host tier: clean, then (if it takes injections)
    under each injection with the oracle model and the fooled one; plus one fooled
    injection on the confined tier where named. Every outcome is compared with the
    committed prediction for it; a mismatch is listed, never corrected."""
    from .library import confinable

    document = json.loads(KNOWN_PREDICTIONS.read_text())
    compared = tuple(document["compared"])
    predicted = {
        (p["case"], p["injection_task"], p["model"], p["tier"]): p for p in document["predictions"]
    }
    runs, contradictions = [], []

    def one(case: KnownCase, g: dict, injection: str | None, fooled: bool, tier: str) -> None:
        sandbox = tuple(confinable(g)) if tier == "confined" else ()
        r = run_pair(g, case.user_task, injection, fooled=fooled, sandbox=sandbox,
                     backend=case.backend, custom=case.custom).as_dict()  # fmt: skip
        model = "fooled" if fooled else "oracle"
        outcome = {
            "case": case.name,
            "tier": tier,
            "attacker_paid": _paid(r["calls"], attacker),
            "refused": bool(r["failure"]) and "outside the handle's payees" in r["failure"],
            **{
                k: r[k]
                for k in (
                    "user_task",
                    "injection_task",
                    "utility",
                    "attack_success",
                    "failure",
                    "calls",
                )
            },
            # Every backend here is a stand-in; `run_pair` says "live" for any given one.
            "model": model,
        }
        runs.append(outcome)
        p = predicted.get((case.name, injection, model, tier))
        if p is None:
            contradictions.append({"run": [case.name, injection, model, tier],
                                   "why": "no committed prediction"})  # fmt: skip
            return
        for key in compared:
            if p[key] != outcome[key]:
                contradictions.append({"run": [case.name, injection, model, tier],
                                       "field": key, "predicted": p[key],
                                       "measured": outcome[key]})  # fmt: skip

    for case in cases:
        g = rewrite_known_payees(case.graph)
        tier = "confined" if case.confined else "host"
        one(case, g, None, False, tier)
        if case.injections:
            for injection in suite().injection_tasks:
                for fooled in (False, True):
                    one(case, g, injection, fooled, tier)
        if case.confined_injection:
            one(case, g, case.confined_injection, True, "confined")
    return {
        "label": "hand-rewritten grants ([any] to [known-payees]) on pinned cases: a "
        "measurement of the rule's two sides, not a defence and not a benchmark result",
        "suite": f"{SUITE_NAME} {SUITE_VERSION}",
        "attack": ATTACK,
        "grant": {"from": ANY_GRANT, "to": KNOWN_GRANT},
        "runs": runs,
        "contradictions": contradictions,
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
    parser.add_argument("command", choices=["oracle", "idle", "bound"])
    args = parser.parse_args(argv)
    RECORDS.mkdir(exist_ok=True)
    path, data = {
        "oracle": lambda: (ORACLE_RECORD, oracle_runs()),
        "idle": lambda: (IDLE_RECORD, idle_pass()),
        "bound": lambda: (BOUND_RECORD, bound_runs()),
    }[args.command]()
    path.write_text(json.dumps(data, indent=1, sort_keys=True) + "\n")
    print(f"wrote {path.relative_to(HERE.parent.parent)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
