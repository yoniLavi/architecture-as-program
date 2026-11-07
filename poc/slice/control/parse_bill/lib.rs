//! The control body for `ParseBill` (task 3.1): find the IBAN and the total due in a
//! bill's text. It holds no capability, so its world imports nothing.

wit_bindgen::generate!({
    path: "wit",
    world: "node",
    generate_all,
});

struct Node;

fn amount(line: &str) -> Option<f64> {
    line.split_whitespace().last()?.parse().ok()
}

impl Guest for Node {
    fn run(_params: String, inputs: Vec<String>) -> Result<String, String> {
        let value: serde_json::Value =
            serde_json::from_str(inputs.first().ok_or("no input")?).map_err(|e| e.to_string())?;
        // The bill may carry its tabs and newlines escaped.
        let text = value
            .get("text")
            .and_then(|t| t.as_str())
            .ok_or("the input has no text")?
            .replace("\\t", " ")
            .replace("\\n", "\n");
        let iban = text
            .split("IBAN:")
            .nth(1)
            .and_then(|rest| rest.split_whitespace().next())
            .ok_or("the bill names no IBAN")?;
        let total = text
            .lines()
            .filter(|l| l.trim_start().starts_with("Total"))
            .filter_map(amount)
            .last()
            .ok_or("the bill states no total")?;
        Ok(serde_json::json!({"iban": iban, "amount": total}).to_string())
    }
}

export!(Node);
