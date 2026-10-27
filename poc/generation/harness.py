"""Run generation trials, record every one, and resume where a run stopped.

    uv run --group poc python -m poc.generation.harness handwritten
    uv run --group poc python -m poc.generation.harness run --run-id pilot --group pilot -n 5
    uv run --group poc python -m poc.generation.harness results

A **trial** is one (node, arm, model, repetition): the model is given the node's
task, its reply goes through the pipeline, and on failure the error is fed back,
up to `MAX_ITERATIONS` attempts. Everything about it is written to one JSON file
under `runs/<run-id>/` — the task's hash, every reply as returned, the files
extracted from it, and the pipeline's verdict on each attempt. Those files are
committed. They are the experiment's data; `results.json` is derived from them.

**Resuming.** A trial whose file exists is skipped. The model backend stops at a
usage ceiling (the subscription is shared with everything else its owner does),
and when it does the harness exits with code 4, having written every trial that
finished. Running the same command again continues from there: a session limit
costs time, not data.

**The model sees only the task.** Each call is `claude -p` with no tools, in
safe mode, in an empty directory, with a fixed one-line system prompt. It cannot
read this repository, and in particular cannot read the hand-written bodies.

**Controls.** `handwritten` puts the existing bodies through the same pipeline
(expected: no violations, which the report pins). The gate-off control needs no
separate run: whenever the gate catches an over-importing component, the pipeline
immediately re-evaluates that same component with the gate off and records
whether it would have shipped.
"""

from __future__ import annotations

import argparse
import json
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from queue import Queue

from ..graph import REPO_ROOT
from ..llm import ClaudeCLIBackend, LLMRequest, ModelCallError, UsageLimitReached
from ..polite import lower_priority
from . import pipeline, registration, task
from .registration import RegistrationError
from .subjects import BY_NODE, Subject, graph_for, subjects

HERE = Path(__file__).resolve().parent
RUNS_DIR = HERE / "runs"
RESULTS_PATH = HERE / "results.json"
# Build products and model working directories: gitignored, rebuildable.
WORK_DIR = REPO_ROOT / "var" / "generation"

MAX_ITERATIONS = 4
MODELS = ("haiku", "sonnet", "opus")
HANDWRITTEN = "hand-written"

SYSTEM = (
    "You are an expert Rust and WebAssembly component-model engineer. "
    "Return exactly what the task asks for."
)

EXIT_OK = 0
EXIT_REFUSED = 2
EXIT_USAGE_LIMIT = 4

# Two trials at once, not three: the machine is shared (design Decision 9).
DEFAULT_JOBS = 2


def trial_id(node: str, arm: str, model: str, n: int) -> str:
    return f"{node}.{arm}.{model}.{n}"


def _write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n")
    tmp.replace(path)


def _task_for(subject: Subject, arm: str) -> task.Task:
    return task.build(graph_for(subject.graph), subject.node, subject.world, arm)


# ── One trial ────────────────────────────────────────────────────────


def run_trial(
    subject: Subject,
    arm: str,
    model: str,
    n: int,
    backend: ClaudeCLIBackend,
    crate: Path,
    target_dir: Path,
    *,
    expected_model: str | None = None,
    extra: dict | None = None,
) -> dict:
    """Run one trial to green or to `MAX_ITERATIONS`. Raises `UsageLimitReached`
    if the backend stops; a trial is only ever recorded whole.

    `expected_model`, for a registered run: the model ID the call must resolve to.
    A call that resolves to any other raises `RegistrationError` and the trial is
    not recorded — an alias that moved mid-run would otherwise split the run
    silently. `extra` is merged into the record (the registration's commit, `HEAD`,
    the priority the trial ran at)."""
    the_task = _task_for(subject, arm)
    prompt = the_task.text
    iterations: list[dict] = []
    started = datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    model_id = model

    for index in range(1, MAX_ITERATIONS + 1):
        began = time.perf_counter()
        try:
            reply = backend.generate(LLMRequest(system=SYSTEM, prompt=prompt)).text
            model_id = backend.usage[-1]["model"] if backend.usage else model
            if expected_model is not None and model_id != expected_model:
                raise RegistrationError(
                    f"the call resolved to {model_id!r}, not the registered {expected_model!r}"
                )
        except UsageLimitReached:
            raise
        except ModelCallError as e:
            # The call itself failed (a timeout, an API error). Recorded as an
            # attempt that produced nothing, so the count of attempts stays honest.
            reply = f"[model call failed: {e}]"
        model_seconds = time.perf_counter() - began

        files = pipeline.parse_reply(reply)
        verdict = pipeline.evaluate(subject, files, crate, target_dir)
        iterations.append(
            {
                "index": index,
                "reply": reply,
                "files": files,
                "model_seconds": round(model_seconds, 1),
                **verdict.to_dict(),
            }
        )
        if verdict.passed:
            break
        prompt = task.with_feedback(the_task, files, reply, verdict.detail)

    green = iterations[-1]["passed"]
    return {
        "trial": trial_id(subject.node, arm, model, n),
        "node": subject.node,
        "group": subject.group,
        "arm": arm,
        "model": model,
        "model_id": model_id,
        "n": n,
        "started": started,
        "task_sha256": the_task.sha256,
        "system": SYSTEM,
        "outcome": "green" if green else "failed",
        "iterations_to_green": len(iterations) if green else None,
        **(extra or {}),
        "iterations": iterations,
    }


