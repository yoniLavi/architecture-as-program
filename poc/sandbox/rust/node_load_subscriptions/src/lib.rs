//! `LoadSubscriptions` as a WASM **component**.
//!
//! Contract, from `graphs/feed-triage.json`:
//!   LoadSubscriptions : (RunInfo) -> SubscriptionList
//!     with StateHandle<'subscriptions', read>
//!
//! Its world imports exactly `state-read`. That interface has `get` and nothing
//! else — no `put`, no way to list keys — so the service can read the feed list
//! its reader maintains and cannot subscribe itself to anything. Which store the
//! `get` reaches is not visible from in here: the name lives in the handle the
//! host binds, as an HTTP allowlist does.

wit_bindgen::generate!({
    path: "../../wit",
    world: "load-subscriptions",
});

use crate::aap::caps::state_read;

/// The key of the subscriptions store that holds the feed list, one URL a line.
const SUBSCRIPTIONS_KEY: &str = "feeds";

struct Node;

impl Guest for Node {
    fn run(_info: RunInfo) -> SubscriptionList {
        // The one reach outside the node: a read of the subscriptions store.
        let raw = state_read::get(SUBSCRIPTIONS_KEY).unwrap_or_default();
        let urls = raw
            .lines()
            .map(str::trim)
            .filter(|line| !line.is_empty() && !line.starts_with('#'))
            .map(String::from)
            .collect();
        SubscriptionList { urls }
    }
}

export!(Node);
