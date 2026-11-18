//! S3's pure cores. Each is the decision logic of a shipped node body
//! (`poc/sandbox/rust/<node>/src/lib.rs`), rewritten so Aeneas can translate it to
//! Lean, with every host result taken as an argument (or through a trait the
//! theorem quantifies over) and every effect returned as data.
//!
//! The shipped bodies are not changed. `tests/differential.rs` holds each core to a
//! verbatim copy of the shipped logic on generated inputs, which is the link from
//! what is proved to what runs (the translation's fidelity is checked separately,
//! in Lean, by evaluating the extracted functions on the same inputs).
//!
//! Text is `Vec<u32>` of Unicode scalar values: the contract vocabulary's `len` is
//! Python's, which counts code points, and Aeneas has no model of `str`'s methods.

// ── DropSeen ────────────────────────────────────────────────────────
//
// Shipped: keep each item whose id is new to this batch and not recorded by an
// earlier run. Ids are interned to u64 by the shell.

pub fn contains(xs: &Vec<u64>, x: u64) -> bool {
    let mut found = false;
    let mut i = 0;
    while i < xs.len() {
        if xs[i] == x {
            found = true;
        }
        i += 1;
    }
    found
}

/// The ids to keep, in input order: each once, and none that `recorded` holds.
pub fn drop_seen(items: &Vec<u64>, recorded: &Vec<u64>) -> Vec<u64> {
    let mut fresh: Vec<u64> = Vec::new();
    let mut i = 0;
    while i < items.len() {
        let id = items[i];
        if !contains(&fresh, id) && !contains(recorded, id) {
            fresh.push(id);
        }
        i += 1;
    }
    fresh
}

// ── SummariseItem's summary ─────────────────────────────────────────
//
// Shipped: `one_line(reply, 400)` = `split_whitespace().join(" ").chars().take(400)`
// applied to the model's reply. The contract: `len(summary) <= 400`, for every reply.

/// `char::is_whitespace`: the Unicode White_Space property, spelled out.
pub fn is_space(c: u32) -> bool {
    (c >= 0x09 && c <= 0x0D)
        || c == 0x20
        || c == 0x85
        || c == 0xA0
        || c == 0x1680
        || (c >= 0x2000 && c <= 0x200A)
        || c == 0x2028
        || c == 0x2029
        || c == 0x202F
        || c == 0x205F
        || c == 0x3000
}

/// Words joined by single spaces, then the first `limit` code points.
pub fn one_line(text: &Vec<u32>, limit: usize) -> Vec<u32> {
    let mut out: Vec<u32> = Vec::new();
    let mut pending_space = false;
    let mut i = 0;
    while i < text.len() {
        let c = text[i];
        if is_space(c) {
            if out.len() > 0 {
                pending_space = true;
            }
        } else {
            if pending_space {
                out.push(0x20);
                pending_space = false;
            }
            out.push(c);
        }
        i += 1;
    }
    truncate(&out, limit)
}

pub fn truncate(xs: &Vec<u32>, limit: usize) -> Vec<u32> {
    let mut out: Vec<u32> = Vec::new();
    let mut i = 0;
    while i < xs.len() && i < limit {
        out.push(xs[i]);
        i += 1;
    }
    out
}

// ── GenerateResponse's tool loop ────────────────────────────────────
//
// Shipped: up to MAX_ROUNDS model calls; a call for the granted tool is answered
// from the knowledge base and the loop goes on; any other tool ends the run with
// an error; a text reply ends it with that text. The model and the knowledge base
// are the host's: here they are a trait, so a theorem about `respond` holds for
// every implementation, that is, for every model, however it adapts.

pub const MAX_ROUNDS: usize = 3;

pub enum Reply {
    Text(Vec<u32>),
    Call(Vec<u32>, Vec<u32>), // tool, query
}

pub enum Outcome {
    Ok(Vec<u32>),
    ToolRefused(Vec<u32>),
}

/// One crossing, as data: what the shell will have done, in order.
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum Effect {
    Generate,
    Lookup,
}

pub trait Host {
    /// `tool-llm.generate`, given what the knowledge base last returned (or nothing).
    fn generate(&mut self, round: usize) -> Reply;
    /// `kb-read.lookup`.
    fn lookup(&mut self, query: &Vec<u32>) -> Vec<u32>;
}

pub fn same(a: &Vec<u32>, b: &Vec<u32>) -> bool {
    if a.len() != b.len() {
        return false;
    }
    let mut eq = true;
    let mut i = 0;
    while i < a.len() {
        if a[i] != b[i] {
            eq = false;
        }
        i += 1;
    }
    eq
}

/// The loop, with every crossing logged. `granted` is the one tool the node's
/// clause grants (`lookup`).
pub fn respond<H: Host>(host: &mut H, granted: &Vec<u32>) -> (Outcome, Vec<Effect>) {
    let mut log: Vec<Effect> = Vec::new();
    let mut round = 0;
    let mut outcome = Outcome::Ok(Vec::new());
    let mut done = false;
    while round < MAX_ROUNDS && !done {
        log.push(Effect::Generate);
        match host.generate(round) {
            Reply::Text(text) => {
                outcome = Outcome::Ok(text);
                done = true;
            }
            Reply::Call(tool, query) => {
                if !same(&tool, granted) {
                    outcome = Outcome::ToolRefused(tool);
                    done = true;
                } else {
                    log.push(Effect::Lookup);
                    let _hits = host.lookup(&query);
                }
            }
        }
        round += 1;
    }
    (outcome, log)
}
