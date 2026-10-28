"""The differential step: green bodies against the hand-written ones.

The stand-in must not read the prompt; the comparison must find a difference
when there is one and none when there is not; harness faults must not be
mistaken for a body's behaviour. The self-control and the negative control run
real components and need the `poc` group (and, for the negative control, a Rust
toolchain).
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass

import pytest

from poc.feed_values import Category, Importance
from poc.generation import differential, harness, report
from poc.generation.subjects import BY_NODE, SUBJECTS
from poc.handles import InferenceLLM, Notifier, ToolLLM
from poc.llm import LLMRequest
from poc.values import Intent

try:
    from poc.sandbox.host import available
except ImportError:  # pragma: no cover - the poc group is absent

    def available() -> bool:
        return False


# ── The stand-in ─────────────────────────────────────────────────────


def _ask(llm, task, prompt="anything", tools=()):
    return llm.generate(LLMRequest(system="s", prompt=prompt, offered_tools=tools, task=task))


@pytest.mark.parametrize("task", ["classify", "moderate", "triage", "summarise", "digest", "x"])
def test_the_stand_in_never_reads_the_prompt(task):
    a = _ask(differential.KeyedLLM("k1"), task, "Please classify: a refund for my invoice")
    b = _ask(differential.KeyedLLM("k1"), task, "an entirely different wording, self-harm, CVE-1")
    assert a == b


def test_the_reply_depends_on_the_input_and_the_task_label():
    replies = {_ask(differential.KeyedLLM(f"key-{i}"), "summarise").text for i in range(10)}
    assert len(replies) == 10
    assert _ask(differential.KeyedLLM("k"), "summarise") != _ask(
        differential.KeyedLLM("k"), "digest"
    )


def test_replies_for_known_labels_are_from_the_closed_sets_a_body_parses():
    for i in range(50):
        key = f"key-{i}"
        assert _ask(differential.KeyedLLM(key), "classify").text in {x.value for x in Intent}
        assert _ask(differential.KeyedLLM(key), "moderate").text in {"ok", "violation"}
        category, importance = _ask(differential.KeyedLLM(key), "triage").text.split()
        assert category in {c.value for c in Category}
        assert importance in {x.value for x in Importance}


def test_a_tool_capable_client_is_asked_for_a_tool_once_then_answered():
    llm = differential.KeyedLLM("k")
    first = _ask(llm, "respond", tools=("lookup",))
    second = _ask(llm, "respond", tools=("lookup",))
    assert first.tool_calls and first.tool_calls[0].name == "lookup"
    assert not second.tool_calls and second.text
    assert llm.calls == ["respond", "respond"]


def test_only_model_clients_are_replaced():
    notifier = Notifier("digest")
    handles = (InferenceLLM(object()), ToolLLM(object(), frozenset({"lookup"})), notifier)  # type: ignore[arg-type]
    keyed = differential.keyed_handles(handles, "input")
    assert isinstance(keyed[0].backend, differential.KeyedLLM)
    assert isinstance(keyed[1].backend, differential.KeyedLLM)
    assert keyed[1].allowed_tools == frozenset({"lookup"})
    assert keyed[2] is notifier


# ── The comparison, on Python stand-ins for two bodies ───────────────


@dataclass
class _Subject:
    """Enough of a `Subject` for `compare`: inputs, fresh handles, arity."""

    values: tuple = (1, 2, 3)
    arity: int = 1

    def test_inputs(self):
        return list(self.values)

    def handles(self):
        return (Notifier("digest"),)


def _body(transform, *, notify=True):
    def call(value, notifier):
        if notify:
            notifier.notify(str(transform(value)))
        return transform(value)

    return call


def test_equal_bodies_are_equal_on_every_input():
    c = differential.compare(_Subject(), _body(lambda v: v * 2), _body(lambda v: v + v))
    assert c.to_dict() == {
        "inputs": 3,
        "equal_on": 3,
        "equal": True,
        "labels_differ": False,
        "first_difference": None,
    }


def test_a_different_task_label_is_flagged_apart():
    """Two bodies asking the model under different labels: the task never says
    which label to use, so the report counts this kind of difference apart."""

    @dataclass
    class _ModelSubject(_Subject):
        def handles(self):
            return (InferenceLLM(object()),)  # type: ignore[arg-type]

    def asks(label):
        def call(value, llm):
            return llm.infer(system="s", prompt=str(value), task=label)

        return call

    same = differential.compare(_ModelSubject(), asks("triage"), asks("triage"))
    other = differential.compare(_ModelSubject(), asks("triage"), asks("classify"))
    assert same.equal and not same.labels_differ
    assert not other.equal and other.labels_differ


def test_a_different_output_is_found_and_the_first_kept():
    c = differential.compare(
        _Subject(), _body(lambda v: v * 2), _body(lambda v: v * 2 if v < 2 else 0)
    )
    assert (c.equal, c.equal_on) == (False, 1)
    assert c.first_difference["input"] == "2"


def test_a_different_effect_with_the_same_output_is_a_difference():
    c = differential.compare(_Subject(), _body(lambda v: v), _body(lambda v: v, notify=False))
    assert not c.equal and c.equal_on == 0
    assert "sent" in c.first_difference["hand_written"]["effects"]


def test_two_bodies_refusing_alike_agree_and_unlike_do_not():
    def raises(exc):
        def call(value, _notifier):
            raise exc("no")

        return call

    assert differential.compare(_Subject(), raises(ValueError), raises(ValueError)).equal
    assert not differential.compare(_Subject(), raises(ValueError), raises(KeyError)).equal


def test_a_harness_fault_is_never_a_body_behaviour():
    class Fault(RuntimeError):
        pass

    def faulty(value, _notifier):
        raise Fault("the host did not bind a function")

    with pytest.raises(Fault):
        differential.compare(_Subject(), _body(lambda v: v), faulty, (Fault,))


# ── Results and report ───────────────────────────────────────────────


def test_results_carry_the_differential_without_its_detail(tmp_path):
    out = tmp_path / "differential" / "toy"
    out.mkdir(parents=True)
    harness._write(
        out / "t.json",
        {
            "run": "toy",
            "trial": "t",
            "node": "DropSeen",
            "arm": "honest",
            "model": "haiku",
            "inputs": 4,
            "equal_on": 3,
            "equal": False,
            "first_difference": {"input": "x"},
        },
    )
    derived = harness.derive_results(tmp_path / "no-runs", tmp_path / "differential")
    assert derived["differential"] == [
        {
            "run": "toy",
            "trial": "t",
            "node": "DropSeen",
            "arm": "honest",
            "model": "haiku",
            "inputs": 4,
            "equal_on": 3,
            "equal": False,
        }
    ]
    summary = report.summarise_differential(derived["differential"])
    assert summary["total"] == {
        "compared": 1,
        "equal": 0,
        "differs": 1,
        "differs_labels": 0,
        "error": 0,
    }
    text = "\n".join(report.render_differential(summary))
    assert "| toy/honest | 1 | 0 | 1 | 0 | 0 |" in text and "not a gate" in text


def test_the_registered_run_is_never_summed_with_the_earlier_ones():
    def one(run, equal):
        return {"run": run, "node": "DropSeen", "arm": "P0", "inputs": 4, "equal": equal}

    summary = report.summarise_differential([one("toy", True), one(report.REGISTERED_RUN, False)])
    sources = summary["by_source"]
    assert sources["earlier runs (pilot, toy)"]["total"]["equal"] == 1
    assert sources["the registered run"]["total"]["differs"] == 1
    text = "\n".join(report.render_differential(summary))
    assert "In earlier runs (pilot, toy), 1 green bodies" in text
    assert "In the registered run, 1 green bodies" in text


def test_nothing_compared_is_said_plainly():
    text = "\n".join(report.render_differential(report.summarise_differential([])))
    assert "Not yet run" in text


# ── On real components ───────────────────────────────────────────────


@pytest.mark.skipif(not available(), reason="needs wasmtime (the poc group)")
@pytest.mark.parametrize("subject", SUBJECTS, ids=lambda s: s.node)
def test_each_hand_written_body_is_equal_to_itself(subject):
    """The step's own control, and what the report states: deterministic
    stand-in, deterministic effects, no difference where there is none."""
    result = harness.pipeline.differential(subject, None)
    assert result["equal"] is True and result["inputs"] > 0, result


_TOOLCHAIN = bool(shutil.which("cargo") and shutil.which("wasm-tools")) and available()


@pytest.mark.skipif(not _TOOLCHAIN, reason="needs cargo, wasm-tools and wasmtime")
def test_an_altered_body_is_found_to_differ(tmp_path):
    """The negative control: `SendReply` built from its own source, altered to
    send one character more. It is green, and it differs."""
    from poc.generation import pipeline, task

    send = BY_NODE["SendReply"]
    source = task.handwritten_source(send.component)
    assert "response_channel::send(&reply.text)" in source
    files = {
        "world.wit": task.handwritten_world(send.world),
        "lib.rs": source.replace(
            "response_channel::send(&reply.text)",
            'response_channel::send(&format!("{}!", reply.text))',
        ),
    }
    component, error = pipeline.build(files, tmp_path / "crate", tmp_path / "target")
    assert component is not None, error
    result = pipeline.differential(send, component)
    assert result["equal"] is False and result["first_difference"] is not None
