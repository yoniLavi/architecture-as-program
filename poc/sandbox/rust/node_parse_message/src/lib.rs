//! `ParseMessage` as a WASM **component**.
//!
//! Contract, unchanged from the graph:
//!   ParseMessage : (Untrusted<RawMessage>) -> CustomerQuery  with LLMClient<inference>
//!
//! What changed from the core-wasm port is the boundary — and the boundary
//! changed the code. There is no `(ptr, len)` ABI, no 0x1F framing, and no
//! `alloc` export: the host and this component exchange `raw-message` and
//! `customer-query` *values*, and the marshalling is generated from
//! `poc/sandbox/wit/caps.wit`, which the host links against too.
//!
//! Two checks that the core-wasm body had to perform are gone, absorbed into the
//! type:
//!
//!   * **The closed intent set.** The old body got a string back from the model
//!     and tested it with `INTENTS.contains(...)`, so that adversarial text could
//!     not widen the intent set. Here `Intent` is a WIT `enum`: the widening that
//!     check was guarding against is not representable at all. `classify` below
//!     still maps an unknown label to `Unknown`, but it is now a total function
//!     into a closed type rather than a defensive filter over an open one.
//!
//!   * **The absence of a tool surface.** The old body noted in a comment that it
//!     imported no tool host function. Here it imports the `inference-llm`
//!     interface, whose one function returns a `string`. There is no tool-request
//!     case to receive and no tool interface in the world to call.
//!
//! Capability surface: this component's import set is exactly
//! `aap:caps/inference-llm@0.1.0` — not "plus some powerless WASI stubs", but
//! exactly that and nothing else. `tests/test_poc_sandbox.py` asserts it.

wit_bindgen::generate!({
    path: "../../wit",
    world: "parse-message",
});

// `raw-message` and `customer-query` are re-exported at the crate root by the
// world's `use types.{...}`; `Intent` is reached through its defining interface.
use crate::aap::caps::inference_llm;
use crate::aap::caps::types::Intent;

/// The one free-text field that survives into the structured world. Bounding it
/// is the node's job — the type system cannot say "short string" here.
const MAX_QUESTION_LEN: usize = 512;

const SYSTEM: &str = "You are an intent classifier for customer-support messages. \
                      Reply with exactly one of: billing_question, technical_support, \
                      account_change, general_inquiry, unknown.";

/// Map the model's free-text label onto the closed `Intent` enum.
///
/// Total by construction: any label that is not one of the four named intents
/// becomes `Unknown`. There is no way to return "some other intent" even if the
/// model insists on one, because `Intent` has no such value — the closed-set
/// guarantee is held by the type, not by a membership test in this function.
fn classify(label: &str) -> Intent {
    match label.trim().to_lowercase().as_str() {
        "billing_question" => Intent::BillingQuestion,
        "technical_support" => Intent::TechnicalSupport,
        "account_change" => Intent::AccountChange,
        "general_inquiry" => Intent::GeneralInquiry,
        _ => Intent::Unknown,
    }
}

/// Capitalised tokens (`[A-Z][A-Za-z0-9_-]{2,}`), de-duplicated, order-stable —
/// the same minimal entity extraction the Python node performs.
fn entities(raw: &str) -> Vec<String> {
    let mut out: Vec<String> = Vec::new();
    let mut token = String::new();
    let is_word = |c: char| c.is_ascii_alphanumeric() || c == '_' || c == '-';
    let push = |token: &mut String, out: &mut Vec<String>| {
        if token.len() >= 3 {
            if let Some(first) = token.chars().next() {
                if first.is_ascii_uppercase() && !out.contains(token) {
                    out.push(token.clone());
                }
            }
        }
        token.clear();
    };
    for c in raw.chars() {
        if is_word(c) {
            token.push(c);
        } else {
            push(&mut token, &mut out);
        }
    }
    push(&mut token, &mut out);
    out
}

struct Node;

impl Guest for Node {
    fn run(message: RawMessage) -> CustomerQuery {
        let raw = message.text;

        // Classify through the inference-only handle — the node's only reach
        // outside itself, and the only import in its world.
        let label = inference_llm::infer(SYSTEM, &raw, "classify");

        CustomerQuery {
            intent: classify(&label),
            entities: entities(&raw),
            // The residual free-text channel. Still adversarial data — but now a
            // bounded, *named* field of a typed record, not a slice of a blob
            // whose shape both sides had to agree about by convention.
            question: raw.chars().take(MAX_QUESTION_LEN).collect(),
        }
    }
}

export!(Node);
