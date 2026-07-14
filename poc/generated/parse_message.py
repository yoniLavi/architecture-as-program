"""AI-generated implementation of the `ParseMessage` node.

Generated from the signature + contract in `parse_message.prompt.md`. The runtime
imports `parse_message` from here; this module is the artifact that actually runs.

Contract recap:
  ParseMessage : (Untrusted<RawMessage>) -> CustomerQuery  with LLMClient<inference>
  - discharges trust: Untrusted in, non-Untrusted out
  - intent confined to the closed Intent enum
  - question bounded to CustomerQuery.MAX_QUESTION_LEN
  - all model access via the injected InferenceLLM handle (no other authority)
"""

from __future__ import annotations

import re

from ..handles import InferenceLLM
from ..values import CustomerQuery, Intent, RawMessage, Untrusted

_INTENT_BY_VALUE = {i.value: i for i in Intent}
_ENTITY_RE = re.compile(r"\b[A-Z][A-Za-z0-9_-]{2,}\b")


def parse_message(data: Untrusted[RawMessage], llm: InferenceLLM) -> CustomerQuery:
    raw = data.value.text

    # Classify via the inference-only handle. Whatever the model returns, we map
    # it onto the closed Intent set — adversarial text cannot widen it.
    label = (
        llm.infer(
            system=(
                "You are an intent classifier for customer-support messages. "
                "Reply with exactly one of: " + ", ".join(_INTENT_BY_VALUE) + "."
            ),
            prompt=raw,
            task="classify",
        )
        .strip()
        .lower()
    )
    intent = _INTENT_BY_VALUE.get(label, Intent.UNKNOWN)

    # Minimal entity extraction (capitalised tokens), de-duplicated, order-stable.
    entities = tuple(dict.fromkeys(_ENTITY_RE.findall(raw)))

    # Bounded question: the residual free-text channel. Still adversarial data;
    # downstream nodes (and the tool-capable LLM) must treat it as such.
    question = raw[: CustomerQuery.MAX_QUESTION_LEN]

    return CustomerQuery(intent=intent, entities=entities, question=question)
