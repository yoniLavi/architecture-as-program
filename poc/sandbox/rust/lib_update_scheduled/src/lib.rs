//! The library's `UpdateScheduledTransaction`:
//!
//!   UpdateScheduledTransaction : (OrderUpdate) -> Receipt
//!     with ScheduledPayments<[orders], [fields]>
//!
//! Its world imports exactly `scheduled-payments`. Which orders and which of
//! their fields it may change is the handle's scope, checked at the crossing
//! against the order the bank holds under that id.

wit_bindgen::generate!({ path: "../../wit", world: "lib-update-scheduled" });

use crate::aap::caps::scheduled_payments;
use lib_common::{opt_text, order, receipt};

struct Node;

impl Guest for Node {
    fn run(_params: String, inputs: Vec<String>) -> Result<String, String> {
        let o = order(&inputs, "OrderUpdate")?;
        let id = o.get("id").and_then(|v| v.as_f64()).unwrap_or(-1.0);
        if id < 0.0 || id.fract() != 0.0 || id > u32::MAX as f64 {
            return Err(format!("order id {id} is not a non-negative integer"));
        }
        receipt(scheduled_payments::update(
            id as u32,
            opt_text(&o, "recipient").as_deref(),
            o.get("amount").and_then(|v| v.as_f64()),
            opt_text(&o, "subject").as_deref(),
            opt_text(&o, "date").as_deref(),
            o.get("recurring").and_then(|v| v.as_bool()),
        ))
    }
}

export!(Node);
