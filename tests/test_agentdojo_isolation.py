"""AgentDojo stays in its own dependency group, out of reach of Paper 2 and `scripts/`.

AgentDojo (pinned in `pyproject.toml`'s `agentdojo` group) pulls in a large tree of
model SDKs. The banking harness in `poc/agentdojo/` needs it; nothing else may. Two
layers must never reach it:

* `scripts/`, which is stdlib-only so the pre-commit hook stays portable;
* `poc/evaluate.py` and everything it imports, because Paper 2 typesets from it.

Checked twice: dynamically (importing them pulls no `agentdojo` module) and
statically (no module they load mentions an `agentdojo` import, which catches a
lazy import inside a function that the dynamic check cannot see).
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"

_IMPORT = re.compile(r"^\s*(?:import|from)\s+agentdojo\b", re.MULTILINE)

# Imports every `scripts/*.py` as a module (hyphenated names by path) and
# `poc.evaluate`, then reports which modules were loaded and whether AgentDojo was.
_PROBE = r"""
import importlib, importlib.util, json, sys
from pathlib import Path
root = Path(sys.argv[1])
sys.path[:0] = [str(root / "scripts"), str(root)]
for path in sorted((root / "scripts").glob("*.py")):
    name = "_probe_" + path.stem.replace("-", "_")
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
importlib.import_module("poc.evaluate")
files = sorted(
    getattr(m, "__file__", None) or "" for m in list(sys.modules.values())
)
print(json.dumps({
    "agentdojo": any(k == "agentdojo" or k.startswith("agentdojo.") for k in sys.modules),
    "files": [f for f in files if f.startswith(str(root)) and "/.venv/" not in f],
}))
"""


def _probe() -> dict:
    out = subprocess.run(
        [sys.executable, "-c", _PROBE, str(ROOT)],
        capture_output=True,
        text=True,
        check=True,
        cwd=ROOT,
    )
    return json.loads(out.stdout.strip().splitlines()[-1])


def test_scripts_and_paper2_evaluation_do_not_load_agentdojo() -> None:
    assert _probe()["agentdojo"] is False


def test_no_reachable_module_mentions_an_agentdojo_import() -> None:
    loaded = {Path(f) for f in _probe()["files"]}
    # Every scripts/ file, imported or not, and every repo module the evaluation loads.
    checked = loaded | set(SCRIPTS.glob("*.py"))
    assert any(p.name == "evaluate.py" for p in checked)
    offenders = [str(p.relative_to(ROOT)) for p in checked if _IMPORT.search(p.read_text())]
    assert offenders == []
