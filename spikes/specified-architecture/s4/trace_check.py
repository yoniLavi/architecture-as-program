"""S4's check against the artifact: the shipped GenerateResponse component's
crossings, over every reply script, against the bound proved in Lean
(`s3/lean/Proofs.lean`, `respond_crossings_le`: at most 3 generates and 3 lookups,
so at most 6 crossings, for every model).

    cd spikes/specified-architecture
    PYTHONPATH=../../scripts:../.. uv run --project ../.. --group poc python -m s4.trace_check

"The contract's inputs" here are reply scripts: every sequence of four replies over
{text, call the granted tool, call another tool} (81 scripts; the fourth reply is
never reached, which is itself checked). The component is the committed
`poc/sandbox/wasm/node_generate_response.wasm`, unchanged; crossings are counted by
the host, in order, through `Sandbox`'s own wrapping. Writes trace_check.json.
"""

from __future__ import annotations

import itertools
import json
from pathlib import Path

from poc.sandbox.host import Sandbox, record
from poc.sandbox.interfaces import KB_READ, TOOL_LLM

PROVED_GENERATE_BOUND = 3
PROVED_LOOKUP_BOUND = 3
PROVED_CROSSING_BOUND = 6
OUT = Path(__file__).resolve().parent / "trace_check.json"
REPLIES = ("text", "call-granted", "call-other")


def run(script: tuple[str, ...]) -> tuple[list[str], int]:
    seq: list[str] = []
    rounds = iter(script)

    def generate(_system: str, _prompt: str):
        seq.append("generate")
        kind = next(rounds, "text")
        if kind == "text":
            return "an answer"
        tool = "lookup" if kind == "call-granted" else "exfiltrate"
        return record(tool=tool, query="q")

    def lookup(_query: str) -> list[str]:
        seq.append("lookup")
        return ["hit"]

    sb = Sandbox(
        "node_generate_response",
        {TOOL_LLM: {"generate": generate}, KB_READ: {"lookup": lookup}},
    )
    sb.call("run", record(intent="billing-question", question="Why?", knowledge=[]))
    return seq, sb.crossings


def core_log(script: tuple[str, ...]) -> list[str]:
    """The core's log (`cores::respond`), in Python: the same loop as the Rust core,
    which `cores/tests/differential.rs` holds to the shipped control flow."""
    log: list[str] = []
    for r in range(3):
        log.append("generate")
        kind = script[r] if r < len(script) else "text"
        if kind == "text" or kind == "call-other":
            break
        log.append("lookup")
    return log


def main() -> None:
    rows = []
    excess = 0
    for script in itertools.product(REPLIES, repeat=4):
        seq, crossings = run(script)
        assert crossings == len(seq), "the host's count and the logged sequence agree"
        over = (
            seq.count("generate") > PROVED_GENERATE_BOUND
            or seq.count("lookup") > PROVED_LOOKUP_BOUND
            or crossings > PROVED_CROSSING_BOUND
        )
        excess += over
        rows.append(
            {
                "script": list(script),
                "crossings": crossings,
                "sequence": seq,
                "matches_core_log": seq == core_log(script),
                "exceeds_proved_bound": over,
            }
        )
    out = {
        "component": "poc/sandbox/wasm/node_generate_response.wasm (unchanged)",
        "scripts": len(rows),
        "max_crossings": max(r["crossings"] for r in rows),
        "proved_bound": PROVED_CROSSING_BOUND,
        "excesses": excess,
        "sequence_mismatches_with_core": sum(not r["matches_core_log"] for r in rows),
        "bound_attained": any(r["crossings"] == PROVED_CROSSING_BOUND for r in rows),
        "rows": rows,
    }
    OUT.write_text(json.dumps(out, indent=2) + "\n")
    print({k: v for k, v in out.items() if k != "rows"})


if __name__ == "__main__":
    main()
