"""S1's checks. Run from the repo root:

    uv run --group poc pytest spikes/specified-architecture/s1 -q

Not collected by `make test` (testpaths is `tests/`), so no build step runs them.
"""

from __future__ import annotations

import pytest

from poc.handles import CapabilityError, InferenceLLM, ReadDBHandle, ToolLLM
from poc.llm import StubLLM
from poc.values import ConversationContext, Intent, RawMessage, Untrusted

from .budget import (
    BudgetError,
    BudgetExhausted,
    Meter,
    MeteredBackend,
    UsageStub,
    is_assignable,
    route,
    split,
)

wasmtime = pytest.importorskip("wasmtime")

from .metered_sandbox import (  # noqa: E402
    SPIKE_WASM,
    GuestTrapped,
    MeteredSandbox,
    StoreBudget,
    metered_tier,
)

SPIN = SPIKE_WASM / "spin.wasm"


# ── Narrowing ───────────────────────────────────────────────────────


def test_budget_is_a_trailing_scope_the_parser_already_accepts():
    base, budgets = split("LLMClient<inference, Calls<'5'>, Tokens<'4000'>>")
    assert str(base.head) == "LLMClient" and budgets == {"Calls": 5, "Tokens": 4000}


@pytest.mark.parametrize(
    "provided, expected, ok",
    [
        ("LLMClient<inference>", "LLMClient<inference, Calls<'5'>>", True),  # unbounded covers
        ("LLMClient<inference, Calls<'10'>>", "LLMClient<inference, Calls<'5'>>", True),
        ("LLMClient<inference, Calls<'5'>>", "LLMClient<inference, Calls<'10'>>", False),
        ("LLMClient<inference, Calls<'5'>>", "LLMClient<inference>", False),  # child unbounded
        ("LLMClient<[lookup], Calls<'5'>>", "LLMClient<inference, Calls<'5'>>", True),
        ("LLMClient<inference, Calls<'5'>>", "LLMClient<[lookup], Calls<'5'>>", False),  # base
        ("HTTPClient<['a.x', 'b.x'], Requests<'50'>>", "HTTPClient<['a.x'], Requests<'9'>>", True),
        (
            "StateHandle<'seen', read-write, Bytes<'1000'>>",
            "StateHandle<'seen', read, Bytes<'1000'>>",
            True,
        ),
    ],
)
def test_narrowing(provided, expected, ok):
    assert is_assignable(provided, expected) is ok


@pytest.mark.parametrize(
    "bad",
    [
        "LLMClient<inference, Calls<'0'>>",
        "LLMClient<inference, Calls<'-1'>>",
        "LLMClient<inference, Calls<'1.5'>>",
        "LLMClient<inference, Calls<'2'>, Calls<'3'>>",
        "LLMClient<Calls<'2'>, inference>",
    ],
)
def test_malformed_budgets_are_refused(bad):
    with pytest.raises(BudgetError):
        split(bad)


# ── Metering: narrowing is not enough ───────────────────────────────


def test_two_children_each_within_narrowing_cannot_spend_twice_the_parent():
    """Both children pass narrowing (5 ≤ 5), and the parent's total still holds,
    because both meters sit beneath the parent's."""
    parent_type = "LLMClient<inference, Calls<'5'>>"
    parent = Meter("parent", split(parent_type)[1])
    a = route(parent, parent_type, "LLMClient<inference, Calls<'5'>>", "a")
    b = route(parent, parent_type, "LLMClient<inference, Calls<'5'>>", "b")
    llm_a = InferenceLLM(MeteredBackend(StubLLM(), a))
    llm_b = InferenceLLM(MeteredBackend(StubLLM(), b))
    for _ in range(3):
        llm_a.infer(system="s", prompt="p", task="summarise")
    llm_b.infer(system="s", prompt="p", task="summarise")
    llm_b.infer(system="s", prompt="p", task="summarise")
    with pytest.raises(BudgetExhausted) as e:
        llm_b.infer(system="s", prompt="p", task="summarise")
    assert e.value.meter == "parent" and e.value.kind == "Calls"
    assert parent.spent["Calls"] == 5 and b.spent["Calls"] == 2  # the refusal charged nothing


def test_exhaustion_is_not_a_capability_error():
    m = Meter("n", {"Calls": 1})
    llm = InferenceLLM(MeteredBackend(StubLLM(), m))
    llm.infer(system="s", prompt="p", task="summarise")
    with pytest.raises(BudgetExhausted) as e:
        llm.infer(system="s", prompt="p", task="summarise")
    assert not isinstance(e.value, CapabilityError)


def test_tokens_are_recorded_after_the_call_and_overrun_by_at_most_one_call():
    m = Meter("n", {"Tokens": 25})
    backend = MeteredBackend(UsageStub(reply_words=10), m)
    llm = InferenceLLM(backend)
    for _ in range(3):  # 10, 20, 30: the third starts under budget and lands over
        llm.infer(system="s", prompt="p", task="summarise")
    assert m.spent["Tokens"] == 30 and backend.overruns == [5]
    with pytest.raises(BudgetExhausted):
        llm.infer(system="s", prompt="p", task="summarise")


