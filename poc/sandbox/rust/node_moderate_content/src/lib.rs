//! `ModerateContent` as a WASM **component** — an inference-only classifier.
//!
//! Contract, unchanged from the graph:
//!   ModerateContent : (CustomerQuery)
//!     -> ok: ModeratedQuery | violation: PolicyViolation | escalation: EscalationRequest
//!     with LLMClient<inference>
//!
//! Its world imports exactly `inference-llm` and nothing else — the same
//! attenuation as `ParseMessage`: it can be *influenced* by the query text it
//! classifies, but holds no tool interface through which to *act* on it. The
//! moderation verdict is a three-way `variant` whose case names (`ok`, `violation`,
//! `escalation`) are the very ports the graph's variant edges route on, so the
//! runtime reads the case directly instead of re-parsing a tag string.
//!
//! Interchangeable with the Python body by construction: same signature, same
//! contract, same closed intent set carried through, a different implementation
//! language. Confinement is the world; the classification logic is the node's own.

wit_bindgen::generate!({
    path: "../../wit",
    world: "moderate-content",
});

// `customer-query` and `moderation-result` are re-exported at the crate root by
// the world's `use types.{...}`; the variant's payload records are reached through
// their defining interface.
use crate::aap::caps::inference_llm;
use crate::aap::caps::types::{EscalationRequest, ModeratedQuery, PolicyViolation};

const SYSTEM: &str = "You are a content-moderation classifier. Reply with exactly one of: \
                      ok, violation, escalation.";

struct Node;

impl Guest for Node {
    fn run(query: CustomerQuery) -> ModerationResult {
        // Classify through the inference-only handle — the node's only reach
        // outside itself, and the only import in its world.
        let verdict = inference_llm::infer(SYSTEM, &query.question, "moderate")
            .trim()
            .to_lowercase();

        match verdict.as_str() {
            "violation" => ModerationResult::Violation(PolicyViolation {
                reason: "content policy".to_string(),
            }),
            "escalation" => ModerationResult::Escalation(EscalationRequest {
                query,
                reason: "ambiguous".to_string(),
            }),
            // Anything else is treated as clean, exactly as the host body does:
            // a classifier that fails open here would be a policy choice, and the
            // Python and Rust bodies make the same one.
            _ => ModerationResult::Ok(ModeratedQuery { query }),
        }
    }
}

export!(Node);
