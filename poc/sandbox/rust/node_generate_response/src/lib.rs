//! `GenerateResponse`, ported to Rust / `wasm32-wasip1`.
//!
//! The tool-capable node. Its module imports exactly two host functions —
//! `cap_generate` (the LLM, which offers only the `lookup` tool) and
//! `cap_kb_lookup` (the read-only knowledge-base handle) — and nothing else.
//! The tool-orchestration loop runs here, in the node body: the node decides how
//! to use its capabilities, and it can only reach the two it was granted.
//!
//! If the model asks for any tool other than `lookup`, the node has no import to
//! satisfy it and cannot act — the exact analogue of the host tier's `ToolLLM`
//! refusing an out-of-scope tool, but enforced by the absence of the import
//! rather than by a runtime check. `exfiltrate` is not refused; it is unreachable.
//!
//! Output is the node's sum type, framed as `ok FS <text>` or `error FS <msg>`.

use abi::{leak_str, take_string, unpack, FS, RS};

abi::abi_exports!();

#[link(wasm_import_module = "cap")]
extern "C" {
    /// One LLM round. Args: `system FS prompt`. Returns `T FS <text>` for a text
    /// answer, or `C FS <tool> FS <query>` for a tool-call request.
    fn cap_generate(ptr: i32, len: i32) -> i64;
    /// Read-only knowledge-base lookup. Args: `query`. Returns RS-joined hits.
    fn cap_kb_lookup(ptr: i32, len: i32) -> i64;
}

const MAX_ROUNDS: usize = 3;
const SYSTEM: &str = "You are a helpful customer-support agent. Use the lookup tool if needed.";

fn call(f: unsafe extern "C" fn(i32, i32) -> i64, args: &str) -> String {
    let packed = unsafe { f(args.as_ptr() as i32, args.len() as i32) };
    let (ptr, len) = unpack(packed);
    unsafe { take_string(ptr, len) }
}

#[no_mangle]
pub extern "C" fn run(ptr: i32, len: i32) -> i64 {
    let input = unsafe { take_string(ptr, len) };
    // ConversationContext: intent FS question FS knowledge(RS-joined).
    let mut fields = input.split(FS);
    let _intent = fields.next().unwrap_or("");
    let question = fields.next().unwrap_or("").to_string();

    let mut convo = question.clone();
    // Mirrors the host tier's ToolLLM.respond: run up to MAX_ROUNDS; a text reply
    // ends the loop, a tool reply is serviced and the loop continues. If the
    // budget is exhausted without a text reply, return the last text seen (empty)
    // as `ok` — the same outcome the host tier produces, so the two node bodies
    // stay interchangeable.
    let mut last_text = String::new();
    for _ in 0..MAX_ROUNDS {
        let reply = call(cap_generate, &format!("{SYSTEM}{FS}{convo}"));
        let mut parts = reply.split(FS);
        match parts.next() {
            Some("T") => {
                last_text = parts.next().unwrap_or("").to_string();
                return leak_str(&format!("ok{FS}{last_text}"));
            }
            Some("C") => {
                let tool = parts.next().unwrap_or("");
                let query = parts.next().unwrap_or("");
                if tool != "lookup" {
                    // No import exists for any other tool: the node cannot act on
                    // it. Faithful to the graph's LLMClient<[lookup]> scope.
                    return leak_str(&format!(
                        "error{FS}requested tool {tool:?} is outside this node's capability set"
                    ));
                }
                let hits = call(cap_kb_lookup, query);
                let joined = hits.replace(RS, "; ");
                let result = if joined.is_empty() {
                    "no knowledge-base match".to_string()
                } else {
                    joined
                };
                convo = format!("{question}\n\n[TOOL RESULT lookup] {result}");
            }
            _ => return leak_str(&format!("error{FS}malformed model reply")),
        }
    }
    leak_str(&format!("ok{FS}{last_text}"))
}