def run_handwritten(subject: Subject, crate: Path, target_dir: Path) -> dict:
    """The control: the hand-written body, through the same pipeline."""
    files = {
        "world.wit": task.handwritten_world(subject.world),
        "lib.rs": task.handwritten_source(subject.component),
    }
    verdict = pipeline.evaluate(subject, files, crate, target_dir)
    return {
        "trial": f"{subject.node}.{HANDWRITTEN}",
        "node": subject.node,
        "group": subject.group,
        "arm": HANDWRITTEN,
        "model": HANDWRITTEN,
        "model_id": HANDWRITTEN,
        "n": 1,
        "outcome": "green" if verdict.passed else "failed",
        "iterations_to_green": 1 if verdict.passed else None,
        "iterations": [{"index": 1, "reply": None, "files": files, **verdict.to_dict()}],
    }


# ── A run of trials ──────────────────────────────────────────────────


def planned(chosen: tuple[Subject, ...], arms: list[str], models: list[str], n: int):
    """Every trial of a run, ordered so that a run stopped early is balanced:
    repetition outermost, so each cell has its first trial before any has its second."""
    return [
        (subject, arm, model, rep)
        for rep in range(1, n + 1)
        for subject in chosen
        for arm in arms
        for model in models
    ]


def run(
    run_id: str,
    chosen: tuple[Subject, ...],
    arms: list[str],
    models: list[str],
    n: int,
    *,
    jobs: int,
    ceiling: float,
    model_ids: dict[str, str] | None = None,
    guard=None,
    annotate=None,
) -> int:
    """Run (or resume) every planned trial not yet recorded.

    For a registered run: `model_ids` maps each model alias to the full ID it is
    called by and must resolve to; `guard()` runs before every trial and raises
    `RegistrationError` to stop the run; `annotate()` returns what each record
    carries besides its trial (the registration's commit, `HEAD`, the priority)."""
    run_dir = RUNS_DIR / run_id
    tasks_dir = run_dir / "tasks"
    tasks_dir.mkdir(parents=True, exist_ok=True)
    for subject in chosen:
        for arm in arms:
            (tasks_dir / f"{subject.node}.{arm}.md").write_text(_task_for(subject, arm).text)

    todo = [
        t
        for t in planned(chosen, arms, models, n)
        if not (run_dir / f"{trial_id(t[0].node, t[1], t[2], t[3])}.json").exists()
    ]
    total = len(planned(chosen, arms, models, n))
    print(
        f"run {run_id}: {total - len(todo)}/{total} trials recorded, {len(todo)} to run", flush=True
    )
    if not todo:
        return EXIT_OK

    # One usage-window record shared by every backend, so a ceiling reached
    # through one model's call stops the others too.
    windows: dict[str, float] = {}
    backends = {
        m: ClaudeCLIBackend(
            model=(model_ids or {}).get(m, m),
            workdir=WORK_DIR / "llm",
            timeout=900.0,
            ceiling=ceiling,
            windows=windows,
        )
        for m in models
    }
    slots: Queue[int] = Queue()
    for slot in range(jobs):
        slots.put(slot)
    stop = threading.Event()
    lock = threading.Lock()
    done = 0

    def work(item) -> None:
        nonlocal done
        subject, arm, model, rep = item
        if stop.is_set():
            return
        slot = slots.get()
        try:
            if guard is not None:
                guard()
            name = trial_id(subject.node, arm, model, rep)
            record = run_trial(
                subject,
                arm,
                model,
                rep,
                backends[model],
                WORK_DIR / "build" / f"slot-{slot}",
                WORK_DIR / "target" / f"slot-{slot}",
                expected_model=(model_ids or {}).get(model),
                extra=annotate() if annotate is not None else None,
            )
            _write(run_dir / f"{name}.json", record)
            with lock:
                done += 1
                classes = [",".join(i["classes"]) or "pass" for i in record["iterations"]]
                print(f"[{done}/{len(todo)}] {name}: {' → '.join(classes)}", flush=True)
        except UsageLimitReached as e:
            if not stop.is_set():
                print(f"stopping: {e}", flush=True)
            stop.set()
        except (pipeline.HarnessFault, RegistrationError):
            # The instrument is wrong, or the run is no longer the registered one.
            # Stop every worker; record nothing for this trial; let the error surface.
            stop.set()
            raise
        finally:
            slots.put(slot)

    with ThreadPoolExecutor(max_workers=jobs) as pool:
        list(pool.map(work, todo))

    if stop.is_set():
        print(
            f"usage ceiling reached with {len(todo) - done} trials still to run; "
            f"run the same command again later to continue",
            flush=True,
        )
        return EXIT_USAGE_LIMIT
    return EXIT_OK


