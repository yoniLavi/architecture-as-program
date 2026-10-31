"""Paper 4's architect and its reviewers (`openspec/changes/add-architect-and-reviewers`).

A Product Owner's prompt goes to an **architect** model, which writes a signal graph over
the banking node library (`poc/agentdojo/library.py`) in two stages: an abstract graph
from the prompt alone, then a mapping onto the library, every grant citing the prompt.
The graph then meets a **formal review** (the validator, the link check, the
least-authority check) and an **independent reviewer** model, before anything runs.

The architect never sees tool output, an injection, or a reviewer's verdict: its inputs
are the prompt, the catalogue (stage two only) and verdicts its own output earned.

Stdlib-only except where a module says otherwise; no test or build step calls a model.
"""
