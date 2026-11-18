"""S1's measurement: what fuel and epoch interruption cost. Writes results.json.

    uv run --group poc python -m s1.measure     (from spikes/specified-architecture,
                                                 with scripts/ and the repo root on
                                                 PYTHONPATH; see README)

Two costs, because fuel instruments the guest's code and the crossing band would
not see that:
* the **crossing**, by the benchmark's own method (`poc/sandbox/bench.py`): one
  component driven down two paths, answering directly (1 crossing) or through a
  tool round (3), differenced;
* **guest compute**: the spin guest's `burn(200_000)`, a loop with no crossing.

Each on four engines that differ only in fuel and epoch interruption, all built
from `engine_config()`. Timings are CPU time of the measuring thread, best of
several warmed rounds (the benchmark's `_time`), and the configurations are
interleaved round by round so drifting load lands on all of them alike.
"""

from __future__ import annotations

import json
import os
import platform
from pathlib import Path

from poc.handles import ReadDBHandle
from poc.sandbox.bench import _generate_answering, _generate_via_tool, _time
from poc.sandbox.host import record
from poc.sandbox.interfaces import KB_READ, TOOL_LLM
from poc.sandbox.nodes import _from_intent
from poc.values import ConversationContext, Intent

from .metered_sandbox import SPIKE_WASM, MeteredSandbox, StoreBudget

CONFIGS = {"plain": (False, False), "fuel": (True, False), "epoch": (False, True),
           "fuel+epoch": (True, True)}  # fmt: skip
BURN_N = 200_000
OUT = Path(__file__).resolve().parent / "results.json"


def _gen(generate, fuel, epoch):
    db = ReadDBHandle("knowledge-base", {"billing_question": ["Refunds take 3-5 days."]})
    return MeteredSandbox(
        "node_generate_response",
        {TOOL_LLM: {"generate": generate}, KB_READ: {"lookup": db.read}},
        StoreBudget(),
        fuel=fuel,
        epoch=epoch,
    )


def measure(rounds: int = 5, repeats: int = 400) -> dict:
    ctx = ConversationContext(intent=Intent.BILLING_QUESTION, question="Why?", knowledge=())
    context = record(intent=_from_intent(ctx.intent), question=ctx.question, knowledge=[])
    best: dict[str, dict[str, float]] = {k: {} for k in CONFIGS}
    for _ in range(rounds):
        for name, (fuel, epoch) in CONFIGS.items():
            tool = _gen(_generate_via_tool, fuel, epoch)
            direct = _gen(_generate_answering, fuel, epoch)
            t_tool = _time(lambda tool=tool: tool.call("run", context), repeats)
            t_direct = _time(lambda direct=direct: direct.call("run", context), repeats)
            crossing = max((t_tool - t_direct) / 2, 0.0)
            spin = MeteredSandbox("spin", {}, StoreBudget(), path=SPIKE_WASM / "spin.wasm",
                                  fuel=fuel, epoch=epoch)  # fmt: skip
            burn = _time(lambda spin=spin: spin.call("burn", BURN_N), 20)
            for key, v in (("crossing_ms", crossing), ("invocation_ms", t_direct),
                           ("burn_ms", burn)):  # fmt: skip
                best[name][key] = min(best[name].get(key, float("inf")), v)
    plain = best["plain"]
    for name in CONFIGS:
        best[name]["burn_vs_plain"] = best[name]["burn_ms"] / plain["burn_ms"]
        best[name]["invocation_vs_plain"] = best[name]["invocation_ms"] / plain["invocation_ms"]
    # Fuel spent per invocation of the real node (deterministic), and per burn round.
    sb = _gen(_generate_via_tool, True, False)
    inst = sb.fuel_spent()
    sb.call("run", context)
    spin = MeteredSandbox("spin", {}, StoreBudget(), path=SPIKE_WASM / "spin.wasm", epoch=False)
    s0 = spin.fuel_spent()
    spin.call("burn", BURN_N)
    return {
        "clock": "CPU time of the measuring thread; best of warmed rounds, interleaved",
        "machine": platform.platform(),
        "load_average_at_end": os.getloadavg(),
        "burn_n": BURN_N,
        "configs": best,
        "fuel": {
            "generate_response_instantiation": inst,
            "generate_response_tool_round_invocation": sb.fuel_spent() - inst,
            "burn_per_iteration": (spin.fuel_spent() - s0) / BURN_N,
        },
        "crossing_band_ms": [0.005, 0.100],
    }


def main() -> None:
    result = measure()
    OUT.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
