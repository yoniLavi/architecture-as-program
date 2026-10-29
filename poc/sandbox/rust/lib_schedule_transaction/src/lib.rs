//! The library's `ScheduleTransaction`:
//!
//!   ScheduleTransaction : (StandingOrder) -> Receipt  with Payments<[payees], cap, recurring>
//!
//! Its world imports exactly `payments-recurring`: it can schedule, and it has no
//! function to send once.

wit_bindgen::generate!({ path: "../../wit", world: "lib-schedule-transaction" });

use crate::aap::caps::payments_recurring;
use lib_common::{order, receipt, text};

struct Node;

impl Guest for Node {
    fn run(_params: String, inputs: Vec<String>) -> Result<String, String> {
        let o = order(&inputs, "StandingOrder")?;
        let amount = o.get("amount").and_then(|v| v.as_f64()).unwrap_or_default();
        let recurring = o
            .get("recurring")
            .and_then(|v| v.as_bool())
            .unwrap_or_default();
        receipt(payments_recurring::schedule(
            &text(&o, "recipient"),
            amount,
            &text(&o, "subject"),
            &text(&o, "date"),
            recurring,
        ))
    }
}

export!(Node);
