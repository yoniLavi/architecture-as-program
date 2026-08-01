"""The evaluation harness and — the point of it — its pins.

The harness's job is not to *report* the demonstrator's evidence but to *guard*
it. A report that renders green whatever the code does would let the central
security claim rot silently, so the tests that matter most here are the ones that
prove the guard fires: a wrong expected verdict, a rejection caught by the wrong
reason class, and an unpinned mutation must each fail the evaluation.

The corpus half needs no toolchain (the validator is stdlib-only), so it runs on
every `pytest`. The artifact half needs wasmtime for the overhead and sandbox-tier
sections and skips without it.

Covers the `evaluation` spec requirements added by `add-evaluation-harness`:
  - The demonstrator ships a reproducible evaluation artifact
  - The evaluation pins expected verdicts as a regression guard
"""

from __future__ import annotations

import json
from dataclasses import replace

import pytest

from poc.demo import SANDBOXED_NODES
from poc.evaluate import (
    ACCEPTED,
    CORPUS,
    DERIVED_NODES,
    REASON_EDGE_TYPE,
    REASON_TRUST_LATTICE,
    REJECTED,
    Derivation,
    EvaluationError,
    check,
    check_derivations,
    check_traces,
    derive_and_compare,
    generate,
    main,
    render,
    run,
    run_corpus,
    run_injection,
    serialise,
)
from poc.sandbox import TYPES, available
from poc.trace import validate_document
from poc.variants import UNSAFE_VARIANTS


def _corpus_with(name: str, **changes):
    """The real corpus with one case's pin altered."""
    return tuple(replace(c, **changes) if c.name == name else c for c in CORPUS)


# ── The evaluation, as pinned ────────────────────────────────────────


def test_pinned_corpus_verdicts_hold():
    """The headline: every case does what it is pinned to do."""
    assert check(run_corpus()) == []


def test_the_canonical_graphs_are_accepted():
    """Half the corpus exists to keep the other half honest: a validator that
    rejected everything would catch both mutations and be worthless."""
    canonical = [o for o in run_corpus() if o.case.kind == "canonical"]
    assert canonical, "the corpus must contain the safe wirings, not only the unsafe ones"
    assert all(o.actual == ACCEPTED for o in canonical)


def test_each_mutation_is_rejected_by_its_pinned_reason():
    outcomes = {o.case.name: o for o in run_corpus() if o.case.kind == "mutation"}
    assert outcomes["bypass_pipeline"].actual == REJECTED
    assert outcomes["bypass_pipeline"].reason == REASON_EDGE_TYPE
    assert outcomes["launder_trust"].actual == REJECTED
    assert outcomes["launder_trust"].reason == REASON_TRUST_LATTICE


# ── The guard actually guards ────────────────────────────────────────


def test_a_wrong_expected_verdict_fails_the_evaluation():
    """If the pin says an unsafe wiring should assemble, the harness must object —
    otherwise it is not checking anything."""
    corrupted = _corpus_with("bypass_pipeline", expected=ACCEPTED, reason=None)
    problems = check(run_corpus(corrupted))
    assert problems, "a wrong expected verdict must be reported"
    assert "bypass_pipeline" in problems[0]


def test_a_wrong_reason_class_fails_the_evaluation():
    """The subtler guard. `launder_trust` is still *rejected* here, so a pass/fail
    pin would stay green — but it is rejected as a trust-lattice violation, and
    pinning it to a type mismatch must fail. This is what keeps the trust-lattice
    claim tested rather than merely true by coincidence."""
    corrupted = _corpus_with("launder_trust", reason=REASON_EDGE_TYPE)
    problems = check(run_corpus(corrupted))
    assert problems, "a rejection for the wrong reason must be reported"
    assert "caught by" in problems[0]


def test_an_unpinned_mutation_fails_the_evaluation():
    """A mutation added to the corpus without an expected verdict would otherwise be
    silently absent from the table while the counts still read as complete."""
    without = tuple(c for c in CORPUS if c.name != "launder_trust")
    with pytest.raises(EvaluationError, match="disagree"):
        run_corpus(without)


