# Generation prompt — `ParseMessage`, Rust / `wasm32-wasip1`

This file records the prompt used to generate the **sandbox-tier** implementation
of `ParseMessage` (`poc/sandbox/rust/node_parse_message/src/lib.rs`). It is the
same node, the same signature, and the same contract as the host-tier Python
version (`poc/generated/parse_message.py`) — a *different implementation language*
for the node body, and nothing else.

This is the proposal's "code as compiled artifact" property made literal (§2,
@sec:thesis): the graph's type signatures and contract are the stable interface;
the implementation inside the node is interchangeable. The graph JSON does not
change, the wiring does not change, and both node bodies satisfy the same tests
(`test_sandbox_and_host_tiers_produce_the_same_outcome`). Which tier — and which
language — runs the node is a deployment choice, not an architectural one.

## Node signature (from `graphs/customer-support.json`)

```
ParseMessage : (Untrusted<RawMessage>) -> CustomerQuery
  with LLMClient<inference>
discharges_trust: true
```

## Capability surface (WASM)

The module is compiled to `wasm32-wasip1` and run under an empty WASI context. Its
**only** import is one host function:

```
cap_infer(args_ptr, args_len) -> packed(ptr,len)   // the inference-only LLM
```

There is deliberately no tool-calling import, no filesystem, no socket, no
environment, and no clock. The inference-only guarantee that the host tier
enforces by the *absence of a method* becomes, here, the *absence of an import* —
a strictly stronger property (`test_inference_only_node_has_no_tool_import_at_all`).

## ABI

Flat bytes in linear memory, addressed by a packed `(ptr << 32) | len` i64; fields
framed by `FS` (0x1F), list elements by `RS` (0x1E). See
`poc/sandbox/rust/abi/src/lib.rs`. Input to `run` is the raw message text; output
is `intent FS entities(RS-joined) FS question`.

## Contract (identical to the Python version)

1. **Trust discharge.** Consume the raw untrusted message and return a structured
   `CustomerQuery`. The original raw text MUST NOT pass through as an opaque blob.
2. **Closed intent set.** `intent` MUST be one of
   `billing_question | technical_support | account_change | general_inquiry |
   unknown`. Any unrecognised model output falls back to `unknown` — adversarial
   text cannot widen the set.
3. **Bounded question.** `question` MUST be truncated to 512 characters. This is
   the residual free-text channel and remains adversarial data downstream.
4. **Capability use.** Classification MUST go through the injected `cap_infer`
   import. The node has no other authority — and, on this tier, no *mechanism* to
   acquire any, because nothing else is in its import table.

## Notes returned by the agent

- The classifier output is mapped onto the closed set exactly as the Python
  version does; the fallback to `unknown` preserves the invariant regardless of
  what the model (or an adversary influencing it) returns.
- Entity extraction (capitalised tokens, de-duplicated, order-stable) is
  reimplemented without a regex crate to keep the module dependency-free and the
  artifact small; it is an implementation detail behind the same contract.
