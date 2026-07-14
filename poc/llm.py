"""LLM backends behind a single small interface.

The runtime talks to an `LLMBackend`. Two implementations:

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

from dataclasses import dataclass, field
from typing import Protocol


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
