"""LLM backends behind a single small interface.

The runtime talks to an `LLMBackend`. Three implementations (the third,
`ClaudeCLIBackend`, is the feed-triage service's live backend — the local `claude`
CLI on the author's subscription, inference only, documented at the class):

* `StubLLM` — a deterministic, offline backend. It classifies/moderates/answers
  using simple rules. This is what runs by default and in CI: it makes the
  security tests deterministic and network-free. It is a *stand-in* for a model,
  clearly labelled as such; the security properties the PoC demonstrates are
  structural and do not depend on the model's quality.
* `AnthropicBackend` — calls the real Claude API (opt-in, `--live`). This is what
  authentically stress-tests "LLM as trust discharger": a real model is given the
  adversarial input and we observe that capability confinement holds regardless.

Crucially, a backend only ever returns *data* (text, or a request to call one of
the tools it was told about). It has no ability to perform effects itself — tool
execution is mediated by the capability handle that wraps the backend (see
`handles.py`), which is where scope is enforced.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

_REPO_ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class ToolCall:
    """A backend's *request* to call a tool. Whether the call is permitted, and
    its execution, is decided by the capability handle — not here."""

    name: str
    arguments: dict


@dataclass(frozen=True)
class LLMRequest:
    system: str
    prompt: str
    # Tools the model is told it may call. The wrapping handle guarantees this
    # never exceeds the handle's scope.
    offered_tools: tuple[str, ...] = ()
    # A coarse hint so the stub knows what kind of answer to synthesise.
    task: str = "respond"


@dataclass(frozen=True)
class LLMResponse:
    text: str = ""
    tool_calls: tuple[ToolCall, ...] = ()


class LLMBackend(Protocol):
    def generate(self, request: LLMRequest) -> LLMResponse: ...


# ── Deterministic offline backend ──────────────────────────────────


# Keyword tables for the stub's classification. Deliberately simple — the point
# is determinism, not NLP quality.
_INTENT_KEYWORDS: dict[str, tuple[str, ...]] = {
    "billing_question": ("bill", "invoice", "charge", "refund", "payment", "price"),
    "technical_support": ("error", "bug", "crash", "broken", "not working", "login"),
    "account_change": ("cancel", "upgrade", "downgrade", "change my", "close account"),
}

# Strings that, if present, the stub moderator flags as a policy violation.
_MODERATION_BLOCKLIST: tuple[str, ...] = ("self-harm", "explicit-violence-token")


@dataclass
class StubLLM:
    """Deterministic, offline stand-in for a model. Records every request it
    received so tests can inspect exactly what reached the model layer (e.g. to
    assert the tool-capable node never received raw user text)."""

    calls: list[LLMRequest] = field(default_factory=list)

    def generate(self, request: LLMRequest) -> LLMResponse:
        self.calls.append(request)
        text = request.prompt.lower()
        if request.task == "classify":
            return LLMResponse(text=self._classify(text))
        if request.task == "moderate":
            verdict = "violation" if any(b in text for b in _MODERATION_BLOCKLIST) else "ok"
            return LLMResponse(text=verdict)
        # The feed-triage tasks. Same stance as above: keyword rules, so the
        # service's tests are deterministic and call no model.
        if request.task == "triage":
            return LLMResponse(text=self._triage(text))
        if request.task == "summarise":
            body = request.prompt.split("Text: ", 1)[-1]
            return LLMResponse(text=" ".join(body.split())[:160])
        if request.task == "digest":
            count = sum(1 for line in request.prompt.splitlines() if line.startswith("- "))
            return LLMResponse(text=f"{count} item(s) worth your attention today.")
        # Default: synthesise a benign answer. If a lookup tool is offered, ask
        # for it once — exercising the tool path through the handle's scope check.
        if "lookup" in request.offered_tools:
            return LLMResponse(tool_calls=(ToolCall("lookup", {"query": request.prompt[:64]}),))
        return LLMResponse(text="Thanks for reaching out — here is the information you requested.")

    @staticmethod
    def _classify(text: str) -> str:
        for intent, keywords in _INTENT_KEYWORDS.items():
            if any(k in text for k in keywords):
                return intent
        return "general_inquiry"

    @staticmethod
    def _triage(text: str) -> str:
        """`<category> <importance>` for a feed item, by keyword."""
        category = "other"
        for name, keywords in _CATEGORY_KEYWORDS.items():
            if any(k in text for k in keywords):
                category = name
                break
        if any(k in text for k in _MUST_READ_KEYWORDS):
            importance = "must_read"
        elif category in ("security", "research", "release"):
            importance = "worth_a_look"
        else:
            importance = "skip"
        return f"{category} {importance}"


_CATEGORY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "security": ("vulnerab", "cve-", "exploit", "injection", "sandbox escape"),
    "release": ("released", "release notes", "now available", "announcing"),
    "research": ("we propose", "we present", "arxiv", "this paper"),
    "tooling": ("cli", "library", "plugin", "toolchain"),
    "discussion": ("opinion", "thoughts on", "ask hn"),
}
_MUST_READ_KEYWORDS: tuple[str, ...] = ("capabilit", "webassembly", "wasm", "coding agent")


# ── The local Claude CLI (opt-in; the service's live backend) ──────


class ModelCallError(RuntimeError):
    """A model call that produced no usable answer: the CLI failed, timed out, or
    returned something that was not its own result format."""


class UsageLimitReached(ModelCallError):
    """The subscription's usage window is exhausted, or close enough to it that
    this backend's ceiling refuses to go further. Not a failure of the work: stop,
    and resume when the window resets."""


# Environment variables never passed to the CLI. An API key in the environment
# would be used in preference to the logged-in subscription and billed per token,
# which this backend exists to avoid; the `CLAUDE*` variables describe a *parent*
# Claude Code session and would make the child behave as part of it.
_SCRUBBED_PREFIXES = ("ANTHROPIC_", "CLAUDE", "AI_AGENT")


def _clean_env() -> dict[str, str]:
    return {k: v for k, v in os.environ.items() if not k.startswith(_SCRUBBED_PREFIXES)}


def _usage_windows(events: list) -> dict[str, float]:
    """The utilisation of each usage window the CLI reported, from 0.0 to 1.0."""
    windows: dict[str, float] = {}
    for event in events:
        if not isinstance(event, dict) or event.get("type") != "rate_limit_event":
            continue
        info = event.get("rate_limit_info") or {}
        for name, window in (info.get("unifiedWindows") or {}).items():
            if isinstance(window, dict) and isinstance(window.get("utilization"), int | float):
                windows[name] = float(window["utilization"])
    return windows


# The Claude models this repository runs, alias → full ID. An alias resolves at
# call time and can move between releases; anything that must name what it ran
# (the registered generation run, a replay) calls the model by its full ID and
# records what the call resolved to. One table, so the two cannot disagree.
CLAUDE_MODEL_IDS: dict[str, str] = {
    "haiku": "claude-haiku-5-5",
    "sonnet": "claude-sonnet-5-5",
    "opus": "claude-opus-5-5",
}


@dataclass
class ClaudeCLIBackend:
    """Calls the locally installed, logged-in `claude` CLI — one process per call.

    This is how the feed-triage service and the generation experiment reach a
    model without an API key: the author's existing subscription, through the CLI,
    in print mode. Each call is made as bare as the CLI allows:

    * `--tools ""`: the model has no tool. It cannot read a file, run a command or
      fetch a URL, so a model call can return text and do nothing else — the same
      attenuation `LLMClient<inference>` claims, enforced at the call as well.
    * `--safe-mode`: no `CLAUDE.md`, memory, hooks, plugins, skills or MCP
      servers. The working directory sits under the repository's `var/`, so
      without this the CLI would discover the repository's own instructions and
      hand them to a model that is supposed to see only its prompt.
    * `--system-prompt`: the node's own system text replaces the CLI's default
      agent prompt.
    * `--no-session-persistence`, and a fresh empty working directory per call,
      removed afterwards: one call leaves nothing for the next to find.

    It serves inference only. A request that offers tools is refused, since
    nothing here speaks a tool-use protocol.

    **Usage.** The subscription is the author's, and shared with whatever else is
    using it. The CLI reports each usage window's utilisation with every call;
    once any window is at or above `ceiling`, further calls raise
    `UsageLimitReached` without starting a process. Callers treat that as "stop
    and resume later", never as an error in the work.

    Never used by a test or a build step: those run `StubLLM`."""

    model: str = "haiku"
    workdir: Path = field(default_factory=lambda: _REPO_ROOT / "var" / "llm")
    executable: str = "claude"
    timeout: float = 600.0
    # Reasoning effort passed to the CLI, or None for its default.
    effort: str | None = None
    ceiling: float = 0.90
    calls: list[LLMRequest] = field(default_factory=list)
    # One record per completed call: model, duration, tokens. For the run report.
    usage: list[dict] = field(default_factory=list)
    windows: dict[str, float] = field(default_factory=dict)

    def command(self, request: LLMRequest) -> list[str]:
        cmd = [
            self.executable,
            "-p",
            "--safe-mode",
            "--model",
            self.model,
            "--tools",
            "",
            "--no-session-persistence",
            "--output-format",
            "json",
        ]
        if self.effort:
            cmd += ["--effort", self.effort]
        if request.system:
            cmd += ["--system-prompt", request.system]
        return cmd

    def generate(self, request: LLMRequest) -> LLMResponse:
        if request.offered_tools:
            raise ModelCallError(
                f"the Claude CLI backend serves inference only; it cannot offer "
                f"tools {list(request.offered_tools)}"
            )
        over = {n: u for n, u in self.windows.items() if u >= self.ceiling}
        if over:
            raise UsageLimitReached(
                f"usage window(s) {over} are at or above the {self.ceiling:.0%} ceiling"
            )
        self.calls.append(request)

        self.workdir.mkdir(parents=True, exist_ok=True)
        cwd = Path(tempfile.mkdtemp(prefix="call-", dir=self.workdir))
        try:
            try:
                done = subprocess.run(
                    self.command(request),
                    input=request.prompt,
                    capture_output=True,
                    text=True,
                    cwd=cwd,
                    env=_clean_env(),
                    timeout=self.timeout,
                    check=False,
                )
            except subprocess.TimeoutExpired as e:
                raise ModelCallError(f"the model call timed out after {self.timeout:.0f}s") from e
            except OSError as e:
                raise ModelCallError(f"could not run {self.executable!r}: {e}") from e
        finally:
            shutil.rmtree(cwd, ignore_errors=True)

        return self._read(done)

    def _read(self, done: subprocess.CompletedProcess) -> LLMResponse:
        try:
            parsed = json.loads(done.stdout)
        except json.JSONDecodeError as e:
            detail = (done.stderr or done.stdout or "").strip()[:400]
            if "limit" in detail.lower():
                raise UsageLimitReached(detail) from e
            raise ModelCallError(
                f"the CLI exited {done.returncode} without a JSON result: {detail}"
            ) from e
        # `--output-format json` is one result object, or — in verbose mode — the
        # list of events ending in it.
        events = parsed if isinstance(parsed, list) else [parsed]
        self.windows.update(_usage_windows(events))
        result = next(
            (e for e in reversed(events) if isinstance(e, dict) and e.get("type") == "result"),
            None,
        )
        if result is None:
            raise ModelCallError("the CLI's output held no result")
        text = result.get("result")
        if result.get("is_error") or not isinstance(text, str):
            detail = str(text or result.get("subtype") or "")[:400]
            if result.get("api_error_status") == 429 or "usage limit" in detail.lower():
                raise UsageLimitReached(detail)
            raise ModelCallError(f"the model call failed: {detail}")
        self.usage.append(
            {
                "model": next(iter(result.get("modelUsage") or {}), self.model),
                "duration_ms": result.get("duration_ms"),
                "output_tokens": (result.get("usage") or {}).get("output_tokens"),
            }
        )
        return LLMResponse(text=text.strip())


# ── Real Claude backend (opt-in) ───────────────────────────────────


MODEL = "claude-opus-4-8"

# JSON schemas for the tools a node may offer. The backend can only ever *ask*
# for one of these; whether the call is permitted and executed is decided by the
# capability handle, never here.
_TOOL_SCHEMAS: dict[str, dict] = {
    "lookup": {
        "name": "lookup",
        "description": (
            "Look up articles in the customer-support knowledge base. "
            "Call this when answering a question requires product documentation."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "What to look up."},
            },
            "required": ["query"],
        },
    },
}


@dataclass
class AnthropicBackend:
    """Calls the real Claude API. Used with `--live` so the adversarial
    demonstration runs against an actual model rather than a stub.

    Note what this class does *not* do: it never executes a tool. The Messages
    API only ever *requests* a tool call (a `tool_use` content block); the caller
    decides whether to honour it. That is precisely the capability boundary the
    proposal argues for, and it lives in `handles.ToolLLM`, not here.

    Only the tools named in `request.offered_tools` are declared to the model —
    an `InferenceLLM` handle forces that list empty, so the model is never even
    told tools exist."""

    model: str = MODEL
    max_tokens: int = 1024
    calls: list[LLMRequest] = field(default_factory=list)
    _client: object | None = field(default=None, repr=False, compare=False)

    def _ensure_client(self):
        if self._client is None:
            try:
                import anthropic
            except ImportError as e:  # pragma: no cover - depends on optional group
                raise RuntimeError(
                    "the --live path needs the Anthropic SDK: `uv sync --group poc`"
                ) from e
            self._client = anthropic.Anthropic()
        return self._client

    def generate(self, request: LLMRequest) -> LLMResponse:
        self.calls.append(request)
        client = self._ensure_client()

        kwargs: dict = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "system": request.system,
            "messages": [{"role": "user", "content": request.prompt}],
        }
        # Declare only the tools this handle's scope permits. Empty => omit
        # entirely, so an inference-only node's model sees no tools at all.
        tools = [_TOOL_SCHEMAS[t] for t in request.offered_tools if t in _TOOL_SCHEMAS]
        if tools:
            kwargs["tools"] = tools

        # Note: no temperature/top_p — those are rejected (400) on this model.
        response = client.messages.create(**kwargs)  # type: ignore[attr-defined]

        text_parts: list[str] = []
        tool_calls: list[ToolCall] = []
        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                tool_calls.append(ToolCall(name=block.name, arguments=dict(block.input)))

        return LLMResponse(text="".join(text_parts).strip(), tool_calls=tuple(tool_calls))
