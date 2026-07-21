//! `SendReply` as a WASM **component** — the identity-routing case.
//!
//! Contract, unchanged from the graph:
//!   SendReply : (AgentResponse) -> DeliveryConfirmation
//!     with ResponseChannel<user-session>
//!
//! Its world imports exactly `response-channel`, a write-only sink, and nothing
//! else. There is no `read`/`history` function, so a node that can reply cannot
//! read the channel back.
//!
//! What makes this node worth regenerating is *identity*. The host satisfies the
//! single `send` crossing with a closure over the specific channel instance the
//! parent routed — in the composed platform, `CustomerSupport`'s `customer_session`
//! rather than a sibling's. The `delivery-confirmation` that returns carries that
//! instance's session identity, which the guest never held as data: routing to a
//! named instance is thus observable across the WIT boundary, not just at assembly.

wit_bindgen::generate!({
    path: "../../wit",
    world: "send-reply",
});

// `agent-response` and `delivery-confirmation` are re-exported at the crate root
// by the world's `use types.{...}`.
use crate::aap::caps::response_channel;

struct Node;

impl Guest for Node {
    fn run(reply: AgentResponse) -> DeliveryConfirmation {
        // The one reach outside the node: hand the reply text to the write-only
        // channel and return the confirmation it stamps with its own identity.
        response_channel::send(&reply.text)
    }
}

export!(Node);
