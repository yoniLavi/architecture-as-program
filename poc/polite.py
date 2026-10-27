"""Run at the lowest priority the machine offers.

The machine these long runs happen on is shared with its owner's other work, and
a generation run, a feed recorder or a replay must not make that work slower. So
each of them calls `lower_priority()` once, on start, and everything it spawns
afterwards — `claude -p`, `cargo`, `wasm-tools`, the check process — inherits the
setting. Lowering it in the parent is what makes it impossible to forget on any
one command line.

Two settings, because one is not enough on macOS:

* `nice 19`, the lowest CPU priority, everywhere;
* on macOS, `PRIO_DARWIN_BG` (`taskpolicy -b -p <pid>`), which also throttles the
  process's disk and network I/O. A cargo build is I/O-bound as often as not, and
  CPU priority alone does nothing for that.

Both are inherited across `fork`. That was checked on the machine rather than
assumed (27 October 2026): after setting both on a running Python process, a
child and a grandchild it spawned ran at nice 19 and scheduling priority 4, the
background band, against 31 for a sibling started normally.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys

LOWEST_NICE = 19


def lower_priority(enabled: bool = True) -> dict[str, object]:
    """Lower this process's priority, and so its future children's.

    Returns what was applied, for the caller's run record: a timing taken at low
    priority must say so. `enabled=False` (a `--no-nice` flag, for an idle
    machine) changes nothing and reports the priority as it is."""
    if not enabled:
        return {"nice": os.nice(0), "background": False, "lowered": False}
    current = os.nice(0)
    if current < LOWEST_NICE:
        os.nice(LOWEST_NICE - current)
    background = False
    if sys.platform == "darwin" and shutil.which("taskpolicy"):
        done = subprocess.run(
            ["taskpolicy", "-b", "-p", str(os.getpid())],
            capture_output=True,
            check=False,
        )
        background = done.returncode == 0
    return {"nice": os.nice(0), "background": background, "lowered": True}
