"""The least-authority labels (D6): per banking task, the widest grant the prompt alone
justifies. The principle, the per-grant reasons and the open questions are in
`labels/banking.json`; the author approves them before any measured run (task 2.2a),
and they cannot be corrected after it, only disclosed."""

from __future__ import annotations

import json
from pathlib import Path

LABELS_PATH = Path(__file__).resolve().parent / "labels" / "banking.json"


def load(path: Path = LABELS_PATH) -> dict:
    return json.loads(path.read_text())


def approved(data: dict | None = None) -> bool:
    return (data or load())["status"].startswith("APPROVED")


def label(task: str, data: dict | None = None) -> list[str]:
    """The grants within which `task`'s graph is no widening: its own, and the uniform
    ones every task may hold."""
    data = data or load()
    return [*data["tasks"][task]["grants"], *data["uniform"]]
