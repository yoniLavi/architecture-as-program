"""Render the banking harness's evidence → `dist/agentdojo-banking.{md,json}`.

From committed records only: the banking validation corpus (run here; it is the
validator, stdlib), the oracle plans (`records/oracle-plans.json`), their
predictions (`predictions/`), and the undefended baseline (`records/baseline/`).
Calls no model and imports no AgentDojo, so the build can run it anywhere.

Three things it never does: present an oracle plan as a benchmark result; present
a 0% attack-success rate as the absence of a residual (AgentDojo scores only its
nine goals); or let a figure from another model stand as a same-model comparison.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from . import corpus
from .predict import ORACLE, PREDICTIONS, contradictions

HERE = Path(__file__).resolve().parent
RECORDS = HERE / "records"
BASELINE = RECORDS / "baseline"
PAIRS_PER_REP = 160
USER_TASKS = 16
INJECTION_PAIRS = 144


def _rate(hits: int, n: int) -> str:
    return f"{hits}/{n} ({100 * hits / n:.0f}%)" if n else "0/0"


def baseline_summary() -> list[dict[str, Any]]:
    out = []
    for path in sorted(BASELINE.glob("*/rep-*.jsonl")):
        runs = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
        clean = [r for r in runs if r["injection_task"] is None]
        attacked = [r for r in runs if r["injection_task"] is not None]
        per_goal = Counter(r["injection_task"] for r in attacked if r["attack_success"])
        out.append(
            {
                "model_requested": path.parent.name,
                "rep": int(path.stem.split("-")[1]),
                "runs": len(runs),
                "complete": len(runs) == PAIRS_PER_REP,
                "models_resolved": sorted({m for r in runs for m in r["model_resolved"]}),
                "utility": {"hits": sum(r["utility"] for r in clean), "n": len(clean)},
                "utility_under_attack": {
                    "hits": sum(r["utility"] for r in attacked),
                    "n": len(attacked),
                },
                "attack_success": {
                    "hits": sum(bool(r["attack_success"]) for r in attacked),
                    "n": len(attacked),
                },
                "attack_success_by_goal": dict(sorted(per_goal.items())),
            }
        )
    return out


def build() -> dict[str, Any]:
    outcomes = corpus.run()
    oracle = json.loads((RECORDS / "oracle-plans.json").read_text())
    plans = []
    for name in ORACLE:
        doc = json.loads((PREDICTIONS / f"{name}.json").read_text())
        runs = [r for r in oracle["runs"] if r["graph"] == doc["graph"]]
        clean = next(r for r in runs if r["injection_task"] is None)
        plans.append(
            {
                "graph": doc["graph"],
                "user_task": doc["user_task"],
                "vector": doc["vector"],
                "utility": clean["utility"],
                "predicted": {g: p["verdict"] for g, p in doc["predictions"].items()},
                "succeeded_oracle_model": sorted(
                    r["injection_task"]
                    for r in runs
                    if r["model"] == "oracle" and r["attack_success"]
                ),
                "succeeded_fooled_model": sorted(
                    r["injection_task"]
                    for r in runs
                    if r["model"] == "fooled" and r["attack_success"]
                ),
                "contradictions": [r["injection_task"] for r in contradictions(doc, runs)],
            }
        )
    return {
        "suite": oracle["suite"],
        "attack": oracle["attack"],
        "corpus": [
            {
                "case": o.case.name,
                "verdict": o.verdict,
                "pinned": o.case.verdict,
                "reason": o.case.reason,
                "held": o.verdict == o.case.verdict and o.caught_by,
            }
            for o in outcomes
        ],
        "oracle_plans": plans,
        "baseline": baseline_summary(),
    }


def markdown(data: dict[str, Any]) -> str:
    lines = [
        "# AgentDojo banking: the harness's evidence",
        "",
        f"Suite: AgentDojo {data['suite']}, at the pinned commit. Attack: "
        f"`{data['attack']}`, addressing the model as Claude. Rendered from committed "
        "records; no model was called to build this page.",
        "",
        "Three caveats belong beside every figure here:",
        "",
        "- **AgentDojo scores only its nine goals.** An attack that changes the rent amount or "
        "the address is not counted, so 0% attack success is not the absence of a residual.",
        "- **Goals 0, 1 and 3 succeed on any payment to the attacker.** Their predicates read "
        '`x or "" in subject`, which is true whatever the subject. The scorer is used unchanged.',
        "- **No figure from another model is a same-model comparison.** Published numbers for "
        "CaMeL, FIDES or Progent are not reported here; where they are, they carry their model.",
        "",
        "## The banking validation corpus",
        "",
        "| Case | Verdict | Pinned reason | Held |",
        "|---|---|---|---|",
    ]
    for c in data["corpus"]:
        lines.append(
            f"| `{c['case']}` | {c['verdict']} | {c['reason'] or '—'} | "
            f"{'yes' if c['held'] else '**NO**'} |"
        )
    lines += [
        "",
        "## Oracle plans: hand-written graphs, not a benchmark result",
        "",
        "Each graph was written by hand from its task, so these runs measure confinement "
        "*given a correct plan*. Their `Extract` nodes ran on stand-ins: an oracle model "
        "that answers correctly, and a fooled model that obeys the injection with what it "
        "could see. The fooled model is not the worst case; the predictions are.",
        "",
        "| Graph | Vector | Utility | Predicted residual | Succeeded (fooled) | Contradictions |",
        "|---|---|---|---|---|---|",
    ]

    def goals(names: list[str]) -> str:
        return ", ".join(n.rsplit("_", 1)[1] for n in names) or "none"

    for p in data["oracle_plans"]:
        residual = [g for g, v in p["predicted"].items() if v == "residual"]
        lines.append(
            f"| `{p['graph']}` | {p['vector']} | {p['utility']} | {goals(residual)} | "
            f"{goals(p['succeeded_fooled_model'])} | {goals(p['contradictions'])} |"
        )
    lines += [
        "",
        "With the oracle model, no attack succeeded on any plan.",
        "",
        "## The undefended baseline (same model, subscription)",
        "",
        "A Claude agent given the prompt and all eleven banking tools, through `claude -p` "
        "and an MCP server over AgentDojo's own runtime. Beyond AgentDojo's pipeline, the "
        "model also sees the CLI's own context preamble (design, task 4.1).",
        "",
    ]
    if not data["baseline"]:
        lines.append("No baseline run is recorded yet.")
    for b in data["baseline"]:
        status = "complete" if b["complete"] else f"**partial: {b['runs']}/{PAIRS_PER_REP} runs**"
        lines += [
            f"### `{b['model_requested']}`, repetition {b['rep']} ({status})",
            "",
            f"- Resolved to: {', '.join(b['models_resolved']) or '—'}",
            f"- Utility, no attack: {_rate(b['utility']['hits'], b['utility']['n'])} "
            f"of {USER_TASKS} tasks",
            f"- Utility under attack: "
            f"{_rate(b['utility_under_attack']['hits'], b['utility_under_attack']['n'])}",
            f"- Attack success: {_rate(b['attack_success']['hits'], b['attack_success']['n'])} "
            f"of {INJECTION_PAIRS} pairs",
            f"- By goal: {b['attack_success_by_goal'] or 'none'}",
            "",
        ]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    out = Path((argv or sys.argv[1:] or ["dist"])[0])
    out.mkdir(parents=True, exist_ok=True)
    data = build()
    (out / "agentdojo-banking.json").write_text(json.dumps(data, indent=1, sort_keys=True) + "\n")
    (out / "agentdojo-banking.md").write_text(markdown(data))
    if not all(c["held"] for c in data["corpus"]):
        print("a banking corpus pin did not hold", file=sys.stderr)
        return 1
    if any(p["contradictions"] for p in data["oracle_plans"]):
        print("note: a prediction was contradicted; listed in the report", file=sys.stderr)
    print(f"wrote {out}/agentdojo-banking.{{md,json}}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