def handwritten(chosen: tuple[Subject, ...]) -> int:
    failed = 0
    for subject in chosen:
        record = run_handwritten(
            subject, WORK_DIR / "build" / "handwritten", WORK_DIR / "target" / "slot-0"
        )
        _write(RUNS_DIR / HANDWRITTEN / f"{subject.node}.json", record)
        verdict = record["iterations"][0]
        note = ",".join(verdict["classes"]) or "pass"
        print(
            f"{subject.node}: {note}"
            + (f" — {verdict['detail'][:300]}" if not verdict["passed"] else "")
        )
        failed += not verdict["passed"]
    return 1 if failed else 0


def preflight(chosen: tuple[Subject, ...]) -> None:
    """The hand-written control, at this commit, before a registered run's first
    trial. Evaluated and not written: writing would change the committed control
    records, and the tree guard would then refuse every trial."""
    failing = []
    for subject in chosen:
        record = run_handwritten(
            subject, WORK_DIR / "build" / "preflight", WORK_DIR / "target" / "slot-0"
        )
        if not record["iterations"][0]["passed"]:
            failing.append(f"{subject.node} ({','.join(record['iterations'][0]['classes'])})")
    if failing:
        raise RegistrationError(
            "the hand-written control does not pass at this commit, so the instrument is "
            "wrong: " + ", ".join(failing)
        )


def registered(*, jobs: int, ceiling: float, priority: dict, skip_preflight: bool = False) -> int:
    """Run (or resume) the registered replication, exactly as registered."""
    try:
        commit = registration.check_ready()
        design = registration.load()
        chosen = tuple(BY_NODE[n] for n in design["nodes"])
        if not skip_preflight:
            print("preflight: the hand-written control at this commit…", flush=True)
            preflight(chosen)
    except RegistrationError as e:
        print(f"refused: {e}", file=sys.stderr)
        return EXIT_REFUSED

    def annotate() -> dict:
        return {"registration": commit, "head": registration.head(), "priority": priority}

    try:
        return run(
            design["run_id"],
            chosen,
            list(design["conditions"]),
            list(design["models"]),
            design["n"],
            jobs=jobs,
            ceiling=ceiling,
            model_ids=design["models"],
            guard=registration.check_tree,
            annotate=annotate,
        )
    except RegistrationError as e:
        print(f"stopped: {e}", file=sys.stderr)
        return EXIT_REFUSED


# ── results.json: derived from the runs ──────────────────────────────


def _summarise(record: dict, run_id: str) -> dict:
    """A trial with the bulk removed: verdicts kept, replies and files dropped."""
    return {
        "run": run_id,
        "trial": record["trial"],
        "node": record["node"],
        "group": record["group"],
        "arm": record["arm"],
        "model": record["model"],
        "model_id": record.get("model_id", record["model"]),
        "n": record["n"],
        "outcome": record["outcome"],
        "iterations_to_green": record["iterations_to_green"],
        "iterations": [
            {
                "classes": i["classes"],
                "passed": i["passed"],
                "ambient": i["ambient"],
                "declared_ungranted": i["declared_ungranted"],
                "gate_off": i["gate_off"],
                "matches_reference": i["matches_reference"],
            }
            for i in record["iterations"]
        ],
    }


