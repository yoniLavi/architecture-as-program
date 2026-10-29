//! The library's readers as one component: `ReadTransactions`, `ReadScheduled`,
//! `ReadFile`, `ReadUserInfo`, `ReadBalance`, `ReadIban`.
//!
//!   Read* : (TaskRequest) -> Untrusted<…>  with DBHandle<scope, read>
//!
//! Its world imports exactly `kb-read`. Which collection it reads is the handle's
//! scope, bound by the host; the entry's name (a parameter) only shapes the value.

wit_bindgen::generate!({ path: "../../wit", world: "lib-read" });

use crate::aap::caps::kb_read;
use lib_common::{compact, json, params, parse, text, Value};

struct Node;

impl Guest for Node {
    fn run(params_json: String, _inputs: Vec<String>) -> Result<String, String> {
        let p = params(&params_json)?;
        let items = kb_read::lookup("");
        let first = items.first().cloned().unwrap_or_default();
        let value = match text(&p, "entry").as_str() {
            "ReadTransactions" | "ReadScheduled" => {
                Value::Array(items.iter().map(|s| parse(s)).collect::<Result<_, _>>()?)
            }
            "ReadFile" => json!({ "text": first }),
            "ReadIban" => json!({ "iban": first }),
            "ReadBalance" => json!({ "amount": parse(&first)? }),
            "ReadUserInfo" => parse(&first)?,
            other => return Err(format!("not a reader: {other:?}")),
        };
        Ok(compact(&value))
    }
}

export!(Node);
