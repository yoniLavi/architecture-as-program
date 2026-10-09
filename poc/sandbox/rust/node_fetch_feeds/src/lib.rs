//! `FetchFeeds` as a WASM **component**.
//!
//! Contract, from `graphs/feed-triage.json`:
//!   FetchFeeds : (SubscriptionList) -> Untrusted<FeedBatch>
//!     with HTTPClient<[allowlist]>
//!
//! The only component in the service whose world imports `http-client`, and it
//! imports nothing else: no model, no store. So what gets fetched is decided by
//! the subscription list this node is handed, and by nothing a model said —
//! there is no model in here to say it, and no path from one to here.
//!
//! The allowlist is not visible from inside. This body can ask for any URL; a
//! request for a host the graph did not name is refused at the crossing, as a
//! trap. A *permitted* fetch that fails — a timeout, an error status, a response
//! over the size cap — comes back as a value, so one dead feed is recorded and
//! the rest are still read.
//!
//! The output is `Untrusted<FeedBatch>`. That label is the graph's, declared on
//! this node; WIT carries the payload.

wit_bindgen::generate!({
    path: "../../wit",
    world: "fetch-feeds",
});

use crate::aap::caps::http_client;
use crate::aap::caps::types::{FeedDocument, FetchFailure};

struct Node;

impl Guest for Node {
    fn run(subscriptions: SubscriptionList) -> FeedBatch {
        let mut documents = Vec::new();
        let mut failures = Vec::new();
        for url in subscriptions.urls {
            // The one reach outside the node, once per subscription.
            match http_client::fetch(&url) {
                Ok(body) => documents.push(FeedDocument { url, body }),
                Err(error) => failures.push(FetchFailure { url, error }),
            }
        }
        FeedBatch {
            documents,
            failures,
        }
    }
}

export!(Node);