def test_a_token_budget_over_a_backend_that_reports_none_is_refused():
    with pytest.raises(BudgetError, match="reports no token usage"):
        MeteredBackend(StubLLM(), Meter("n", {"Tokens": 100}))


def test_the_backend_meter_sees_the_confined_tiers_direct_backend_calls():
    """`generate_response_sandbox` calls `llm.backend.generate`, around the handle's
    methods. The meter is on the backend, so it still counts each call."""
    from poc.sandbox.nodes import generate_response_sandbox

    m = Meter("GenerateResponse", {"Calls": 1})
    llm = ToolLLM(MeteredBackend(StubLLM(), m), allowed_tools=frozenset({"lookup"}))
    db = ReadDBHandle("knowledge-base", {})
    ctx = ConversationContext(intent=Intent.BILLING_QUESTION, question="q?", knowledge=())
    # StubLLM asks for `lookup` once, then answers: two model calls, budget one.
    with pytest.raises(BudgetExhausted):
        generate_response_sandbox(ctx, llm, db)
    assert m.spent["Calls"] == 1


# ── The store: fuel, deadline, memory ───────────────────────────────


def _spin(budget: StoreBudget, **kw) -> MeteredSandbox:
    return MeteredSandbox("spin", {}, budget, path=SPIN, **kw)


def test_fuel_is_deterministic():
    spent = set()
    for _ in range(5):
        sb = _spin(StoreBudget())
        before = sb.fuel_spent()
        sb.call("burn", 1000)
        spent.add(sb.fuel_spent() - before)
    assert len(spent) == 1


def test_a_runaway_guest_is_stopped_by_fuel_and_classed_as_a_budget():
    sb = _spin(StoreBudget(fuel=1_000_000))
    with pytest.raises(BudgetExhausted) as e:
        sb.call("burn", 2**63)
    assert e.value.kind == "Fuel"
    assert not isinstance(e.value, (CapabilityError, GuestTrapped))


def test_a_runaway_guest_is_stopped_by_the_deadline():
    sb = _spin(StoreBudget(deadline_ms=20), fuel=False)
    with pytest.raises(BudgetExhausted) as e:
        sb.call("burn", 2**63)
    assert e.value.kind == "Deadline"


def test_memory_limit_holds_but_the_refusal_is_ambiguous():
    assert _spin(StoreBudget(memory_bytes=4 << 20)).call("hog", 1) == 1 << 20
    with pytest.raises(GuestTrapped):
        _spin(StoreBudget(memory_bytes=4 << 20)).call("hog", 16)


def test_fuel_too_small_to_instantiate_is_a_budget_not_an_ungranted_capability():
    with pytest.raises(BudgetExhausted):
        _spin(StoreBudget(fuel=10))


def test_an_ungranted_import_is_still_an_ungranted_import_on_the_metered_engine():
    """The classification is extended, not replaced."""
    from poc.sandbox.host import SandboxError

    with pytest.raises(SandboxError) as e:
        MeteredSandbox("hostile_ungranted", {}, StoreBudget(fuel=10**9))
    assert not isinstance(e.value, BudgetExhausted)
    # Named as the capability case, not a generic failure or a resource failure.
    assert "imports a capability it was not granted" in str(e.value)


def test_runtime_adapters_run_under_a_fuel_budget():
    from poc.sandbox.nodes import parse_message_sandbox

    raw = Untrusted(RawMessage(text="Why was I charged twice on invoice ABC123?"))
    with metered_tier(StoreBudget()) as built:
        parse_message_sandbox(raw, InferenceLLM(StubLLM()))
    need = built[0].fuel_spent()
    assert need and need > built[0].instantiation_fuel
    with metered_tier(StoreBudget(fuel=need)):
        parse_message_sandbox(raw, InferenceLLM(StubLLM()))
    with metered_tier(StoreBudget(fuel=need // 2)), pytest.raises(BudgetExhausted):
        parse_message_sandbox(raw, InferenceLLM(StubLLM()))


def test_fuel_overshoot_is_bounded_by_one_check_interval():
    """wasmtime checks fuel at loop headers and function entries, not per operator,
    so the last straight-line stretch runs unchecked: the least budget that lets a
    run finish is a little below what it spends. For `burn` the stretch is one loop
    iteration (23 units at the time of writing); the bound is that it stays small."""

    def ok(fuel: int) -> bool:
        try:
            _spin(StoreBudget(fuel=fuel)).call("burn", 1000)
            return True
        except BudgetExhausted:
            return False

    sb = _spin(StoreBudget())
    sb.call("burn", 1000)
    spent = sb.fuel_spent()
    assert spent is not None
    lo, hi = 0, spent
    while lo + 1 < hi:
        mid = (lo + hi) // 2
        lo, hi = (lo, mid) if ok(mid) else (mid, hi)
    assert 0 < spent - hi <= 64
