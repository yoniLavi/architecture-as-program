"""Summarise runs/pilot.jsonl: counts per arm, target and model. Writes results.json.

python3 spikes/specified-architecture/s3/pilot/report.py
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main() -> None:
    rows = [json.loads(line) for line in (HERE / "runs" / "pilot.jsonl").read_text().splitlines()]

    def cell() -> dict:
        return {"trials": 0, "accepted": 0, "first_attempt": 0, "attempts_when_accepted": [],
                "differential_agrees": 0, "differential_disagrees": 0,
                "refusal_kinds": defaultdict(int)}  # fmt: skip

    cells: dict = defaultdict(cell)
    void = [r for r in rows if r.get("void")]
    rows = [r for r in rows if not r.get("void")]
    for r in rows:
        c = cells[f"{r['arm']} / {r['target']} / {r['model']}"]
        c["trials"] += 1
        if r["accepted_on"] is not None:
            c["accepted"] += 1
            c["first_attempt"] += r["accepted_on"] == 1
            c["attempts_when_accepted"].append(r["accepted_on"])
            if r.get("differential_agrees") is True:
                c["differential_agrees"] += 1
            elif r.get("differential_agrees") is False:
                c["differential_disagrees"] += 1
        for a in r["attempts"]:
            if not a["verdict"].startswith("ACCEPTED"):
                c["refusal_kinds"][a["verdict"].split("\n")[0][:60]] += 1
    out = {k: {**v, "refusal_kinds": dict(v["refusal_kinds"])} for k, v in sorted(cells.items())}
    voided = [{k: r[k] for k in ("arm", "target", "model", "rep", "void")} for r in void]
    (HERE / "results.json").write_text(json.dumps({"cells": out, "void": voided}, indent=2) + "\n")
    print(f"{len(rows)} counted trials, {len(void)} void (a failed model call, not counted)")
    print(f"{'cell':40} trials accepted first  attempts  diff(agree/disagree)")
    for k, v in out.items():
        diff = f"{v['differential_agrees']}/{v['differential_disagrees']}"
        print(f"{k:40} {v['trials']:6} {v['accepted']:8} {v['first_attempt']:5}  "
              f"{v['attempts_when_accepted']!s:9} {diff}")  # fmt: skip
    kinds: dict = defaultdict(int)
    for v in out.values():
        for kk, n in v["refusal_kinds"].items():
            kinds[kk] += n
    print("refusals by kind:", dict(kinds))


if __name__ == "__main__":
    main()
