//! `GenerateResponse` as a WASM **component** — the tool-capable node.
//!
//! Contract, unchanged from the graph:
//!   GenerateResponse : (ConversationContext) -> ok: AgentResponse | error: LLMError
//!     with LLMClient<[lookup]>, DBHandle<'knowledge-base', read>
//!
//! Its world imports exactly two interfaces — `tool-llm` (the LLM, offering only
//! the `lookup` tool) and `kb-read` (the read-only knowledge base). The
//! tool-orchestration loop still lives here, in the node body: the node decides
//! how to use its capabilities, and it can only reach the two it was granted.
//!
//! The port to typed WIT changed three things worth naming:
//!
//!   * **The model's reply is a `variant`, not a tagged string.** The core-wasm
//!     body parsed `"T" FS text` / `"C" FS tool FS query` out of a flat buffer and
//!     had a `_ => "malformed model reply"` arm for when that parse failed. A
//!     malformed reply is no longer representable: `reply` is either `Text` or
//!     `Call`, so the arm is gone along with the failure mode it handled.
//!
//!   * **The knowledge base returns `list<string>`.** No more 0x1E-joining and
//!     re-splitting a list through a string.
//!
//!   * **The output is the graph's sum type.** `response-result` has cases `ok`
//!     and `error` — the same role labels the graph's variant edges route on, so
//!     the runtime reads the case name directly instead of re-parsing a tag.
//!
//! What did NOT change is the security property, and it is worth being precise
//! about why. The node still checks `req.tool != "lookup"` below. That check is
//! not what confines it: `lookup` is the only tool the node has an interface for,
//! so a model demanding `exfiltrate` finds no import to travel through. The check
//! exists to turn an unreachable request into a *legible* error rather than
//! silently ignoring it. Confinement is the world; this is diagnostics.

wit_bindgen::generate!({
    path: "../../wit",
    world: "generate-response",
});

// `conversation-context` and `response-result` are re-exported at the crate root
// by the world's `use types.{...}`; the payload records come from the interface.
use crate::aap::caps::kb_read;
use crate::aap::caps::tool_llm::{self, Reply};
use crate::aap::caps::types::{AgentResponse, LlmError};

/// Tool-loop budget, matching the host tier's `ToolLLM._MAX_ROUNDS`.
const MAX_ROUNDS: usize = 3;
const SYSTEM: &str = "You are a helpful customer-support agent. Use the lookup tool if needed.";

/// The one tool this node's `with` clause grants. Named here only so the error
/// message below can be specific — the enforcement is the import set.
const GRANTED_TOOL: &str = "lookup";

struct Node;

impl Guest for Node {
    fn run(ctx: ConversationContext) -> ResponseResult {
        let question = ctx.question;
        let mut convo = question.clone();

        for _ in 0..MAX_ROUNDS {
            match tool_llm::generate(SYSTEM, &convo) {
                // The model answered. Done.
                Reply::Text(text) => {
                    return ResponseResult::Ok(AgentResponse { text });
                }
                // The model asked for a tool.
                Reply::Call(req) => {
                    if req.tool != GRANTED_TOOL {
                        // Unreachable authority, reported legibly. There is no
                        // import for this tool, so the node could not act on the
                        // request even if it wanted to; saying so beats dropping it.
                        return ResponseResult::Error(LlmError {
                            message: format!(
                                "requested tool {:?} is outside this node's capability set",
                                req.tool
                            ),
                        });
                    }
                    let hits = kb_read::lookup(&req.query);
                    let result = if hits.is_empty() {
                        "no knowledge-base match".to_string()
                    } else {
                        hits.join("; ")
                    };
                    convo = format!("{question}\n\n[TOOL RESULT lookup] {result}");
                }
            }
        }

        // Budget exhausted without a text reply. The host tier returns its last
        // (empty) text in the same situation; the two bodies stay interchangeable.
        ResponseResult::Ok(AgentResponse {
            text: String::new(),
        })
    }
}

export!(Node);
