"""The model judges standing in for the author at steps 7 and 8 (task 4.3).

The author was unavailable and directed, on 7 November 2026, that fresh subagents judge
in their place. Two judges, A and B, each saw every review page **without** the AI
reviewer's verdicts and without the labels (the page minus its AI reviewer lines), and
judged independently, on the same scale the author would have used. Their verdicts are
a model's, never a person's, and the author's own verdict files
(`verdicts/<unit>.json`) stay as written: empty until the author fills them.

Each judge's reply is committed as given (`verdicts/judges-raw/<judge>.json`), and
split, by `record`, into one file per unit (`verdicts/<unit>.judges.json`). A reply that
misses a unit or a grant, or gives a verdict off the scale, is refused, not repaired.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from .page import RUNS, SCALE, VERDICTS

RAW = VERDICTS / "judges-raw"
OUTCOMES = ("accept", "reject")
VIEW = "the review page without the AI reviewer's verdicts, and without the labels"
NOTE = (
    "Model judges standing in for the author, at the author's direction (7 November "
    "2026); a model's verdicts, never a person's. The author's own file is beside this one."
)


def units() -> dict[str, list[str]]:
    out = {}
    for path in sorted(RUNS.glob("*.json")):
        r = json.loads(path.read_text())
        if r.get("outcome") == "complete":
            out[r["unit"]] = list(r["final_graph"]["capabilities"])
    return out


def check(reply: dict) -> list[str]:
    """Every problem with a judge's reply; empty if it covers everything on the scale."""
    problems = []
    got = reply.get("units") if isinstance(reply, dict) else None
    if not isinstance(got, dict):
        return ["no `units` object"]
    for unit, grants in units().items():
        u = got.get(unit)
        if not isinstance(u, dict):
            problems.append(f"{unit}: missing")
            continue
        for cap in grants:
            v = (u.get("grants") or {}).get(cap)
            if not isinstance(v, dict) or v.get("verdict") not in SCALE:
                problems.append(f"{unit}: {cap}: no verdict on the scale")
        if (u.get("outcome") or {}).get("verdict") not in OUTCOMES:
            problems.append(f"{unit}: no outcome verdict")
    return problems


def record(judge: str, reply: dict, *, model: str, date: str) -> None:
    """Commit-ready files for one judge's checked reply."""
    problems = check(reply)
    if problems:
        raise ValueError(f"judge {judge}: " + "; ".join(problems))
    RAW.mkdir(parents=True, exist_ok=True)
    (RAW / f"{judge}.json").write_text(json.dumps(reply, indent=1, ensure_ascii=False) + "\n")
    for unit in units():
        path = VERDICTS / f"{unit}.judges.json"
        data = (
            json.loads(path.read_text())
            if path.exists()
            else {"unit": unit, "note": NOTE, "judges": {}}
        )
        data["judges"][judge] = {"model": model, "date": date, "saw": VIEW,
                                 **reply["units"][unit]}  # fmt: skip
        path.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    # python -m poc.slice.judges <judge> <reply.json> <model> <date>
    name, reply_path, model_id, day = sys.argv[1:5]
    record(name, json.loads(Path(reply_path).read_text()), model=model_id, date=day)
    print(f"recorded judge {name}")
