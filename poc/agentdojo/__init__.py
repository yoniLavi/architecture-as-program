"""Paper 4's AgentDojo banking harness.

Signal graphs run inside AgentDojo's own scorer, at the pinned commit in
`pyproject.toml`'s `agentdojo` group. Only the modules that need AgentDojo import
it (`adapter`, `pipeline`, `baseline`); the rest — the corpus, the node library,
the predictions — are stdlib-only, so their tests run without that group. Nothing
here is reachable from `scripts/` or from the evaluation Paper 2 typesets
(`tests/test_agentdojo_isolation.py`).
"""
