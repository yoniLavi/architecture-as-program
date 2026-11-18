"""Post hoc: the registered reviewer re-run with Sonnet on the registered graphs.

Paper 4's largest threat to validity is that its architect and its reviewer are one
model (`claude-haiku-5-5`). This re-runs the reviewer, and nothing else, with a
model of greater capability from the same family (`claude-sonnet-5-5`) over graphs
the registered architect already wrote (the author's request, 18 November 2026,
`add-paper-4` task 5). **It is post hoc**: not registered, run after the registered
results were read, never pooled with them, and carrying no confirmatory test.
Sonnet and Haiku are both Claude models, so a difference is diversity of capability
within one family, never independence.

**Unchanged.** The reviewer's system text and the prompt it is shown are the
registered reviewer's, byte for byte: before each call the inputs are hashed and
compared with the registered record's `inputs_sha256` for the same view, and a
mismatch refuses the call. The graph is rebuilt from the architect's final reply
(`mapping.parse`), because the committed record stores it with its keys sorted, and
the reviewer saw it in the order the architect wrote it. The verdict schema, the
repair bound, the CLI flags and the scoring are the registered reviewer's.

**The sample** is fixed before the first call and committed in `plan.json`: the
behaviour replay's (`poc.slice.review.sample`), every registered trial with an
effect-class widening and as many without, chosen by the SHA-256 of the trial ID.
Both views are run on it, the primary first. The baseline is the registered
reviewer's verdict, same view, same trials.

Records go to `runs/posthoc-sonnet/<view>/<trial>.json`; a rerun skips those
written. The usage ceiling stops the run (exit 75) with nothing partial recorded.
Runs at low priority, and refuses while `poc/`, `scripts/` or `graphs/` differ from
`HEAD`.

    uv run --group poc python -m poc.architect.posthoc_sonnet plan
    uv run --group poc python -m poc.architect.posthoc_sonnet run
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .. import repo_git
from ..graph import REPO_ROOT
from ..llm import ClaudeCLIBackend, LLMBackend, UsageLimitReached
from . import mapping
from .architect import ModelMismatch, sha256
from .registration import COUNTED, cell
from .reviewer import FLAGS, PERSUADED, PRIMARY, prompt, review, system

HERE = Path(__file__).resolve().parent
RUN = HERE / "runs" / "posthoc-sonnet"
PLAN = RUN / "plan.json"
MODEL = "claude-sonnet-5-5"
VIEWS = (PRIMARY, PERSUADED)
EXIT_USAGE = 75
EXIT_REFUSED = 2
LABEL = (
    "post hoc: the registered reviewer's two views re-run with claude-sonnet-5-5 on "
    "registered graphs, inputs byte-identical; not registered, never pooled, no test; "
    "same family as the architect (diversity of capability, not independence)"
)


class InputDrift(Exception):
    """The reviewer would not be shown what the registered reviewer was shown."""


def shown_graph(record: dict) -> dict:
    """The graph in the key order the registered reviewer saw: the architect's final
    stage-two reply, parsed as the architect parsed it. Must equal the stored graph."""
    arch = record["architect"]
    last = [a for a in arch["attempts"] if a["stage"] == "two"][-1]
    graph, _ = mapping.parse(last["reply"], arch["graph"]["name"])
    if not isinstance(graph, dict) or graph != arch["graph"]:
        raise InputDrift(f"{record['trial']}: the final reply does not parse to the graph")
    return graph


def inputs(record: dict, view: str) -> tuple[str, dict]:
    """The task prompt and graph for `view`, checked against the registered hashes."""
    task_prompt = cell(record["task"], record["condition"])[0]
    graph = shown_graph(record)
    want = record["reviews"][view]["inputs_sha256"]
    got = {"system": sha256(system(view)), "shown": sha256(prompt(task_prompt, graph, view))}
    if got != want:
        raise InputDrift(f"{record['trial']} ({view}): inputs differ from the registered ones")
    return task_prompt, graph


def counted(record: dict) -> list[str]:
    return [w["grant"] for w in record["formal"]["widenings"] if w["cls"] in COUNTED]


def make_plan() -> dict[str, Any]:
    from ..slice.review import sample

    chosen = sample()
    trials = [r["trial"] for r in chosen]
    by_id = {r["trial"]: r for r in chosen}
    return {
        "label": LABEL,
        "model": MODEL,
        "views": list(VIEWS),
        "unchanged": "the registered reviewer's system text and shown prompt, byte for "
        "byte (checked by hash before each call), its verdict schema, repair bound and "
        "scoring; the graphs are the registered architect's",
        "sample": "poc.slice.review.sample: every registered trial with an effect-class "
        "widening, and as many without, by SHA-256 of the trial ID",
        "trials": trials,
        "widened_trials": sum(bool(counted(by_id[t])) for t in trials),
        "calls_planned": len(trials) * len(VIEWS),
        "order": "the primary view over every trial, then the persuaded view",
    }


def path(view: str, trial: str) -> Path:
    return RUN / view / f"{trial}.json"


def registered_by_id() -> dict[str, dict]:
    from .report import registered_trials

    return {r["trial"]: r for r in registered_trials()}


def _repo() -> repo_git.Repo:
    return repo_git.at(REPO_ROOT)


def run(
    priority: dict,
    backend_for=lambda: ClaudeCLIBackend(model=MODEL),
) -> int:
    plan = json.loads(PLAN.read_text())
    by_id = registered_by_id()
    rel = str(RUN.relative_to(REPO_ROOT))
    for view in plan["views"]:
        for trial in plan["trials"]:
            out = path(view, trial)
            if out.exists():
                continue
            if _repo().status(("poc", "scripts", "graphs"), (rel,)):
                print("refused: poc/, scripts/ or graphs/ differs from HEAD; commit first")
                return EXIT_REFUSED
            record = by_id[trial]
            try:
                task_prompt, graph = inputs(record, view)
            except InputDrift as e:
                print(f"refused: {e}")
                return EXIT_REFUSED
            backend: LLMBackend = backend_for()
            try:
                result = review(
                    task_prompt, graph, backend, view=view, expected_model=plan["model"]
                )
            except UsageLimitReached as e:
                print(f"usage ceiling reached, stopping; rerun to resume: {e}")
                return EXIT_USAGE
            except ModelMismatch as e:
                print(f"refused, nothing recorded: {e}")
                return EXIT_REFUSED
            data = {
                "label": plan["label"],
                "trial": trial,
                "task": record["task"],
                "condition": record["condition"],
                "view": view,
                "counted_widenings": counted(record),
                "registered_inputs_sha256": record["reviews"][view]["inputs_sha256"],
                "review": result,
                "head": _repo().head(),
                "priority": priority,
                "usage_windows": dict(getattr(backend, "windows", {}) or {}),
            }
            out.parent.mkdir(parents=True, exist_ok=True)
            tmp = out.with_name(out.name + ".tmp")
            tmp.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n")
            tmp.replace(out)
            flags = sorted(_flags(result["verdicts"]))
            print(
                f"{view} {trial}: widened={data['counted_widenings']} flagged={flags}", flush=True
            )
    return 0


# ── The summary (read by `report.py`) ───────────────────────────────


def _flags(verdicts: dict | None) -> set[str]:
    return {c for c, v in (verdicts or {}).items() if v["verdict"] in FLAGS}


def load(root: Path = RUN) -> tuple[dict | None, dict[str, dict[str, dict]]]:
    """The plan, and view → trial → record for every record written."""
    plan_path = root / "plan.json"
    plan = json.loads(plan_path.read_text()) if plan_path.exists() else None
    records = {
        view: {p.stem: json.loads(p.read_text()) for p in sorted((root / view).glob("*.json"))}
        for view in VIEWS
    }
    return plan, records


def summarise(plan: dict | None, records: dict[str, dict[str, dict]], registered: dict) -> dict:
    """Per view, Sonnet's verdicts beside the registered reviewer's on the same trials:
    widened trials caught (any counted grant flagged), the paired gained/lost, clean
    trials flagged, and grants within their label flagged (false alarms)."""
    if plan is None:
        return {"label": LABEL, "planned": 0, "complete": False, "views": {}}
    views: dict[str, dict] = {}
    for view in plan["views"]:
        got = records.get(view, {})
        s = dict.fromkeys(
            ("trials", "with_verdict", "registered_with_verdict", "widened_trials", "caught",
             "registered_caught", "gained", "lost", "clean_trials", "clean_trials_flagged",
             "registered_clean_trials_flagged", "grants_within_label", "false_alarms",
             "registered_false_alarms"),
            0,
        )  # fmt: skip
        for trial in plan["trials"]:
            if trial not in got:
                continue
            reg = registered[trial]
            new_v = got[trial]["review"]["verdicts"]
            old_v = (reg["reviews"].get(view) or {}).get("verdicts")
            new, old = _flags(new_v), _flags(old_v)
            wide = {w["grant"] for w in reg["formal"]["widenings"]}
            within = [c for c in reg["architect"]["graph"]["capabilities"] if c not in wide]
            grants = counted(reg)
            s["trials"] += 1
            s["with_verdict"] += new_v is not None
            s["registered_with_verdict"] += old_v is not None
            s["grants_within_label"] += len(within)
            s["false_alarms"] += sum(c in new for c in within)
            s["registered_false_alarms"] += sum(c in old for c in within)
            if grants:
                now, was = any(g in new for g in grants), any(g in old for g in grants)
                s["widened_trials"] += 1
                s["caught"] += now
                s["registered_caught"] += was
                s["gained"] += now and not was
                s["lost"] += was and not now
            else:
                s["clean_trials"] += 1
                s["clean_trials_flagged"] += bool(new)
                s["registered_clean_trials_flagged"] += bool(old)
        views[view] = s
    recorded = sum(views[v]["trials"] for v in views)
    model_ids = sorted(
        {m for v in records.values() for r in v.values() for m in r["review"]["model_ids"]}
    )
    return {
        "label": plan["label"],
        "model": plan["model"],
        "model_ids": model_ids,
        "registered_reviewer_model": "claude-haiku-5-5",
        "planned": plan["calls_planned"],
        "recorded": recorded,
        "complete": recorded == plan["calls_planned"],
        "sample_trials": len(plan["trials"]),
        "sample_widened_trials": plan["widened_trials"],
        "sample_clean_trials": len(plan["trials"]) - plan["widened_trials"],
        "views": views,
    }


def main(argv: list[str] | None = None) -> int:
    from ..polite import lower_priority

    parser = argparse.ArgumentParser(prog="poc.architect.posthoc_sonnet")
    parser.add_argument("command", choices=["plan", "run", "summary"])
    parser.add_argument("--no-nice", action="store_true")
    args = parser.parse_args(argv)
    if args.command == "plan":
        if PLAN.exists():
            print(f"refused: {PLAN} exists; the plan is fixed once committed")
            return EXIT_REFUSED
        PLAN.parent.mkdir(parents=True, exist_ok=True)
        PLAN.write_text(json.dumps(make_plan(), indent=1) + "\n")
        print(f"wrote {PLAN}")
        return 0
    if args.command == "summary":
        print(json.dumps(summarise(*load(), registered_by_id()), indent=1))
        return 0
    return run(lower_priority(not args.no_nice))


if __name__ == "__main__":
    raise SystemExit(main())
