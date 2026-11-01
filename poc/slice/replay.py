"""The scope-binding link check, replayed over the registered architect run (task 1.2).

Shadow mode: the check (`formal.scope_binding`) is run over the committed records of
the registered run (`poc/architect/runs/registered/`), which it never changes, and
its findings are compared with what the run's own review found. It decides no
trial's outcome; the registered figures stay as `dist/architect.md` reports them.

Two variants, side by side: each literal scope element bound to its grant's **quote**
(the check as designed) and to the whole **prompt** (the weaker form). For each, the
replay counts the counted widenings it flags, the unseen ones among them (the ones
the link check and the reviewer both missed), and its false alarms: grants it flags
that the least-authority check finds within the label. It also counts the unseen
widenings it cannot reach at all, because every element of their scope is open
(`any`, `inbound-senders`, `uncapped`): the check's ceiling, not a miss.

Stdlib-only, and it calls no model.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from ..architect import formal
from ..architect.registration import CONDITIONS, COUNTED, cell

RECORDS = Path(__file__).resolve().parent.parent / "architect" / "runs" / "registered"
QUOTE = "quote"
PROMPT = "prompt"
VARIANTS = (QUOTE, PROMPT)


def trials(root: Path = RECORDS) -> list[dict]:
    """Every registered trial that produced a graph, in a fixed order."""
    out = []
    for condition in CONDITIONS:
        for path in sorted((root / condition).glob("*.json")):
            record = json.loads(path.read_text())
            if record.get("formal") is not None:
                out.append(record)
    return out


def replay(records: list[dict]) -> dict[str, dict]:
    """Per variant, the counts above, overall and by condition."""
    result: dict[str, dict] = {}
    for variant in VARIANTS:
        total: Counter = Counter()
        by_condition: dict[str, Counter] = {c: Counter() for c in CONDITIONS}
        examples: list[dict] = []
        for record in records:
            graph = record["architect"]["graph"]
            prompt = cell(record["task"], record["condition"])[0] if variant == PROMPT else None
            findings = formal.scope_binding(graph, prompt)
            flagged = {f.capability for f in findings}
            widenings = record["formal"]["widenings"]
            widened = {w["grant"] for w in widenings}
            counted = [w["grant"] for w in widenings if w["cls"] in COUNTED]
            unseen = record["unseen"]
            by_kind = {w["grant"] for w in widenings if w["by"] == formal.BY_KIND}
            row = Counter(
                graphs=1,
                literal_grants=sum(bool(formal.literal_scope(c)) for c in graph["capabilities"]),
                flagged=len(flagged),
                counted_widenings=len(counted),
                counted_flagged=sum(g in flagged for g in counted),
                unseen=len(unseen),
                unseen_flagged=sum(g in flagged for g in unseen),
                unseen_by_kind=sum(g in by_kind for g in unseen),
                unseen_open=sum(not formal.literal_scope(g) for g in unseen),
                false_alarms=len(flagged - widened),
            )
            # `update`, not `+=`: Counter addition drops the zero counts.
            total.update(row)
            by_condition[record["condition"]].update(row)
            for f in findings:
                if f.capability in unseen and len(examples) < 10:
                    examples.append({"trial": record["trial"], **f.as_dict()})
        result[variant] = {
            "total": dict(total),
            "by_condition": {c: dict(v) for c, v in by_condition.items()},
            "unseen_examples": examples,
        }
    return result


def unseen_breakdown(records: list[dict]) -> dict[str, int]:
    """The unseen widenings by kind, by how they widen, and whether their scope has a
    literal element at all: what any text-binding check could reach."""
    out: Counter = Counter()
    for record in records:
        how = {w["grant"]: w["by"] for w in record["formal"]["widenings"]}
        for grant in record["unseen"]:
            literal = "literal" if formal.literal_scope(grant) else "open"
            out[f"{formal.kind(grant)}, by {how[grant]}, {literal}"] += 1
    return dict(sorted(out.items(), key=lambda kv: (-kv[1], kv[0])))


def main() -> None:  # pragma: no cover - a reading aid
    print(json.dumps(replay(trials()), indent=1))


if __name__ == "__main__":  # pragma: no cover
    main()
