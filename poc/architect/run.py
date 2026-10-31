"""Driving the architect over AgentDojo's banking tasks (task 4.1: the pilot).

    uv run --group poc --group agentdojo python -m poc.architect.run pilot --model claude-haiku-5-5

**The pilot is exploratory and unregistered**, and every record says so. It asks two
things before any registration: can the architect express the tasks over the library,
and do its graphs have utility through AgentDojo's own scorer? No pretext, no
injection. Per task, in order:

1. the architect (`architect.author`);
2. the formal review: the validator's verdict (from the architect's loop), the link
   check and the least-authority check against the approved labels;
3. the reviewer's primary verdict and its score against step 2's widenings;
4. one clean AgentDojo run of the graph, its `Extract` nodes answered by the same
   model, on the host tier.

A run that is refused for lack of a grant is recorded with its failure; nothing about
it goes back to the architect here. (Run-time refusals can name values the bank holds,
such as a payee, so a graph edit returned to the architect must carry the refusal's
class and node, never its message: that loop is the measured run's, task 4.4.)

Each task is recorded whole under `runs/pilot/<model>/<task>.json`, written when done,
so a rerun resumes. The usage ceiling stops the run (exit 75), and nothing partial is
recorded. Runs at low priority (`poc/polite.py`).
"""

from __future__ import annotations

import argparse
import json
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any

from ..graph import REPO_ROOT
from ..llm import ClaudeCLIBackend, LLMBackend, ModelCallError, UsageLimitReached
from . import formal, labels
from .architect import GRAPH, ModelMismatch, author
from .reviewer import PRIMARY, review, score

HERE = Path(__file__).resolve().parent
RUNS = HERE / "runs"
PILOT = "pilot"
PILOT_LABEL = "exploratory: unregistered pilot, no pretext, no injection"
TASKS = tuple(f"user_task_{i}" for i in range(16))
EXIT_USAGE = 75


def graph_name(task: str) -> str:
    return "ArchitectUserTask" + task.rsplit("_", 1)[1]


def record_path(run: str, model: str, task: str) -> Path:
    return RUNS / run / model / f"{task}.json"


def _write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(data, indent=1, ensure_ascii=False, sort_keys=True) + "\n")
    tmp.replace(path)


def head() -> str:
    done = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, capture_output=True, text=True, check=False
    )
    return done.stdout.strip()


def formal_review(graph: dict, task: str, prompt: str) -> dict:
    return {
        "links": [f.as_dict() for f in formal.link_check(graph, prompt)],
        "widenings": [w.as_dict() for w in formal.least_authority(graph, labels.label(task))],
    }


def pilot_task(
    task: str,
    model: str,
    backend_for: Callable[[str], LLMBackend],
    *,
    run_graph: Callable[[dict, str, LLMBackend], dict] | None = None,
) -> dict:
    """One task of the pilot, recorded whole. `backend_for(role)` gives the model for
    the architect, the reviewer and the graph's `Extract` nodes, separately, so each
    role's usage stays its own. `run_graph` scores a graph on AgentDojo (injected for
    tests; the default needs the `agentdojo` group)."""
    prompt = labels.load()["tasks"][task]["prompt"]
    arch = author(prompt, backend_for("architect"), name=graph_name(task), expected_model=model)
    record: dict[str, Any] = {
        "label": PILOT_LABEL,
        "task": task,
        "prompt": prompt,
        "model": model,
        "head": head(),
        "architect": arch,
        "formal": None,
        "reviewer": None,
        "run": None,
    }
    if arch["outcome"] != GRAPH:
        return record
    graph = arch["graph"]
    record["formal"] = formal_review(graph, task, prompt)
    rev = review(prompt, graph, backend_for("reviewer"), view=PRIMARY, expected_model=model)
    widened = formal.least_authority(graph, labels.label(task))
    record["reviewer"] = {**rev, "score": score(rev["verdicts"], widened, graph["capabilities"])}
    runner = run_graph or _agentdojo_run
    record["run"] = runner(graph, task, backend_for("extract"))
    return record


def _agentdojo_run(graph: dict, task: str, backend: LLMBackend) -> dict:
    from ..agentdojo.harness import run_pair

    result = run_pair(graph, task, backend=backend).as_dict()
    result["tier"] = "host"
    return result


def main(argv: list[str] | None = None) -> int:
    from ..polite import lower_priority

    parser = argparse.ArgumentParser(prog="poc.architect.run")
    parser.add_argument("command", choices=[PILOT])
    parser.add_argument("--model", required=True, help="a full model ID, e.g. claude-haiku-5-5")
    parser.add_argument("--tasks", nargs="*", default=list(TASKS))
    parser.add_argument("--no-nice", action="store_true")
    args = parser.parse_args(argv)
    priority = lower_priority(not args.no_nice)
    for task in args.tasks:
        path = record_path(PILOT, args.model, task)
        if path.exists():
            continue

        def backend_for(_role: str) -> LLMBackend:
            return ClaudeCLIBackend(model=args.model)

        try:
            record = pilot_task(task, args.model, backend_for)
        except UsageLimitReached as e:
            print(f"usage ceiling reached, stopping; rerun to resume: {e}")
            return EXIT_USAGE
        except (ModelMismatch, ModelCallError) as e:
            print(f"{task}: harness fault, not recorded: {e}")
            continue
        record["priority"] = priority
        _write(path, record)
        run = record["run"] or {}
        print(
            f"{task}: {record['architect']['outcome']}"
            + (f", utility={run.get('utility')}, failure={run.get('failure')}" if run else ""),
            flush=True,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
