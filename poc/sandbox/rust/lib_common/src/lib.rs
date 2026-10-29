//! What the banking library's components share: values as JSON, the closed record
//! check, `inN.path` resolution and template filling. The Python side is
//! `poc/agentdojo/library.py`; the two must agree on every value that crosses, and
//! the harness runs the oracle graphs on both tiers to hold them to it.
//!
//! An rlib, not a component: it imports nothing, so linking it adds no import.

pub use serde_json::{json, Map, Value};

/// JSON as both sides spell it: compact, keys sorted (serde_json's default map is
/// ordered; Python passes `sort_keys=True, separators=(",", ":")`).
pub fn compact(v: &Value) -> String {
    serde_json::to_string(v).unwrap_or_default()
}

pub fn parse(text: &str) -> Result<Value, String> {
    serde_json::from_str(text).map_err(|e| format!("not JSON: {e}"))
}

pub fn parse_inputs(inputs: &[String]) -> Result<Vec<Value>, String> {
    inputs.iter().map(|s| parse(s)).collect()
}

pub fn params(text: &str) -> Result<Map<String, Value>, String> {
    match parse(text)? {
        Value::Object(m) => Ok(m),
        _ => Err("params are not an object".into()),
    }
}

/// `value` as a record of exactly `schema`'s fields; a type ending in `?` is
/// optional, and `null` counts as absent.
pub fn check_record(
    value: &Value,
    schema: &[(String, String)],
    what: &str,
) -> Result<Map<String, Value>, String> {
    let obj = value
        .as_object()
        .ok_or_else(|| format!("{what} is not a record"))?;
    let mut extra: Vec<&String> = obj
        .keys()
        .filter(|k| !schema.iter().any(|(n, _)| n == *k))
        .collect();
    if !extra.is_empty() {
        extra.sort();
        return Err(format!("{what} has fields outside its schema: {extra:?}"));
    }
    let mut out = Map::new();
    for (name, ftype) in schema {
        let optional = ftype.ends_with('?');
        let base = ftype.trim_end_matches('?');
        match obj.get(name) {
            None | Some(Value::Null) => {
                if !optional {
                    return Err(format!("{what} is missing field {name:?}"));
                }
            }
            Some(v) => {
                let ok = match base {
                    "string" => v.is_string(),
                    "boolean" => v.is_boolean(),
                    _ => v.is_number(),
                };
                if !ok {
                    return Err(format!("{what} field {name:?} is {v}, not a {base}"));
                }
                out.insert(name.clone(), v.clone());
            }
        }
    }
    Ok(out)
}

pub fn schema(pairs: &[(&str, &str)]) -> Vec<(String, String)> {
    pairs
        .iter()
        .map(|(n, t)| (n.to_string(), t.to_string()))
        .collect()
}

fn is_path(text: &str) -> bool {
    let Some(rest) = text.strip_prefix("in") else {
        return false;
    };
    let mut parts = rest.split('.');
    let index = parts.next().unwrap_or("");
    if index.is_empty() || !index.chars().all(|c| c.is_ascii_digit()) {
        return false;
    }
    parts.all(|p| {
        let mut cs = p.chars();
        matches!(cs.next(), Some(c) if c.is_ascii_alphabetic() || c == '_')
            && cs.all(|c| c.is_ascii_alphanumeric() || c == '_')
    })
}

pub fn resolve(inputs: &[Value], path: &str) -> Result<Value, String> {
    if !is_path(path) {
        return Err(format!("not a path: {path:?}"));
    }
    let mut parts = path[2..].split('.');
    let index: usize = parts
        .next()
        .unwrap_or("0")
        .parse()
        .map_err(|_| "bad index")?;
    let mut value = inputs
        .get(index)
        .ok_or_else(|| format!("{path:?} names a missing input"))?;
    for part in parts {
        value = value
            .as_object()
            .and_then(|o| o.get(part))
            .ok_or_else(|| format!("{path:?} does not resolve: no field {part:?}"))?;
    }
    Ok(value.clone())
}

/// A value as a template shows it: a string raw, a whole float as an integer.
fn show(v: &Value) -> String {
    match v {
        Value::String(s) => s.clone(),
        Value::Number(n) => match n.as_f64() {
            Some(f) if n.is_f64() && f.fract() == 0.0 && f.abs() < 1e15 => format!("{}", f as i64),
            _ => n.to_string(),
        },
        other => compact(other),
    }
}

/// Fill `{inN.path}` placeholders; anything else in braces is left as written.
pub fn fill(template: &str, inputs: &[Value]) -> Result<String, String> {
    let mut out = String::new();
    let mut rest = template;
    while let Some(open) = rest.find('{') {
        out.push_str(&rest[..open]);
        let after = &rest[open + 1..];
        match after.find('}') {
            Some(close) if is_path(&after[..close]) => {
                out.push_str(&show(&resolve(inputs, &after[..close])?));
                rest = &after[close + 1..];
            }
            _ => {
                out.push('{');
                rest = after;
            }
        }
    }
    out.push_str(rest);
    Ok(out)
}

/// The record schemas the writers take (`RECORDS` in library.py).
pub fn record_schema(name: &str) -> Vec<(String, String)> {
    match name {
        "PaymentOrder" => schema(&[
            ("amount", "number"),
            ("date", "string"),
            ("recipient", "string"),
            ("subject", "string"),
        ]),
        "StandingOrder" => schema(&[
            ("amount", "number"),
            ("date", "string"),
            ("recipient", "string"),
            ("recurring", "boolean"),
            ("subject", "string"),
        ]),
        "OrderUpdate" => schema(&[
            ("amount", "number?"),
            ("date", "string?"),
            ("id", "number"),
            ("recipient", "string?"),
            ("recurring", "boolean?"),
            ("subject", "string?"),
        ]),
        _ => schema(&[
            ("city", "string?"),
            ("first_name", "string?"),
            ("last_name", "string?"),
            ("street", "string?"),
        ]),
    }
}

/// The one data input a writer takes, checked against its record.
pub fn order(inputs: &[String], record: &str) -> Result<Map<String, Value>, String> {
    let values = parse_inputs(inputs)?;
    let first = values.first().ok_or("no input")?;
    check_record(first, &record_schema(record), record)
}

pub fn text(m: &Map<String, Value>, key: &str) -> String {
    m.get(key)
        .and_then(Value::as_str)
        .unwrap_or_default()
        .to_string()
}

pub fn opt_text(m: &Map<String, Value>, key: &str) -> Option<String> {
    m.get(key).and_then(Value::as_str).map(str::to_string)
}

/// A tool's result, wrapped as the host-tier body wraps it.
pub fn receipt(result: Result<String, String>) -> Result<String, String> {
    let ok = result?;
    Ok(compact(
        &json!({ "result": parse(&ok).unwrap_or(Value::String(ok)) }),
    ))
}
