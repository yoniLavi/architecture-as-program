"""The human-review page (task 4.2): one per slice unit, for the author's steps 7 and 8.

Rendered from the unit's committed record alone, calling no model. It shows the task's
prompt; the final graph as a listing; what each grant would do (the behaviour view,
with the architect's node names); and, per grant, what the AI reviewer said in each
view, what the developer asked for, and what the minimiser would remove. The labels
are not shown: they are the measurement the author's verdicts are compared with, in
the report, and showing them would turn a verdict into agreement.

Beside each page, a verdict file (`poc/slice/verdicts/<unit>.json`) with an empty
verdict per grant and on the outcome, for the author to fill. Once filled it is
committed as written and never regenerated: `write` creates a file only if none exists.
"""

from __future__ import annotations

import json
from pathlib import Path

from .behaviour import render

HERE = Path(__file__).resolve().parent
RUNS = HERE / "runs" / "slice"
PAGES = HERE / "pages"
VERDICTS = HERE / "verdicts"
SCALE = ("needed", "wider", "not-needed")


def _listing(graph: dict) -> str:
    caps = set(graph["capabilities"])
    lines = []
    for n in graph["nodes"]:
        data = [i for i in n["inputs"] if i not in caps]
        held = [i for i in n["inputs"] if i in caps]
        lines.append(f"{n['name']} [{n['uses']}] : ({', '.join(data)}) -> {n['output']}")
        if held:
            lines.append(f"    with {', '.join(held)}")
        for k, v in (n.get("params") or {}).items():
            lines.append(f"    {k}: {json.dumps(v, ensure_ascii=False)}")
    lines.append("")
    for e in graph["data_edges"]:
        pos = f" (input {e['to_input']})" if "to_input" in e else ""
        lines.append(f"{e['from']} -> {e['to']}{pos}")
    return "\n".join(lines)


def _verdict(review: dict | None, cap: str) -> str:
    v = ((review or {}).get("verdicts") or {}).get(cap)
    if not v:
        return "no verdict"
    out = f"**{v['verdict']}**"
    if v.get("quote"):
        out += f", quoting “{v['quote']}”"
    if v.get("narrower"):
        out += f"; would do: `{v['narrower']}`"
    return out


def _review_of_final(record: dict) -> tuple[dict | None, dict | None, str]:
    """(primary, behaviour, which graph they judged) for the final graph."""
    for d in record.get("developers", []):
        decision = (d.get("escalation") or {}).get("decision") or {}
        if decision.get("outcome") == "accepted":
            return None, decision.get("review"), "the edited graph (behaviour view only)"
    reviews = record.get("reviews") or {}
    return reviews.get("primary"), reviews.get("behaviour"), "the architect's graph"


def page(record: dict) -> str:
    graph = record["final_graph"]
    primary, behaviour, judged = _review_of_final(record)
    minimised = {r["grant"]: r for r in record["minimise"]["report"]}
    out = [
        f"# Slice review: {record['task']}, {record['condition']}",
        "",
        "One person's judgement on one graph: a verdict on each grant (step 8) and on the "
        "outcome (step 7). Fill `poc/slice/verdicts/" + record["unit"] + ".json`.",
        "",
        *(
            [
                "**A hand-built graph.** The architect, offered the `Custom` entry, used it "
                "in none of the six units, so this graph was built by hand to put a custom "
                "node before the developer. The architect appears only if the developer's "
                "request reached it as an edit.",
                "",
            ]
            if record.get("hand_built")
            else []
        ),
        "## The task, as the architect and the reviewer saw it",
        "",
        "> " + record["prompt"].replace("\n", "\n> "),
        "",
        "## The final graph",
        "",
        "```",
        _listing(graph),
        "```",
        "",
        "## What each grant would do",
        "",
        "Computed from the graph, not written by the architect.",
        "",
        "```",
        render(graph),
        "```",
        "",
        f"## Each grant: the AI reviewer (on {judged}) and the minimiser",
        "",
    ]
    for cap in graph["capabilities"]:
        m = minimised.get(cap, {})
        narrowed = m.get("narrowed")
        trim = "unchanged" if not m.get("changed") else (
            "drop it" if narrowed is None else f"`{narrowed}`")  # fmt: skip
        out += [
            f"### `{cap}`",
            "",
            f"- AI reviewer, primary view: {_verdict(primary, cap)}",
            f"- AI reviewer, behaviour shown: {_verdict(behaviour, cap)}",
            f"- The minimiser would narrow it to: {trim}",
            f"- **Your verdict** ({' / '.join(SCALE)}):",
            "",
        ]
    out += ["## The developer", ""]
    devs = record.get("developers") or []
    if not devs:
        out.append("No `Custom` node: the architect used the library only.")
    for d in devs:
        rec = d.get("after_escalation") or d["developer"]
        out.append(f"- `{d['node']}`: {d['developer']['outcome']}"
                   + (f"; requested `{d['developer']['escalation']['capability']}`, "
                      f"{d['escalation']['decision']['outcome']}" if d.get("escalation") else "")
                   + (f"; then {rec['outcome']}" if d.get("after_escalation") else ""))  # fmt: skip
        probe = d.get("pretext_probe")
        if probe:
            out.append(f"  - with the P5 pretext: {probe['outcome']}")
    final = record["utility"]["final"]
    out += [
        "",
        "## The outcome (step 7)",
        "",
        f"- AgentDojo utility: **{final.get('utility')}**"
        + ("" if final.get("ran") else f" (not run: {final.get('why')})"),
        f"- The answer the user got: “{final.get('answer', '')}”",
        f"- Failure, if any: {final.get('failure') or 'none'}",
        "- Bank calls made: "
        + (
            ", ".join(
                f"`{c['function']}({json.dumps(c['args'], ensure_ascii=False)})`"
                for c in final.get("calls", [])
            )
            or "none"
        ),
        "- **Your verdict** on the outcome (accept / reject), and why:",
        "",
    ]
    # No trailing whitespace: a committed page must survive the whitespace hook unchanged.
    return "\n".join(line.rstrip() for line in "\n".join(out).splitlines())


def verdict_template(record: dict) -> dict:
    return {
        "unit": record["unit"],
        "reviewer": "the author",
        "date": None,
        "grants": {c: {"verdict": None, "note": ""} for c in record["final_graph"]["capabilities"]},
        "outcome": {"verdict": None, "note": ""},
        "scale": {"grants": list(SCALE), "outcome": ["accept", "reject"]},
    }


def write() -> list[str]:
    PAGES.mkdir(exist_ok=True)
    VERDICTS.mkdir(exist_ok=True)
    wrote = []
    for path in sorted(RUNS.glob("*.json")):
        record = json.loads(path.read_text())
        if record.get("outcome") != "complete":
            continue
        (PAGES / f"{record['unit']}.md").write_text(page(record) + "\n")
        v = VERDICTS / f"{record['unit']}.json"
        if not v.exists():
            v.write_text(json.dumps(verdict_template(record), indent=1, ensure_ascii=False) + "\n")
            wrote.append(v.name)
    return wrote


if __name__ == "__main__":
    print(write())
