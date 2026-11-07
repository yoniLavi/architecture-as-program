"""The slice's report (task 5.2): `dist/slice.{md,json}`, from committed records alone.

Exploratory, one author, a few graphs: its findings shape the plan and the papers'
framing, and are never a figure in a paper. It calls no model and is stdlib-only.

It gathers, by step:
* step 3's scope-binding check, replayed over the registered run (1.2);
* step 4's behaviour-shown reviewer, replayed over the registered run (2.1);
* step 6's minimiser over the registered graphs (4.1);
* the slice's own units (5.1), each step's outcome;
* steps 7 and 8, the author's verdicts beside the AI reviewer's and the labels', grant
  by grant, once the author has filled them (4.3); until then, marked pending.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from ..architect import formal, labels
from . import replay
from . import review as behaviour
from .minimise import minimise
from .page import RUNS, VERDICTS, _review_of_final

NOTE = (
    "Exploratory: one author, a few graphs, Haiku in every role, not registered. Its "
    "findings shape the plan and the papers' framing; none is a figure in a paper."
)


def _unit(record: dict) -> dict[str, Any]:
    graph = record.get("final_graph") or {}
    label = labels.label(record["task"])
    devs = []
    for d in record.get("developers") or []:
        dev = d["developer"]
        row = {"node": d["node"], "outcome": dev["outcome"],
               "attempts": len(dev.get("attempts", []))}  # fmt: skip
        if d.get("escalation"):
            row["requested"] = dev["escalation"]["capability"]
            row["decision"] = d["escalation"]["decision"]["outcome"]
            row["granted"] = d["escalation"]["decision"].get("changed", [])
            row["after"] = (d.get("after_escalation") or {}).get("outcome")
        probe = d.get("pretext_probe")
        if probe:
            classes = [(a.get("verdict") or {}).get("class") for a in probe["attempts"]]
            row["pretext_probe"] = {"outcome": probe["outcome"], "classes": classes,
                                    "escalated": probe["outcome"] == "escalated"}  # fmt: skip
        devs.append(row)
    verdict_path = VERDICTS / f"{record['unit']}.json"
    author = json.loads(verdict_path.read_text()) if verdict_path.exists() else None
    primary, behaviour_view, _ = _review_of_final(record)

    def said(review: dict | None, cap: str) -> str | None:
        return ((review or {}).get("verdicts") or {}).get(cap, {}).get("verdict")

    grants = []
    for cap in graph.get("capabilities", []):
        own = ((author or {}).get("grants") or {}).get(cap) or {}
        grants.append({
            "grant": cap,
            "label": "within" if formal.within(cap, label) else "widening",
            "primary": said(primary, cap),
            "behaviour": said(behaviour_view, cap),
            "author": own.get("verdict"),
        })  # fmt: skip
    final = (record.get("utility") or {}).get("final") or {}
    return {
        "unit": record["unit"],
        "hand_built": bool(record.get("hand_built")),
        "outcome": record.get("outcome"),
        "custom_nodes": [n["name"] for n in graph.get("nodes", []) if n["uses"] == "Custom"],
        "developers": devs,
        "minimised": [
            r["grant"] for r in (record.get("minimise") or {}).get("report", []) if r["changed"]
        ],
        "utility": final.get("utility") if final.get("ran", True) else None,
        "failure": final.get("failure") or final.get("why"),
        "residual_goals": sorted(
            g
            for g, p in (record.get("predictions") or {}).get("predictions", {}).items()
            if p["verdict"] == "residual"
        ),
        "grants": grants,
        "author_outcome": ((author or {}).get("outcome") or {}).get("verdict"),
        "author_filled": bool(author and author.get("date")),
    }


def build() -> dict[str, Any]:
    records = [json.loads(p.read_text()) for p in sorted(RUNS.glob("*.json"))]
    registered = replay.trials()
    rows = [minimise(r["architect"]["graph"])[1] for r in registered]
    return {
        "note": NOTE,
        "scope_binding_replay": {v: replay.replay(registered)[v]["total"] for v in replay.VARIANTS},
        "behaviour_replay": behaviour.summarise(behaviour.load()),
        "minimiser_registered": {
            "graphs": len(rows),
            "grants": sum(map(len, rows)),
            "narrowed": sum(x["changed"] for row in rows for x in row),
        },
        "units": [_unit(r) for r in records],
    }  # fmt: skip


def _cell(v: object, missing: str = "pending") -> str:
    return missing if v is None else str(v)


def markdown(data: dict[str, Any]) -> str:
    sb = data["scope_binding_replay"]
    br = data["behaviour_replay"]
    mr = data["minimiser_registered"]
    p, b = br["primary"], br["behaviour"]
    out = [
        "# The vertical slice",
        "",
        f"_{data['note']}_",
        "",
        "## Replays over the registered architect run (shadow mode)",
        "",
        f"- **Scope-binding link check** (step 3, task 1.2): bound to the quote, it flagged "
        f"{sb['quote']['unseen_flagged']} of {sb['quote']['unseen']} unseen widenings, with "
        f"{sb['quote']['false_alarms']} false alarms. Bound to the prompt, it flagged "
        f"{sb['prompt']['unseen_flagged']}.",
        f"- **Behaviour-shown reviewer** (step 4, task 2.1): it caught {b['caught']} of "
        f"{b['widened_trials']} widened trials, against {p['caught']} for the registered "
        f"reviewer on the same graphs. It flagged {b['clean_trials_flagged']} of "
        f"{b['clean_trials']} clean trials, against {p['clean_trials_flagged']}.",
        f"- **Minimiser** (step 6, task 4.1): it narrowed {mr['narrowed']} of {mr['grants']} "
        f"grants in {mr['graphs']} graphs.",
        "",
        "## The slice's units (task 5.1)",
        "",
        "| Unit | Custom nodes | Developer | Minimised | Utility | Residual goals | "
        "Author: outcome |",
        "|---|---|---|---|---|---|---|",
    ]
    for u in data["units"]:
        dev = "; ".join(
            f"{d['node']}: {d['outcome']}"
            + (f" (asked `{d['requested']}`, {d['decision']}, granted {d['granted']}, then "
               f"{d['after']})" if d.get("requested") else "")
            + (f"; P5 probe: {d['pretext_probe']['outcome']}" if d.get("pretext_probe") else "")
            for d in u["developers"]
        ) or "none"  # fmt: skip
        name = u["unit"] + (" (hand-built)" if u["hand_built"] else "")
        out.append(
            f"| {name} | {', '.join(u['custom_nodes']) or 'none'} | {dev} | "
            f"{len(u['minimised'])} | {_cell(u['utility'], 'not run')} | "
            f"{len(u['residual_goals'])} | "
            f"{_cell(u['author_outcome'])} |"
        )
    out += [
        "",
        "## Grant by grant: the labels, the AI reviewer and the author (steps 4 and 8)",
        "",
        "The author's verdicts are one person's judgement, never a study.",
        "",
        "| Unit | Grant | Label | Primary | Behaviour | Author |",
        "|---|---|---|---|---|---|",
    ]
    for u in data["units"]:
        for g in u["grants"]:
            out.append(
                f"| {u['unit']} | `{g['grant']}` | {g['label']} | {_cell(g['primary'], '—')} | "
                f"{_cell(g['behaviour'], '—')} | {_cell(g['author'])} |"
            )
    return "\n".join(out) + "\n"


def main(argv: list[str] | None = None) -> int:
    out = Path((argv or sys.argv[1:] or ["dist"])[0])
    out.mkdir(parents=True, exist_ok=True)
    data = build()
    (out / "slice.json").write_text(json.dumps(data, indent=1, sort_keys=True) + "\n")
    (out / "slice.md").write_text(markdown(data))
    print(f"wrote {out}/slice.{{md,json}}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
