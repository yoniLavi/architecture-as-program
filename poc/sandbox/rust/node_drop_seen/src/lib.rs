//! `DropSeen` as a WASM **component**.
//!
//! Contract, from `graphs/feed-triage.json`:
//!   DropSeen : (List<Untrusted<FeedItem>>) -> List<Untrusted<FeedItem>>
//!     with StateHandle<'seen', read>
//!
//! Its world imports exactly `state-read`: it can ask whether an item's id has
//! been recorded and cannot record one. Deciding which items are new confers no
//! way to change which items are new — that authority is `RecordSeen`'s alone,
//! and it runs last.
//!
//! The items are untrusted and stay untrusted: this node keeps or drops each
//! whole and reads nothing of it but its id, which the parser computed.

wit_bindgen::generate!({
    path: "../../wit",
    world: "drop-seen",
});

use crate::aap::caps::state_read;

struct Node;

impl Guest for Node {
    fn run(items: Vec<FeedItem>) -> Vec<FeedItem> {
        let mut fresh: Vec<FeedItem> = Vec::new();
        for item in items {
            // Each id once, and only if no earlier run recorded it.
            if fresh.iter().any(|kept| kept.id == item.id) {
                continue;
            }
            if state_read::get(&item.id).is_some() {
                continue;
            }
            fresh.push(item);
        }
        fresh
    }
}

export!(Node);
