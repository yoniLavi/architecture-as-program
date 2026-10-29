//! The library's `Respond`:
//!
//!   Respond : (…) -> DeliveryConfirmation  with ResponseChannel<session>
//!
//! Its world imports exactly `response-channel`, a write-only sink. It fills its
//! template's `{inN.path}` placeholders from its inputs and sends the result as the
//! final answer.

wit_bindgen::generate!({ path: "../../wit", world: "lib-respond" });

use crate::aap::caps::response_channel;
use lib_common::{compact, fill, json, params, parse_inputs, text};

struct Node;

impl Guest for Node {
    fn run(params_json: String, inputs: Vec<String>) -> Result<String, String> {
        let p = params(&params_json)?;
        let answer = fill(&text(&p, "template"), &parse_inputs(&inputs)?)?;
        let confirmation = response_channel::send(&answer);
        Ok(compact(
            &json!({ "session": confirmation.session, "delivered": confirmation.delivered }),
        ))
    }
}

export!(Node);
