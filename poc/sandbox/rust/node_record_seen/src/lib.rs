//! `RecordSeen` as a WASM **component**.
//!
//! Contract, from `graphs/feed-triage.json`:
//!   RecordSeen : (PublishedDigest) -> RunReport
//!     with StateHandle<'seen', read-write>
//!     ensures recorded >= 0
//!
//! The only component in the service whose world imports `state-rw`, so the only
//! node that can mark an item seen — and the last to run. If anything upstream
//! fails, this never executes, nothing is recorded, and the next run considers
//! the same items again. The ordering is the graph's, not a convention in here.
//!
//! What it writes are item ids, which the parser computed as digests: no string
//! a feed chose is ever used as a key.

wit_bindgen::generate!({
    path: "../../wit",
    world: "record-seen",
});

use crate::aap::caps::state_rw;

struct Node;

impl Guest for Node {
    fn run(published: PublishedDigest) -> RunReport {
        for id in &published.considered {
            // The node's reach outside itself: one write per considered item.
            state_rw::put(id, &published.date);
        }
        RunReport {
            recorded: published.considered.len() as u32,
            date: published.date,
        }
    }
}

export!(Node);
