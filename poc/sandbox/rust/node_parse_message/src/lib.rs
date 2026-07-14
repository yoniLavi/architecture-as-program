//! `ParseMessage`, regenerated in Rust and compiled to `wasm32-wasip1`.
//!
//! Same signature, same contract, unchanged graph — a different implementation
//! language for the node body. This is "code as compiled artifact" made literal:
//! the Python version in `poc/generated/parse_message.py` and this one both
//! satisfy the `ParseMessage` contract; the graph does not know or care which
//! runs. See `poc/generated/parse_message.wasm.prompt.md` for the generation
//! prompt.
//!
//! Contract:
//!   ParseMessage : (Untrusted<RawMessage>) -> CustomerQuery  with LLMClient<inference>
//!   * discharges trust: raw untrusted text in, structured CustomerQuery out
//!   * intent confined to the closed Intent set — adversarial text cannot widen it
//!   * question bounded to MAX_QUESTION_LEN (512)
//!   * model access ONLY through the injected inference capability
//!
//! Capability surface: the module imports exactly one host function, `cap_infer`.
//! There is no filesystem, socket, environment, clock, or tool-calling import —
//! not because a method is hidden, but because the import table does not contain
//! one. That absence is the sandbox tier's enforcement.

use abi::{leak_str, take_string, unpack, FS, RS};

abi::abi_exports!();

#[link(wasm_import_module = "cap")]
extern "C" {
    /// Inference-only LLM call. Args: `system FS prompt FS task`. Returns the
    /// classification string. No tool-calling counterpart exists to import.
    fn cap_infer(ptr: i32, len: i32) -> i64;
}

const MAX_QUESTION_LEN: usize = 512;
const INTENTS: [&str; 5] = [
    "billing_question",
    "technical_support",
    "account_change",
    "general_inquiry",
    "unknown",
];

fn infer(system: &str, prompt: &str, task: &str) -> String {
    let args = format!("{system}{FS}{prompt}{FS}{task}");
    let packed = unsafe { cap_infer(args.as_ptr() as i32, args.len() as i32) };
    let (ptr, len) = unpack(packed);
    unsafe { take_string(ptr, len) }
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

#[no_mangle]
pub extern "C" fn run(ptr: i32, len: i32) -> i64 {
    let raw = unsafe { take_string(ptr, len) };

    // Classify via the inference-only handle. Whatever the model returns is
    // mapped onto the closed set; an unrecognised label falls back to "unknown",
    // so adversarial text can never introduce a new intent.
    let label = infer(
        "You are an intent classifier for customer-support messages. \
         Reply with exactly one of: billing_question, technical_support, \
         account_change, general_inquiry, unknown.",
        &raw,
        "classify",
    );
    let label = label.trim().to_lowercase();
    let intent = if INTENTS.contains(&label.as_str()) {
        label.as_str()
    } else {
        "unknown"
    };

    let ents = entities(&raw).join(&RS.to_string());

    // Bounded question — the residual free-text channel, still adversarial data.
    let question: String = raw.chars().take(MAX_QUESTION_LEN).collect();

    leak_str(&format!("{intent}{FS}{ents}{FS}{question}"))
}
