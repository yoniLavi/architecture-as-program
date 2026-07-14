"""Component-tier node adapters.

Each adapter has the *same* shape as a host-tier node implementation —
``impl(data_value, *capability_handles)`` — so the executor runs either tier
through one code path. Inside, an adapter:

1. converts the node's input value into the WIT record the component expects,
2. exposes the node's Python capability handles as the functions of the typed WIT
   interfaces its world imports (these are the only interfaces it is linked
   against — its capability set),
3. runs the component under the `Sandbox`, and
4. converts the component's typed output back into a domain value.

The capability handles are the *same objects* the host tier uses (`InferenceLLM`,
`ToolLLM`, `ReadDBHandle`). The difference is purely in enforcement: on this tier
the node body cannot reach past the interfaces wired here, because it runs as a
confined WASM component whose import set contains nothing else.

Compare the core-wasm version this replaces. Steps 1 and 4 were `str.split(FS)`
and f-string framing over a flat byte ABI, and the `ok`/`error` sum type came back
as a tag character to re-parse. Here the conversions are field-for-field, the
intent is an enum on both sides, and the component's `response-result` variant
arrives carrying the same case labels the graph routes on. The adapters got
shorter because the boundary got smarter.
"""

from __future__ import annotations

from ..handles import InferenceLLM, ReadDBHandle, ToolLLM
from ..llm import LLMRequest
from ..values import (
    AgentResponse,
    ConversationContext,
    CustomerQuery,
    Intent,
    LLMError,
    RawMessage,
    Untrusted,
    Variant,
)
from .host import Sandbox, record
from .interfaces import INFERENCE_LLM, KB_READ, TOOL_LLM


# WIT idents are kebab-case; the domain `Intent` enum's values are snake_case.
# One conversion, in one place — not a string protocol each side reparses.
def _to_intent(wit_intent: str) -> Intent:
    """Lift a WIT `intent` enum case (`billing-question`) into the domain `Intent`."""
    try:
        return Intent(wit_intent.replace("-", "_"))
    except ValueError:  # pragma: no cover — WIT's enum is closed; this cannot widen
        return Intent.UNKNOWN


def _from_intent(intent: Intent) -> str:
    """Lower a domain `Intent` into its WIT enum case."""
    return intent.value.replace("_", "-")


def parse_message_sandbox(data: Untrusted[RawMessage], llm: InferenceLLM) -> CustomerQuery:
    """`ParseMessage` on the component tier.

    Its world imports exactly `aap:caps/inference-llm@0.1.0` — the inference-only
    LLM — and nothing else. No tool interface, no knowledge base, and (unlike the
    core-wasm module it replaces) no WASI stubs either.
    """

    def infer(system: str, prompt: str, task: str) -> str:
        return llm.infer(system=system, prompt=prompt, task=task)

    sandbox = Sandbox("node_parse_message", {INFERENCE_LLM: {"infer": infer}})
    out = sandbox.call("run", record(text=data.value.text))

    # `out` is a typed customer-query: an enum, a list, a string. Nothing to parse
    # and no framing to get wrong — and `out.intent` *cannot* be a value outside
    # the closed set, because the WIT enum has no other case to return.
    return CustomerQuery(
        intent=_to_intent(out.intent),
        entities=tuple(out.entities),
        question=out.question,
    )


def generate_response_sandbox(ctx: ConversationContext, llm: ToolLLM, db: ReadDBHandle) -> Variant:
    """`GenerateResponse` on the component tier.

    Its world imports exactly two interfaces — `tool-llm` (the LLM, offering only
    the tools this handle's scope permits) and `kb-read` (the read-only knowledge
    base). The tool loop runs inside the component; a tool outside `{lookup}` has
    no interface in its world, so it cannot be invoked at all.
    """

    def generate(system: str, prompt: str):
        # Offer only the tools this handle's scope permits, exactly as the host
        # tier does. Whatever the model then requests, the component can only act
        # on a tool it has an import for.
        resp = llm.backend.generate(
            LLMRequest(
                system=system,
                prompt=prompt,
                offered_tools=tuple(sorted(llm.allowed_tools)),
                task="respond",
            )
        )
        if resp.tool_calls:
            call = resp.tool_calls[0]
            query = str(call.arguments.get("query", "")) if call.arguments else ""
            # The `call(tool-request)` case of the `reply` variant. wasmtime selects
            # the case from the value's shape: a record here, a plain `str` below.
            return record(tool=call.name, query=query)
        return resp.text

    def lookup(query: str) -> list[str]:
        # A WIT `list<string>` crosses as a list. The core-wasm tier joined it with
        # 0x1E on the way out and split it on the way in.
        return db.read(query)

    sandbox = Sandbox(
        "node_generate_response",
        {TOOL_LLM: {"generate": generate}, KB_READ: {"lookup": lookup}},
    )
    out = sandbox.call(
        "run",
        record(
            intent=_from_intent(ctx.intent),
            question=ctx.question,
            knowledge=list(ctx.knowledge),
        ),
    )

    # `out` is the graph's sum type: a WIT variant whose case labels are the very
    # `ok` / `error` roles the graph's variant edges route on.
    if out.tag == "ok":
        return Variant("ok", AgentResponse(text=out.payload.text))
    return Variant("error", LLMError(message=out.payload.message))


# Component-tier implementations, keyed by graph node name — the sandbox analogue
# of `poc.nodes.REGISTRY`. A node not listed here has no component port yet and
# runs on the host tier.
SANDBOX_REGISTRY = {
    "ParseMessage": parse_message_sandbox,
    "GenerateResponse": generate_response_sandbox,
}
