"""The minimal contract language: parsing, blame, and where each check lands.

The vocabulary is deliberately closed (comparisons, variant membership, presence,
`len`), because that ceiling is what keeps a contract checkable without a solver
and lets a precondition later be derived into a property-based-test strategy. The
tests below pin the ceiling as much as the behaviour: a predicate outside the
vocabulary must be *rejected*, not silently accepted and evaluated as false.
"""

from __future__ import annotations

import copy

import pytest

from poc.contracts import (
    BLAME_CALLER,
    BLAME_IMPLEMENTATION,
    ContractError,
    ContractViolation,
    check,
    parse,
    parse_all,
)
from poc.demo import BENIGN, STORES
from poc.graph import AssemblyError, assemble, load_graph_dict
from poc.llm import StubLLM
from poc.runtime import execute
from poc.values import CustomerRequest

# ── The vocabulary, and its ceiling ──────────────────────────────────────────


class _Box:
    def __init__(self, **kw):
        self.__dict__.update(kw)


def test_the_four_permitted_forms_parse_and_evaluate():
    value = _Box(text="hello", intent="billing_question", count=3)
    assert parse("text == 'hello'").holds(value)
    assert parse("count >= 3").holds(value)
    assert parse("intent in ['billing_question', 'refund']").holds(value)
    assert parse("present(text)").holds(value)
    assert parse("len(text) > 0").holds(value)


def test_a_predicate_outside_the_vocabulary_is_rejected():
    """The ceiling is the design: an unsupported form must fail loudly at parse
    time rather than quietly evaluating to false at run time."""
    for bad in ("forall x. x > 0", "text.upper() == 'HI'", "count + 1 == 4", ""):
        with pytest.raises(ContractError):
            parse(bad)


def test_a_missing_field_is_false_not_an_error_once_parsed():
    """Distinct from the above: a *well-formed* predicate over a field the value
    lacks is simply unsatisfied. Only unparseable text is an error."""
    assert not parse("nope == 'x'").holds(_Box(text="hi"))
    assert not parse("present(nope)").holds(_Box(text="hi"))


# ── Blame ────────────────────────────────────────────────────────────────────


def test_blame_distinguishes_the_caller_from_the_implementation():
    """Racket's contribution, and the point of the whole layer: a precondition
    failure indicts whatever supplied the input; a postcondition failure indicts
    the body."""
    preds = parse_all(["len(text) > 0"], what="requires")
    with pytest.raises(ContractViolation) as caller:
        check(preds, _Box(text=""), node="N", kind="requires")
    assert caller.value.blame == BLAME_CALLER

    with pytest.raises(ContractViolation) as impl:
        check(preds, _Box(text=""), node="N", kind="ensures")
    assert impl.value.blame == BLAME_IMPLEMENTATION
    assert "N" in str(impl.value) and "len(text) > 0" in str(impl.value)


# ── Where each failure lands ─────────────────────────────────────────────────


def _graph_with(node_name: str, **contract):
    g = copy.deepcopy(load_graph_dict("customer-support"))
    for n in g["nodes"]:
        if n["name"] == node_name:
            n.update(contract)
    return g


def _run(graph):
    g = assemble(graph, backend=StubLLM(), stores=STORES)
    return execute(g, CustomerRequest(session_id="user-session", body=BENIGN))


def test_a_satisfied_contract_does_not_disturb_the_run():
    result = _run(_graph_with("ParseMessage", ensures=["present(intent)"]))
    assert result.terminals


def test_a_violated_precondition_fails_the_run_blaming_the_wiring():
    graph = _graph_with("ParseMessage", requires=["len(nonexistent) > 5"])
    with pytest.raises(ContractViolation) as excinfo:
        _run(graph)
    assert excinfo.value.blame == BLAME_CALLER
    assert excinfo.value.node == "ParseMessage"


def test_a_violated_postcondition_fails_the_run_blaming_the_body():
    graph = _graph_with("ParseMessage", ensures=["intent == 'this_is_never_emitted'"])
    with pytest.raises(ContractViolation) as excinfo:
        _run(graph)
    assert excinfo.value.blame == BLAME_IMPLEMENTATION
    assert excinfo.value.node == "ParseMessage"


def test_a_malformed_contract_is_rejected_at_assembly_not_mid_run():
    """An unevaluatable contract is a mistake in the graph, so it fails the same
    gate an unsafe wiring does rather than surfacing part-way through a run."""
    graph = _graph_with("ParseMessage", requires=["forall x. x > 0"])
    with pytest.raises(AssemblyError) as excinfo:
        assemble(graph, backend=StubLLM(), stores=STORES)
    assert "vocabulary" in str(excinfo.value)


def test_graphs_without_contracts_are_untouched():
    """The feature is opt-in: the canonical graphs declare no contracts and run
    exactly as before."""
    result = _run(load_graph_dict("customer-support"))
    assert result.terminals
