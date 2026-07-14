"""Sandbox-tier node adapters.

Each adapter has the *same* shape as a host-tier node implementation —
``impl(data_value, *capability_handles)`` — so the executor can run either tier
through one code path. Inside, an adapter:

1. marshals the node's input value into the ABI's flat string form,
2. exposes the node's Python capability handles as ``str -> str`` host functions
   (these are the only imports the module is linked against — its capability set),
3. runs the WASM module under the empty-WASI `Sandbox`, and
4. unmarshals the module's output back into a domain value.

The capability handles are the *same objects* the host tier uses (`InferenceLLM`,
`ToolLLM`, `ReadDBHandle`). The difference is purely in enforcement: on this tier
the node body cannot reach past the host functions wired here, because it runs as
a confined WASM module rather than as trusted Python.
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
from .host import FS, RS, Sandbox


def parse_message_sandbox(data: Untrusted[RawMessage], llm: InferenceLLM) -> CustomerQuery:
    """`ParseMessage` on the sandbox tier. Its module imports exactly `cap_infer`
    — the inference-only LLM — and nothing else."""

    def cap_infer(args: str) -> str:
        system, prompt, task = args.split(FS)
        return llm.infer(system=system, prompt=prompt, task=task)

    sandbox = Sandbox("node_parse_message", {"cap_infer": cap_infer})
    out = sandbox.call_run(data.value.text)

    intent_str, entities_field, question = out.split(FS)
    try:
        intent = Intent(intent_str)
    except ValueError:
        intent = Intent.UNKNOWN
    entities = tuple(e for e in entities_field.split(RS) if e)
    return CustomerQuery(intent=intent, entities=entities, question=question)


def generate_response_sandbox(ctx: ConversationContext, llm: ToolLLM, db: ReadDBHandle) -> Variant:
    """`GenerateResponse` on the sandbox tier. Its module imports exactly two host
    functions — `cap_generate` (the LLM, offering only the node's allowed tools)
    and `cap_kb_lookup` (the read-only DB) — and nothing else. The tool loop runs
    inside the module; a tool outside `{lookup}` has no import and cannot be run."""

    def cap_generate(args: str) -> str:
        system, prompt = args.split(FS)
        # Offer only the tools this handle's scope permits, exactly as the host
        # tier does. Whatever the model then requests, the module can only act on
        # tools it has an import for.
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
            return f"C{FS}{call.name}{FS}{query}"
        return f"T{FS}{resp.text}"

    def cap_kb_lookup(args: str) -> str:
        return RS.join(db.read(args))

    sandbox = Sandbox(
        "node_generate_response",
        {"cap_generate": cap_generate, "cap_kb_lookup": cap_kb_lookup},
    )
    out = sandbox.call_run(f"{ctx.intent.value}{FS}{ctx.question}{FS}{RS.join(ctx.knowledge)}")

    tag, _, payload = out.partition(FS)
    if tag == "ok":
        return Variant("ok", AgentResponse(text=payload))
    return Variant("error", LLMError(message=payload))


# Sandbox-tier implementations, keyed by graph node name — the sandbox analogue
# of `poc.nodes.REGISTRY`. A node not listed here has no sandbox port yet.
SANDBOX_REGISTRY = {
    "ParseMessage": parse_message_sandbox,
    "GenerateResponse": generate_response_sandbox,
}
