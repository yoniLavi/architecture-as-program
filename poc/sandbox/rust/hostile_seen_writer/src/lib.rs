//! A hostile `DropSeen`: the feed evaluation's second negative control.
//!
//! `DropSeen` is granted `StateHandle<'seen', read>`: it may ask whether an item
//! has been recorded, and nothing else. This body has the same signature and
//! wants more — it marks every item it is shown as seen, so that a feed could
//! bury its own items, or everyone else's, before they are ever triaged. To do
//! that it needs `put`, so its world imports `state-rw` beside the `state-read`
//! it was granted.
//!
//! The read-only mode of the graph type is the *absence* of that interface from
//! what the node's component may import. So the derivation rejects this
//! component for exactly `aap:caps/state-rw@0.1.0`, and a host that links only
//! `state-read` cannot instantiate it: no instruction of the loop below ever runs.

wit_bindgen::generate!({
    path: "../../wit",
    world: "hostile-seen-writer",
});

use crate::aap::caps::{state_read, state_rw};

struct Node;

impl Guest for Node {
    fn run(items: Vec<FeedItem>) -> Vec<FeedItem> {
        for item in &items {
            if state_read::get(&item.id).is_none() {
                // The write a read-only node must not be able to make.
                state_rw::put(&item.id, "buried");
            }
        }
        Vec::new()
    }
}

export!(Node);
