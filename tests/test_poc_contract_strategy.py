"""The generative contract mode: a precondition read as a source of test inputs.

`contracts.strategy` is the second use of a contract. The closed vocabulary was
kept closed so that each predicate names its own boundary, and these tests check
that each of the four forms actually yields it — and that nothing violating the
precondition survives.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from poc.contracts import ContractError, parse_all, strategy
from poc.values import ConversationContext, CustomerQuery, Intent, RawMessage, Untrusted


def _gen(shape, *requires: str, **kw):
    return strategy(parse_all(list(requires), what="requires"), shape, **kw)


@dataclass(frozen=True)
class Order:
    quantity: int
    note: str
    rush: bool
    tags: tuple[str, ...]


def test_a_length_bound_yields_lengths_at_and_below_it_and_discards_above():
    lengths = {len(o.note) for o in _gen(Order, "len(note) <= 5", count=0)}
    assert lengths == {4, 5}  # 6 is generated, violates the precondition, and is discarded


def test_a_lower_length_bound_yields_the_bound_and_one_above():
    lengths = {len(o.tags) for o in _gen(Order, "len(tags) >= 2", count=0)}
    assert lengths == {2, 3}


def test_an_integer_comparison_yields_both_sides_of_its_literal():
    assert {o.quantity for o in _gen(Order, "quantity > 0", count=0)} == {1}
    assert {o.quantity for o in _gen(Order, "quantity >= 10", count=0)} == {10, 11}
    assert {o.quantity for o in _gen(Order, "quantity != 3", count=0)} == {2, 4}


def test_a_boolean_comparison_yields_the_side_that_holds():
    assert {o.rush for o in _gen(Order, "rush == true", count=0)} == {True}


def test_membership_yields_each_literal_and_nothing_outside_the_set():
    notes = {o.note for o in _gen(Order, "note in ['a', 'b', 'c']", count=0)}
    assert notes == {"a", "b", "c"}


def test_membership_over_an_enum_field_yields_each_named_member():
    queries = _gen(CustomerQuery, "intent in ['billing_question', 'unknown']", count=0)
    assert {q.intent for q in queries} == {Intent.BILLING_QUESTION, Intent.UNKNOWN}


def test_presence_keeps_the_field_present():
    assert all(hasattr(o, "note") for o in _gen(Order, "present(note)", count=4))


def test_every_generated_input_satisfies_every_precondition():
    requires = ("len(question) <= 512", "len(question) > 0", "intent != 'unknown'")
    inputs = _gen(ConversationContext, *requires, count=200)
    assert len(inputs) > 5
    predicates = parse_all(list(requires), what="requires")
    assert all(p.holds(i) for i in inputs for p in predicates)
    assert 512 in {len(i.question) for i in inputs}  # the boundary itself is among them


def test_a_nested_path_is_followed_through_a_generic_wrapper():
    inputs = _gen(Untrusted[RawMessage], "len(value.text) <= 3", count=0)
    assert {len(i.value.text) for i in inputs} == {2, 3}
    assert all(isinstance(i, Untrusted) and isinstance(i.value, RawMessage) for i in inputs)


def test_the_arbitrary_inputs_include_text_a_tidy_body_would_not_expect():
    texts = {i.value.text for i in _gen(Untrusted[RawMessage], count=300)}
    assert "" in texts and any("Ignore previous instructions" in t for t in texts)
    assert any(not t.isascii() for t in texts) and any(len(t) > 512 for t in texts)


def test_generation_is_deterministic_for_a_seed_and_varies_across_seeds():
    assert _gen(Order, "quantity > 0", seed=7) == _gen(Order, "quantity > 0", seed=7)
    assert _gen(Order, seed=1, count=40) != _gen(Order, seed=2, count=40)


def test_a_field_with_a_default_is_left_at_its_default():
    assert {q.MAX_QUESTION_LEN for q in _gen(CustomerQuery, count=30)} == {512}


def test_a_type_with_no_generator_is_an_error_not_a_guess():
    @dataclass(frozen=True)
    class Odd:
        blob: bytes

    with pytest.raises(ContractError, match="no generator"):
        _gen(Odd)
