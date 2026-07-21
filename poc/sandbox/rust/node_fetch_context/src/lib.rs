//! `FetchContext` as a WASM **component** — a capability-holding node regenerated
//! in a second language.
//!
//! Contract, unchanged from the graph:
//!   FetchContext : (ModeratedQuery) -> ConversationContext
//!     with DBHandle<'knowledge-base', read>
//!
//! Its world imports exactly `kb-read`, the read-only knowledge base, and nothing
//! else. This is the point of regenerating *this* node: it exercises the typed
//! capability boundary — a database read — rather than a pure transformation.
//! `kb-read` offers `lookup` and no writer, so the node that assembles context has
//! no import through which to mutate the store; the read-only mode of the graph
//! type is the absence of a function, not a runtime permission check.
//!
//! The `list<string>` the knowledge base returns crosses as a list — no 0x1E
//! joining and re-splitting through a string, as the retired flat ABI needed.

wit_bindgen::generate!({
    path: "../../wit",
    world: "fetch-context",
});

// `moderated-query` and `conversation-context` are re-exported at the crate root
// by the world's `use types.{...}`; `Intent` is reached through its defining
// interface.
use crate::aap::caps::kb_read;
use crate::aap::caps::types::Intent;

/// The knowledge-base key for an intent: the snake_case spelling the store is
/// keyed by, matching the host node's `db.read(mq.query.intent.value)`. Total over
/// the closed `Intent` enum — there is no "other" case to forget.
fn intent_key(intent: Intent) -> &'static str {
    match intent {
        Intent::BillingQuestion => "billing_question",
        Intent::TechnicalSupport => "technical_support",
        Intent::AccountChange => "account_change",
        Intent::GeneralInquiry => "general_inquiry",
        Intent::Unknown => "unknown",
    }
}

struct Node;

impl Guest for Node {
    fn run(mq: ModeratedQuery) -> ConversationContext {
        let intent = mq.query.intent;
        // The one reach outside the node: a read of the knowledge base, keyed by
        // intent. `kb-read` has no writer, so this is the whole of its authority.
        let knowledge = kb_read::lookup(intent_key(intent));

        ConversationContext {
            intent,
            question: mq.query.question,
            knowledge,
        }
    }
}

export!(Node);
