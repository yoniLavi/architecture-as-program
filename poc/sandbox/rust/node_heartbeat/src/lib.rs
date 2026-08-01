//! `Heartbeat` as a WASM **component** — the I/O-vocabulary demonstrator.
//!
//! Contract, ahead of the feed-triage graph that will use these kinds for real:
//!   Heartbeat : (FeedRef) -> HeartbeatReport
//!     with Clock, HTTPClient<[...]>, Notifier<'...'>
//!
//! Its world imports exactly three interfaces, and the first is the interesting
//! one: `wasi:clocks/wall-clock@0.2.0`, the *upstream* WASI interface, granted
//! deliberately. Every other component in this tier demonstrates the absence of
//! that import; this one demonstrates the same derivation machinery granting it —
//! a `with` clause visibly buying an authority the artifact otherwise lacks, and
//! a WASI interface granted as a capability like any other.
//!
//! The HTTP allowlist is not visible from in here, which is the design: the
//! interface carries the operation, the handle behind it carries the scope. This
//! body can ask for any URL; whether the fetch happens is decided at the
//! crossing, exactly as an out-of-scope tool call is.

wit_bindgen::generate!({
    path: "../../wit",
    world: "heartbeat",
    // The clock is a *foreign-package* interface (wasi:clocks, vendored under
    // wit/deps), and wit-bindgen requires an explicit opt-in to generate guest
    // bindings for a package it does not own. That opt-in is the honest cost of
    // granting the real WASI interface instead of a bespoke look-alike.
    generate_all,
});

use crate::aap::caps::{http_client, notifier};
use crate::wasi::clocks::wall_clock;

struct Node;

impl Guest for Node {
    fn run(feed_url: String) -> HeartbeatReport {
        // The three reaches outside the node, one per granted interface: read
        // the clock, perform the one permitted fetch, report what happened.
        let stamp = wall_clock::now();
        let body = http_client::get(&feed_url);
        let fetched = body.chars().count() as u32;
        let notified = notifier::notify(&format!(
            "fetched {fetched} chars from {feed_url} at t={}s",
            stamp.seconds
        ));
        HeartbeatReport {
            seconds: stamp.seconds,
            fetched,
            notified,
        }
    }
}

export!(Node);
