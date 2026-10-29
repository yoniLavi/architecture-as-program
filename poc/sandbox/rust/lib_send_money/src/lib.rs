//! The library's `SendMoney`:
//!
//!   SendMoney : (PaymentOrder) -> Receipt  with Payments<[payees], cap>
//!
//! Its world imports exactly `payments`, whose one function sends once. The payee
//! list and the cap live in the handle the host binds, and a payment outside them
//! traps at the crossing before the bank's tool runs.

wit_bindgen::generate!({ path: "../../wit", world: "lib-send-money" });

use crate::aap::caps::payments;
use lib_common::{order, receipt, text};

struct Node;

impl Guest for Node {
    fn run(_params: String, inputs: Vec<String>) -> Result<String, String> {
        let o = order(&inputs, "PaymentOrder")?;
        let amount = o.get("amount").and_then(|v| v.as_f64()).unwrap_or_default();
        receipt(payments::send(
            &text(&o, "recipient"),
            amount,
            &text(&o, "subject"),
            &text(&o, "date"),
        ))
    }
}

export!(Node);
