# Generation prompt — `ParseMessage`

This file records the prompt given to the AI agent to generate `parse_message.py`,
per the proposal's development workflow (§5.2): the agent receives *only* the
node's signature, its contract, and the types of its inputs and outputs — it has
no visibility into adjacent nodes' implementations. Anything it needs from the
rest of the system must come through the typed signature.

## Node signature (from `graphs/customer-support.json`)

```
ParseMessage : (Untrusted<RawMessage>) -> CustomerQuery
  with LLMClient<inference>
discharges_trust: true
```

## Types in scope

```python
Untrusted[T]      # trust wrapper; .value gives the wrapped value
RawMessage        # .text: str
Intent(Enum)      # BILLING_QUESTION | TECHNICAL_SUPPORT | ACCOUNT_CHANGE
                  # | GENERAL_INQUIRY | UNKNOWN
CustomerQuery     # .intent: Intent, .entities: tuple[str, ...],
                  # .question: str  (bounded; MAX_QUESTION_LEN = 512)
InferenceLLM      # .infer(*, system: str, prompt: str, task: str) -> str
                  # NOTE: inference-only — there is NO tool-calling method
```

## Contract

1. **Trust discharge.** Consume `Untrusted[RawMessage]` and return a non-`Untrusted`
   `CustomerQuery`. The original raw text MUST NOT be passed through verbatim as
   an opaque blob; produce a *structured* representation.
2. **Closed intent set.** `intent` MUST be one of the `Intent` enum members. No
   matter what the input says, the function cannot widen this set — adversarial
   text cannot introduce a new intent.
3. **Bounded question.** `question` MUST be truncated to `CustomerQuery.MAX_QUESTION_LEN`.
   This field is the residual free-text channel and remains adversarial data;
   downstream nodes treat it as such.
4. **Capability use.** Classification MUST go through the injected `InferenceLLM`
   handle. The node has no other authority and must not attempt any effect beyond
   calling `.infer(...)`.

## Notes returned by the agent

- The intent string returned by the model is mapped onto the enum via a lookup;
  any unrecognised string falls back to `Intent.UNKNOWN`, preserving the closed set.
- Entity extraction is intentionally minimal (capitalised tokens) — a richer
  extractor is an implementation detail behind the same contract.