def test_the_pinned_mutations_are_exactly_the_defined_ones():
    pinned = {c.name for c in CORPUS if c.kind == "mutation"}
    assert pinned == set(UNSAFE_VARIANTS)


def test_generate_refuses_to_render_a_diverged_evaluation():
    """The artifact must not be rewritten to match a regression."""
    corrupted = _corpus_with("launder_trust", expected=ACCEPTED, reason=None)
    with pytest.raises(EvaluationError, match="diverged"):
        generate(corrupted)


# ── The artifact ─────────────────────────────────────────────────────

sandboxed = pytest.mark.skipif(
    not available(),
    reason="component tier unavailable: wasmtime not installed (`uv sync --group poc`)",
)


@sandboxed
def test_the_artifact_reports_every_evaluation_dimension():
    artifact = generate()
    assert "## 1. Graph-mutation corpus" in artifact
    assert "## 2. Capability-boundary overhead" in artifact
    assert "## 3. Prompt-injection attenuation" in artifact
    assert "## 4. Enforcement tiers: host vs sandbox" in artifact
    assert "## 5. The graph-to-binary derivation" in artifact
    # The corpus verdicts, the overhead figure, and both tiers are present.
    assert "marginal per-crossing" in artifact
    assert "µs" in artifact
    assert "ESCAPES" in artifact and "denied" in artifact


@sandboxed
def test_the_artifact_does_not_overclaim():
    """The honesty clauses are load-bearing: a fully-caught curated corpus reads as
    a soundness proof unless it says otherwise, and the host tier's escapes must be
    reported as the gap they are."""
    artifact = generate()
    assert "curated" in artifact and "illustrative" in artifact
    assert "not** a soundness result" in artifact
    assert "attenuation, not" in artifact
    # The host tier's escapes are disclosed, not hidden.
    assert "expected to read ESCAPES" in artifact
    # Enforcement fidelity is bounded at the WASM boundary, not memory.
    assert "CHERI" in artifact


@sandboxed
def test_main_writes_both_artifacts(tmp_path, monkeypatch, capsys):
    import poc.evaluate as evaluate

    out = tmp_path / "evaluation.md"
    data = tmp_path / "evaluation.json"
    monkeypatch.setattr(evaluate, "ARTIFACT_PATH", out)
    monkeypatch.setattr(evaluate, "DATA_PATH", data)
    monkeypatch.setattr(evaluate, "TRACE_HOST_PATH", tmp_path / "trace-injection-host.json")
    monkeypatch.setattr(evaluate, "TRACE_CONFINED_PATH", tmp_path / "trace-injection-confined.json")
    monkeypatch.setattr(evaluate, "REPO_ROOT", tmp_path)

    assert evaluate.main() == 0
    assert "Demonstrator evaluation" in out.read_text()
    json.loads(data.read_text())
    assert "Wrote" in capsys.readouterr().out


# ── The data the paper reads ─────────────────────────────────────────
#
# Paper 2's Evaluation section typesets its tables from `dist/evaluation.json`
# rather than restating the run's figures by hand. That only holds if the JSON
# actually carries every figure the section needs, so the keys are asserted here:
# a rename that silently emptied a paper table would otherwise still build.


