"""Re-check every accepted pilot trial under the hardened gate. Calls no model.

    cd spikes/specified-architecture
    PYTHONPATH=../../scripts:../.. ../../.venv/bin/python -m s3.pilot.reaudit

Why: the adversarial review of 18 November 2026 showed the pilot's `gate()` (and the
first `check.sh`) could be fooled. A proof file can redefine `#print axioms` with
`macro_rules`, so a `sorry` proof printed clean, and it can run code at build time.
The pilot's own records were inspected (no command-level macro, `#eval` or `sorryAx`
in any accepted file), but "the gate was never fooled" cannot rest on a gate that
can be. This replays each accepted trial's final reply through `hardened_gate`,
the same checks as `s3/check.sh` (see its header), and writes `reaudit.json`.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
from pathlib import Path

from s3.pilot.pilot import LEAN, S3, TARGETS, WORK, blocks, run, setup_work, translate_body

HERE = Path(__file__).resolve().parent
FORBIDDEN = re.compile(
    r"^\s*(axiom|opaque|unsafe|@\[extern|@\[implemented_by|initialize|builtin_initialize)"
    r"|debug\.skipKernelTC|native_decide|ofReduceBool|#eval|run_cmd|run_elab|run_meta"
    r"|run_tac|IO\.|sorry|sorryAx|\badmit\b",
    re.M,
)
OLEANS = ["Cores.olean", "Statements.olean"]


def _hash(paths: list[Path]) -> list[str]:
    return [hashlib.sha256(p.read_bytes()).hexdigest() for p in paths]


def hardened_gate(lean: str, target: str) -> tuple[bool, str]:
    pinned = {
        name: digest
        for digest, name in (
            line.split() for line in (S3 / "statements.sha256").read_text().splitlines() if line
        )
    }
    if (
        hashlib.sha256((WORK / "Statements.lean").read_bytes()).hexdigest()
        != pinned["Statements.lean"]
    ):
        raise RuntimeError("the work copy of the statements drifted: harness fault")
    m = FORBIDDEN.search(lean)
    if m:
        return False, f"REFUSED (scan): forbidden construct {m.group(0)!r}"
    (WORK / "Trial.lean").write_text(lean)
    code, out = run(["lake", "build", "Cores", "Statements"], WORK)
    if code != 0:
        return False, "REFUSED: the pinned code does not build\n" + out[-1500:]
    lib = WORK / ".lake" / "build" / "lib" / "lean"
    before = _hash([lib / o for o in OLEANS])
    build = (WORK / ".lake" / "build").resolve()
    profile = (
        "(version 1)(allow default)(deny network*)(deny file-write*)"
        f'(allow file-write* (subpath "{build}") (subpath "/private/var/folders")'
        ' (literal "/dev/null"))'
    )
    code, out = run(["sandbox-exec", "-p", profile, "lake", "build", "Trial"], WORK)
    if code != 0:
        return False, "REFUSED: does not build in the sandbox\n" + out[-1500:]
    if _hash([lib / o for o in OLEANS]) != before:
        return False, "REFUSED: building the proof changed the compiled statements or code"
    stmt = TARGETS[target][0]
    audit = str(S3 / "audit" / "Audit.lean")
    code, out = run(["lake", "env", "lean", "--run", audit, "Trial", f"Trial.holds={stmt}"], WORK)
    if code != 0:
        return False, "REFUSED: audit failed\n" + out[-1500:]
    return True, "ACCEPTED\n" + out[-600:]


def main() -> None:
    setup_work()
    rows = [json.loads(x) for x in (HERE / "runs" / "pilot.jsonl").read_text().splitlines()]
    results = []
    for r in rows:
        if not r.get("accepted_on"):
            continue
        reply = r["attempts"][-1]["response"]
        lean = blocks(reply, "lean")
        assert lean is not None
        if r["arm"] == "body+proof":
            rust = blocks(reply, "rust")
            assert rust is not None
            ok, why = translate_body(rust, r["target"])
            if not ok:
                raise RuntimeError(f"re-translation failed on an accepted trial: {why[:300]}")
        else:
            shutil.copy(LEAN / "Cores.lean", WORK / "Cores.lean")
        ok, verdict = hardened_gate(lean, r["target"])
        key = f"{r['arm']} / {r['target']} / {r['model']} / rep {r['rep']}"
        results.append({"trial": key, "accepted": ok, "verdict": verdict[:800]})
        print(key, "ACCEPTED" if ok else verdict.splitlines()[0])
    summary = {
        "accepted_by_pilot_gate": len(results),
        "accepted_by_hardened_gate": sum(x["accepted"] for x in results),
        "trials": results,
    }
    (HERE / "reaudit.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(summary["accepted_by_hardened_gate"], "of", len(results), "still accepted")


if __name__ == "__main__":
    main()
