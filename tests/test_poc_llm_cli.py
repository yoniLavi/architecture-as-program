"""The Claude CLI backend, driven by a fake `claude` executable.

No test starts the real CLI: every call here goes to a small script that records
how it was invoked and prints a canned result. What is under test is the
invocation — no tools, no session, no inherited instructions, no API key — and
the handling of what comes back, including the usage ceiling that stops the
service before it spends a subscription the author is also using for other things.

Covers the `signal-graph-runtime` requirement "The LLM backend can be the local
Claude CLI".
"""

from __future__ import annotations

import json
import stat
import sys
from pathlib import Path

import pytest

from poc.llm import ClaudeCLIBackend, LLMRequest, ModelCallError, UsageLimitReached

_FAKE = """#!{python}
import json, os, sys
record = {{"argv": sys.argv[1:], "cwd": os.getcwd(), "stdin": sys.stdin.read(),
          "cwd_listing": os.listdir("."),
          "env": sorted(k for k in os.environ if k.startswith(("ANTHROPIC", "CLAUDE")))}}
with open({log!r}, "a") as f:
    f.write(json.dumps(record) + "\\n")
sys.stdout.write({stdout!r})
sys.stderr.write({stderr!r})
sys.exit({code})
"""


def _result(text: str = "release must_read", **extra) -> dict:
    return {
        "type": "result",
        "subtype": "success",
        "is_error": False,
        "result": text,
        "duration_ms": 1200,
        "usage": {"output_tokens": 7},
        "modelUsage": {"claude-haiku-5-5": {}},
        **extra,
    }


def _rate(five_hour: float, seven_day: float) -> dict:
    return {
        "type": "rate_limit_event",
        "rate_limit_info": {
            "unifiedWindows": {
                "five_hour": {"utilization": five_hour},
                "seven_day": {"utilization": seven_day},
            }
        },
    }


@pytest.fixture
def fake(tmp_path):
    """Build a fake CLI printing `stdout`; returns (backend, read_log)."""

    def make(stdout: object, *, code: int = 0, stderr: str = "", **kwargs):
        log = tmp_path / "calls.jsonl"
        exe = tmp_path / "claude"
        text = stdout if isinstance(stdout, str) else json.dumps(stdout)
        exe.write_text(
            _FAKE.format(python=sys.executable, log=str(log), stdout=text, stderr=stderr, code=code)
        )
        exe.chmod(exe.stat().st_mode | stat.S_IEXEC)
        backend = ClaudeCLIBackend(executable=str(exe), workdir=tmp_path / "llm", **kwargs)

        def read_log() -> list[dict]:
            return (
                [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []
            )

        return backend, read_log

    return make


REQUEST = LLMRequest(system="You classify.", prompt="Title: x\nText: y", task="triage")


def test_the_call_offers_no_tools_and_keeps_no_session(fake):
    backend, log = fake(_result())
    assert backend.generate(REQUEST).text == "release must_read"
    argv = log()[0]["argv"]
    assert argv[0] == "-p"
    assert argv[argv.index("--tools") + 1] == ""
    assert "--no-session-persistence" in argv
    assert "--safe-mode" in argv  # no CLAUDE.md, hooks, plugins or MCP servers
    assert argv[argv.index("--model") + 1] == "haiku"
    assert argv[argv.index("--system-prompt") + 1] == "You classify."


def test_the_prompt_goes_on_stdin_not_the_command_line(fake):
    backend, log = fake(_result())
    backend.generate(REQUEST)
    call = log()[0]
    assert call["stdin"] == REQUEST.prompt
    assert REQUEST.prompt not in call["argv"]


def test_each_call_runs_in_its_own_empty_directory_which_is_removed(fake, tmp_path):
    backend, log = fake(_result())
    backend.generate(REQUEST)
    backend.generate(REQUEST)
    first, second = log()
    assert first["cwd"] != second["cwd"]
    assert first["cwd_listing"] == [] and second["cwd_listing"] == []
    assert Path(first["cwd"]).resolve().parent == (tmp_path / "llm").resolve()
    assert list((tmp_path / "llm").iterdir()) == []


def test_no_api_key_or_parent_session_reaches_the_cli(fake, monkeypatch):
    """An API key in the environment would be billed per token in preference to
    the subscription; the parent session's variables would enrol the child in it."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-should-not-leak")
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "parent")
    monkeypatch.setenv("CLAUDECODE", "1")
    backend, log = fake(_result())
    backend.generate(REQUEST)
    assert log()[0]["env"] == []


def test_the_verbose_event_list_form_is_read_too(fake):
    backend, _ = fake([{"type": "system"}, _rate(0.2, 0.5), _result("ok")])
    assert backend.generate(REQUEST).text == "ok"
    assert backend.windows == {"five_hour": 0.2, "seven_day": 0.5}
    assert backend.usage[0]["model"] == "claude-haiku-5-5"


def test_a_request_offering_tools_is_refused_without_a_call(fake):
    backend, log = fake(_result())
    with pytest.raises(ModelCallError, match="inference only"):
        backend.generate(LLMRequest(system="s", prompt="p", offered_tools=("lookup",)))
    assert log() == []


def test_an_effort_level_is_passed_when_set(fake):
    backend, log = fake(_result(), effort="low", model="sonnet")
    backend.generate(REQUEST)
    argv = log()[0]["argv"]
    assert argv[argv.index("--effort") + 1] == "low"
    assert argv[argv.index("--model") + 1] == "sonnet"


# ── Failures ─────────────────────────────────────────────────────────


def test_an_error_result_is_a_model_call_error(fake):
    backend, _ = fake(_result("boom", is_error=True))
    with pytest.raises(ModelCallError, match="boom"):
        backend.generate(REQUEST)


def test_output_that_is_not_json_is_a_model_call_error(fake):
    backend, _ = fake("segfault", code=139)
    with pytest.raises(ModelCallError, match="139"):
        backend.generate(REQUEST)


def test_a_missing_executable_is_a_model_call_error(tmp_path):
    backend = ClaudeCLIBackend(executable=str(tmp_path / "nope"), workdir=tmp_path / "llm")
    with pytest.raises(ModelCallError, match="could not run"):
        backend.generate(REQUEST)


def test_a_rate_limited_result_is_a_usage_limit(fake):
    backend, _ = fake(_result("Claude usage limit reached", is_error=True, api_error_status=429))
    with pytest.raises(UsageLimitReached):
        backend.generate(REQUEST)


# ── The ceiling ──────────────────────────────────────────────────────


def test_a_window_at_the_ceiling_stops_the_next_call_before_it_starts(fake):
    """The call that reports the window full still returns; the one after it is
    refused without a process being started."""
    backend, log = fake([_rate(0.3, 0.95), _result("last one")], ceiling=0.9)
    assert backend.generate(REQUEST).text == "last one"
    with pytest.raises(UsageLimitReached, match="seven_day"):
        backend.generate(REQUEST)
    assert len(log()) == 1


def test_below_the_ceiling_calls_continue(fake):
    backend, log = fake([_rate(0.3, 0.6), _result()], ceiling=0.9)
    backend.generate(REQUEST)
    backend.generate(REQUEST)
    assert len(log()) == 2 and len(backend.calls) == 2
