"""The validator in the architect's loop: a graph → structured reasons (task 1.3).

Each of the validator's errors is placed in a reason class by the signatures the
evaluation harness and the banking corpus already pin (`poc/evaluate.py`,
`poc/agentdojo/corpus.py`), so the classes the architect is told are the classes the
papers report, and there is one classifier, not two. An error no signature places is
`validator` (other). The library's own check (`library.check_graph`) follows, as in
the pipeline, as class `library`.

A detail is the checker's message about the architect's own graph, with the
validator's temporary file name taken off. Nothing else reaches the architect: no
tool output, no injection, no reviewer verdict.
"""

from __future__ import annotations

import re

from ..agentdojo import corpus
from ..agentdojo.library import check_graph
from ..evaluate import REASON_SIGNATURES as PAPER2_SIGNATURES
from ..graph import validate_graph_dicts
from .abstract import Reason

VALIDATOR_OTHER = "validator"
LIBRARY = "library"
SIGNATURES: dict[str, tuple[str, ...]] = {**PAPER2_SIGNATURES, **corpus.REASON_SIGNATURES}
STAGE_TWO_CLASSES = (*SIGNATURES, VALIDATOR_OTHER, LIBRARY)

_PREFIX = re.compile(r"^\d\d-[^:]*\.json: ")


def classify(message: str) -> str:
    for cls, phrases in SIGNATURES.items():
        if any(p in message for p in phrases):
            return cls
    return VALIDATOR_OTHER


def check(graph: dict) -> list[Reason]:
    """Every reason `graph` is not a valid library graph; empty if it is."""
    reasons = [Reason(classify(m), _PREFIX.sub("", m)) for m in validate_graph_dicts([graph])]
    try:
        library = check_graph(graph)
    except (KeyError, TypeError, AttributeError, ValueError):
        # A graph malformed enough to break the library's bookkeeping has already
        # earned the validator's reasons for it.
        library = [] if reasons else ["the graph's nodes are malformed"]
    return reasons + [Reason(LIBRARY, m) for m in library]
