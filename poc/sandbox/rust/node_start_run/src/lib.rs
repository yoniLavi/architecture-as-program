//! `StartRun` as a WASM **component**.
//!
//! Contract, from `graphs/feed-triage.json`:
//!   StartRun : (Tick) -> RunInfo  with Clock
//!
//! The only node of the feed-triage service that observes the time. Its world
//! imports exactly `wasi:clocks/wall-clock@0.2.0` — the upstream WASI interface,
//! granted as a capability — and every later node that needs the date receives
//! it from here as data. A component that wanted the time and did not hold this
//! node's `with` clause would have no import to ask through.

wit_bindgen::generate!({
    path: "../../wit",
    world: "start-run",
    // The clock is a foreign-package interface (wasi:clocks, vendored under
    // wit/deps); wit-bindgen needs the opt-in to generate bindings for it.
    generate_all,
});

use crate::wasi::clocks::wall_clock;

/// `YYYY-MM-DD` (UTC) for a count of seconds since the epoch.
///
/// The civil-from-days algorithm: there is no date library in a component built
/// for `wasm32-unknown-unknown`, and linking one in would be a great deal of
/// code to format ten characters.
fn date_of(seconds: u64) -> String {
    let z = (seconds / 86_400) as i64 + 719_468;
    let era = z.div_euclid(146_097);
    let doe = z.rem_euclid(146_097);
    let yoe = (doe - doe / 1_460 + doe / 36_524 - doe / 146_096) / 365;
    let doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
    let mp = (5 * doy + 2) / 153;
    let day = doy - (153 * mp + 2) / 5 + 1;
    let month = if mp < 10 { mp + 3 } else { mp - 9 };
    let year = yoe + era * 400 + i64::from(month <= 2);
    format!("{year:04}-{month:02}-{day:02}")
}

struct Node;

impl Guest for Node {
    fn run(_tick: Tick) -> RunInfo {
        // The one reach outside the node: read the clock, once.
        let seconds = wall_clock::now().seconds;
        RunInfo {
            date: date_of(seconds),
            started: seconds,
        }
    }
}

export!(Node);