@sandboxed
def test_the_data_carries_every_figure_the_paper_states():
    payload = json.loads(serialise(run()))

    assert set(payload) == {
        "environment",
        "corpus",
        "overhead",
        "injection",
        "tiers",
        "derivation",
        "trace",
        "display",
    }

    # The paper prints `display` verbatim rather than rounding numbers itself, so
    # these must be strings: typst and pandoc's typst reader format the same float
    # differently (0.04 vs 4.0e-2), and the PDF and HTML would disagree.
    assert all(isinstance(v, str) for v in payload["display"].values())
    assert payload["display"]["crossing_us"] == f"{payload['overhead']['crossing_us']:.1f}"
    assert payload["display"]["mutations_caught_pct"] == "100%"

    corpus = payload["corpus"]
    assert {c["name"] for c in corpus["cases"]} == {c.name for c in CORPUS}
    assert corpus["canonical_accepted"] == corpus["canonical_total"]
    assert corpus["mutation_rejected"] == corpus["mutation_total"]
    assert all(c["ok"] for c in corpus["cases"])

    overhead = payload["overhead"]
    for key in ("crossing_us", "instantiation_ms", "compilation_ms", "projected_overhead"):
        assert isinstance(overhead[key], float)
    assert overhead["within_envelope"] is True

    injection = payload["injection"]
    assert injection["received_type"] == "ConversationContext"
    assert injection["is_untrusted"] is False
    assert injection["out_of_scope_call_refused"] is True
    # The residual is carried in the data too, not softened out of the paper's reach.
    assert injection["adversarial_text_present"] is True

    tiers = payload["tiers"]
    assert all(e["host_escapes"] for e in tiers["escapes"])
    assert not any(e["sandbox_escapes"] for e in tiers["escapes"])
    assert tiers["ambient_imports"] == 0

    trace = payload["trace"]
    # Trust is raised only at the declared discharge node, on both tiers.
    assert trace["trust_raisers_host"] == [trace["discharge_node"]] == ["ParseMessage"]
    assert trace["trust_raisers_confined"] == ["ParseMessage"]
    # The residual, in data: the confined tool-capable node received a trusted-
    # labelled value that still carries adversarial text.
    assert trace["tool_capable_node"] == "GenerateResponse"
    assert trace["tool_capable_tier"] == "sandbox"
    assert trace["tool_capable_input_trust"] == "trusted"
    assert trace["residual_reaches_tool_node"] is True
    # Both tiers record the same crossings for the same graph.
    assert trace["crossings_identical_across_tiers"] is True


@sandboxed
def test_both_artifacts_come_from_one_run():
    """The markdown artifact and the paper's data must not be able to disagree.

    They are rendered from a single `Evaluation`, so the check that matters is
    that neither is re-measured: the crossing figure the paper typesets is the
    same one the artifact prints."""
    ev = run()
    artifact = render(ev.outcomes, ev.bench, ev.injection, ev.escapes, ev.derivations)
    payload = json.loads(serialise(ev))

    assert f"{payload['overhead']['crossing_us']:.1f} µs" in artifact


# ── The injection traces and their pins ──────────────────────────────


@sandboxed
def test_the_canonical_injection_traces_hold_their_pins():
    """Both tiers' traces are schema-valid and satisfy their structural pins: trust
    raised only at the discharge node, and the residual reaching the confined
    tool-capable node through a permitted field."""
    host = run_injection(set())
    confined = run_injection(set(SANDBOXED_NODES))
    assert check_traces(host, confined) == []
    assert validate_document(host.trace.to_dict()) == []
    assert validate_document(confined.trace.to_dict()) == []


@sandboxed
def test_the_trace_guard_fires_if_the_residual_vanishes():
    """The pin that keeps stronger enforcement from being misread as a stronger
    claim. If adversarial text stopped reaching the confined tool-capable node
    through the permitted field, the build must fail rather than quietly re-pin."""
    host = run_injection(set())
    confined = run_injection(set(SANDBOXED_NODES))
    softened = replace(confined, adversarial_text_present=False)
    problems = check_traces(host, softened)
    assert any("residual" in p for p in problems)