def derive_results(runs_dir: Path = RUNS_DIR) -> dict:
    """Every recorded trial, summarised, in a stable order."""
    trials = []
    for path in sorted(runs_dir.glob("*/*.json")):
        trials.append(_summarise(json.loads(path.read_text()), path.parent.name))
    return {"max_iterations": MAX_ITERATIONS, "trials": trials}


def write_results() -> int:
    data = derive_results()
    _write(RESULTS_PATH, data)
    print(f"wrote {RESULTS_PATH.relative_to(REPO_ROOT)}: {len(data['trials'])} trials")
    return EXIT_OK


def rebuild(run_id: str, trial: str, out: Path) -> int:
    """Rebuild a recorded trial's passing body into a component file.

    Built components are not committed — only the sources a model returned are —
    so a body that is to be *used* (swapped into a live run of the service) is
    rebuilt from its record, and put through the whole pipeline again on the way:
    what is written to `out` passed the gate, its contract and its graph run a
    second time, here, and is not taken on the record's word."""
    record = json.loads((RUNS_DIR / run_id / f"{trial}.json").read_text())
    final = record["iterations"][-1]
    if not final["passed"]:
        print(f"{trial} never reached green; there is no passing body to rebuild")
        return 1
    crate = WORK_DIR / "build" / "rebuild"
    verdict = pipeline.evaluate(
        BY_NODE[record["node"]], final["files"], crate, WORK_DIR / "target" / "rebuild"
    )
    if not verdict.passed:
        print(f"{trial}: the recorded body no longer passes: {verdict.classes} — {verdict.detail}")
        return 1
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes((crate / "node.wasm").read_bytes())
    print(f"wrote {out} ({out.stat().st_size} bytes) from {run_id}/{trial}")
    return EXIT_OK


# ── Command line ─────────────────────────────────────────────────────


def _chosen(args: argparse.Namespace) -> tuple[Subject, ...]:
    if args.nodes:
        return tuple(BY_NODE[n] for n in args.nodes)
    return subjects(args.group)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="poc.generation.harness")
    commands = parser.add_subparsers(dest="command", required=True)

    def scope(p: argparse.ArgumentParser) -> None:
        p.add_argument("--group", choices=("pilot", "toy"), help="which subjects (default: all)")
        p.add_argument("--nodes", nargs="+", metavar="NODE", help="or name them")

    p_run = commands.add_parser("run", help="run (or resume) a set of trials")
    scope(p_run)
    p_run.add_argument("--run-id", required=True)
    p_run.add_argument("--arms", nargs="+", default=list(task.ARMS), choices=task.ARMS)
    p_run.add_argument("--models", nargs="+", default=list(MODELS))
    p_run.add_argument("-n", type=int, default=5, help="trials per (node, arm, model)")

    def running(p: argparse.ArgumentParser) -> None:
        p.add_argument("--jobs", type=int, default=DEFAULT_JOBS)
        p.add_argument(
            "--ceiling",
            type=float,
            default=0.6,
            help="stop when any usage window of the subscription reaches this fraction",
        )
        p.add_argument(
            "--no-nice",
            action="store_true",
            help="do not lower priority (for an idle machine); the default runs at the lowest",
        )

    running(p_run)
    running(
        commands.add_parser(
            "registered", help="run (or resume) the registered replication, as registered"
        )
    )

    scope(commands.add_parser("handwritten", help="the control: hand-written bodies"))
    commands.add_parser("results", help="derive results.json from the recorded runs")
    p_build = commands.add_parser("rebuild", help="rebuild a recorded passing body to a file")
    p_build.add_argument("--run-id", required=True)
    p_build.add_argument("--trial", required=True)
    p_build.add_argument("--out", type=Path, required=True)

    args = parser.parse_args(argv)
    if args.command == "results":
        return write_results()
    # Everything below builds crates or calls models: lowered here, once, so every
    # child process inherits it (poc/polite.py).
    priority = lower_priority(not getattr(args, "no_nice", False))
    if args.command == "rebuild":
        return rebuild(args.run_id, args.trial, args.out)
    if args.command == "handwritten":
        return handwritten(_chosen(args))
    if args.command == "registered":
        return registered(jobs=args.jobs, ceiling=args.ceiling, priority=priority)
    return run(
        args.run_id,
        _chosen(args),
        args.arms,
        args.models,
        args.n,
        jobs=args.jobs,
        ceiling=args.ceiling,
    )


if __name__ == "__main__":
    sys.exit(main())