@sandboxed
def test_main_writes_the_injection_traces(tmp_path, monkeypatch):
    import poc.evaluate as evaluate

    monkeypatch.setattr(evaluate, "ARTIFACT_PATH", tmp_path / "evaluation.md")
    monkeypatch.setattr(evaluate, "DATA_PATH", tmp_path / "evaluation.json")
    host = tmp_path / "trace-injection-host.json"
    confined = tmp_path / "trace-injection-confined.json"
    monkeypatch.setattr(evaluate, "TRACE_HOST_PATH", host)
    monkeypatch.setattr(evaluate, "TRACE_CONFINED_PATH", confined)
    monkeypatch.setattr(evaluate, "REPO_ROOT", tmp_path)

    assert evaluate.main() == 0
    for path in (host, confined):
        assert validate_document(json.loads(path.read_text())) == []


# ── The graph-to-binary derivation: the lead claim as a reported figure ──
#
# The comparison itself is asserted in tests/test_poc_sandbox.py. What is pinned
# here is that it is *reported*: the paper's central claim had evidence only in a
# test suite, which is invisible to a reader, and the Evaluation section measured
# four things of which none was the lead.


@sandboxed
def test_the_derivation_covers_every_ported_node():
    """Scenario: the derivation is reported per node.

    Every node the injection scenario runs confined must appear, or the figure
    would report a subset of the tier while reading as a property of it."""
    derivations = derive_and_compare()
    assert {d.node for d in derivations} == set(SANDBOXED_NODES)
    assert {d.node for d, _ in ((d, None) for d in derivations)} == {
        node for node, _ in DERIVED_NODES
    }
    assert all(d.agrees for d in derivations)


@sandboxed
def test_the_granted_count_excludes_the_shared_type_vocabulary():
    """`aap:caps/types` is linked by every component and grants no authority, so
    counting it as a capability would inflate the paper's table by one per row —
    and would make an inference-only node look as though it holds two."""
    parse = next(d for d in derive_and_compare() if d.node == "ParseMessage")
    assert parse.granted == ["aap:caps/inference-llm@0.1.0"]
    assert TYPES in parse.derived and TYPES not in parse.granted
    # It is excluded from the count, not from the comparison.
    assert TYPES in parse.actual


def test_an_over_granting_world_fails_the_evaluation():
    """Scenario: an over-granting world fails the build.

    This is the claim, so the guard is what makes the figure worth reporting: a
    component importing an interface its `with` clause never granted must stop the
    build, not render a row reading "no"."""
    over = Derivation(
        node="ParseMessage",
        component="node_parse_message",
        derived=["aap:caps/inference-llm@0.1.0"],
        actual=["aap:caps/inference-llm@0.1.0", "aap:caps/tool-llm@0.1.0"],
    )
    problems = check_derivations([over])
    assert problems and "tool-llm" in problems[0] and "over-granting" in problems[0]


def test_a_derivation_running_ahead_of_the_artifact_also_fails():
    """The dual direction, and it is not symmetric in meaning: a grant the binary
    does not import means the mapping has drifted ahead of the component, so the
    comparison would be vacuously passing on a stale artifact."""
    stale = Derivation(
        node="FetchContext",
        component="node_fetch_context",
        derived=["aap:caps/kb-read@0.1.0"],
        actual=[],
    )
    problems = check_derivations([stale])
    assert problems and "drifted" in problems[0]


def test_an_empty_derivation_fails_rather_than_reporting_nothing():
    """A silently empty comparison is the failure mode that would leave the lead
    claim with no evidence while the build stayed green."""
    assert check_derivations([])


@sandboxed
def test_the_data_carries_the_derivation_figures():
    payload = json.loads(serialise(run()))["derivation"]
    assert payload["total"] == payload["agreeing"] == len(SANDBOXED_NODES)
    assert payload["grants_compared"] == sum(n["granted_count"] for n in payload["nodes"])
    # GenerateResponse is the interesting row: the only ported node holding two
    # capabilities, and the tool-capable one.
    generate_row = next(n for n in payload["nodes"] if n["node"] == "GenerateResponse")
    assert generate_row["granted_count"] == 2
    assert "aap:caps/tool-llm@0.1.0" in generate_row["granted"]


def test_main_is_importable_without_running():
    assert callable(main)
