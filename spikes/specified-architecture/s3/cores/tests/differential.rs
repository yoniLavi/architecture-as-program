//! Each core against a verbatim copy of the shipped body's logic, on generated
//! inputs. A disagreement means the core proves something about a different
//! function from the one that runs. No dependencies: a fixed-seed xorshift.

use cores::*;

struct Rng(u64);
impl Rng {
    fn next(&mut self) -> u64 {
        self.0 ^= self.0 << 13;
        self.0 ^= self.0 >> 7;
        self.0 ^= self.0 << 17;
        self.0
    }
    fn below(&mut self, n: u64) -> u64 {
        self.next() % n
    }
}

// ── DropSeen: poc/sandbox/rust/node_drop_seen/src/lib.rs, ids for items ──

fn shipped_drop_seen(items: Vec<u64>, recorded: &[u64]) -> Vec<u64> {
    let mut fresh: Vec<u64> = Vec::new();
    for item in items {
        if fresh.iter().any(|kept| *kept == item) {
            continue;
        }
        if recorded.contains(&item) {
            continue;
        }
        fresh.push(item);
    }
    fresh
}

#[test]
fn drop_seen_agrees() {
    let mut r = Rng(0x5eed_0001);
    for _ in 0..20_000 {
        let items: Vec<u64> = (0..r.below(12)).map(|_| r.below(8)).collect();
        let recorded: Vec<u64> = (0..r.below(6)).map(|_| r.below(8)).collect();
        assert_eq!(drop_seen(&items, &recorded), shipped_drop_seen(items.clone(), &recorded));
    }
}

// ── SummariseItem: poc/sandbox/rust/node_summarise_item/src/lib.rs ──

fn shipped_one_line(text: &str, limit: usize) -> String {
    text.split_whitespace()
        .collect::<Vec<_>>()
        .join(" ")
        .chars()
        .take(limit)
        .collect()
}

const ALPHABET: &[char] = &[
    'a', 'b', 'Z', '.', ' ', ' ', '\n', '\t', '\r', '\u{0B}', '\u{0C}', '\u{85}', '\u{A0}',
    '\u{1680}', '\u{2000}', '\u{200A}', '\u{2028}', '\u{2029}', '\u{202F}', '\u{205F}',
    '\u{3000}', '\u{200B}', '\u{FEFF}', 'é', '日', '🙂',
];

#[test]
fn is_space_is_char_is_whitespace() {
    for c in (0u32..=0x10FFFF).filter_map(char::from_u32) {
        assert_eq!(is_space(c as u32), c.is_whitespace(), "{:?}", c);
    }
}

#[test]
fn one_line_agrees() {
    let mut r = Rng(0x5eed_0002);
    for _ in 0..20_000 {
        let s: String = (0..r.below(40)).map(|_| ALPHABET[r.below(ALPHABET.len() as u64) as usize]).collect();
        let limit = r.below(30) as usize;
        let cps: Vec<u32> = s.chars().map(|c| c as u32).collect();
        let want: Vec<u32> = shipped_one_line(&s, limit).chars().map(|c| c as u32).collect();
        assert_eq!(one_line(&cps, limit), want, "{s:?} {limit}");
    }
}

// ── GenerateResponse: poc/sandbox/rust/node_generate_response/src/lib.rs ──

#[derive(Clone)]
enum Script {
    Text,
    Call(bool), // granted tool?
}

struct Scripted {
    script: Vec<Script>,
    calls: Vec<Effect>,
}

impl Host for Scripted {
    fn generate(&mut self, round: usize) -> Reply {
        self.calls.push(Effect::Generate);
        match self.script.get(round).cloned().unwrap_or(Script::Text) {
            Script::Text => Reply::Text(vec![round as u32]),
            Script::Call(true) => Reply::Call(word("lookup"), vec![]),
            Script::Call(false) => Reply::Call(word("exfiltrate"), vec![]),
        }
    }
    fn lookup(&mut self, _q: &Vec<u32>) -> Vec<u32> {
        self.calls.push(Effect::Lookup);
        vec![]
    }
}

fn word(s: &str) -> Vec<u32> {
    s.chars().map(|c| c as u32).collect()
}

/// The shipped loop's shape, verbatim in control flow; strings elided.
fn shipped_respond(script: &[Script]) -> (Result<u32, ()>, Vec<Effect>) {
    let mut calls = Vec::new();
    for round in 0..MAX_ROUNDS {
        calls.push(Effect::Generate);
        match script.get(round).cloned().unwrap_or(Script::Text) {
            Script::Text => return (Ok(round as u32), calls),
            Script::Call(granted) => {
                if !granted {
                    return (Err(()), calls);
                }
                calls.push(Effect::Lookup);
            }
        }
    }
    (Ok(u32::MAX), calls)
}

#[test]
fn respond_agrees_and_logs_exactly_the_crossings() {
    let options = [Script::Text, Script::Call(true), Script::Call(false)];
    for a in 0..3 {
        for b in 0..3 {
            for c in 0..3 {
                for d in 0..3 {
                    let script = vec![
                        options[a].clone(),
                        options[b].clone(),
                        options[c].clone(),
                        options[d].clone(),
                    ];
                    let mut host = Scripted { script: script.clone(), calls: vec![] };
                    let (outcome, log) = respond(&mut host, &word("lookup"));
                    let (want, want_calls) = shipped_respond(&script);
                    assert_eq!(log, want_calls);
                    assert_eq!(host.calls, log, "the log is the crossings the host saw");
                    match (outcome, want) {
                        (Outcome::Ok(t), Ok(r)) if r == u32::MAX => assert!(t.is_empty()),
                        (Outcome::Ok(t), Ok(r)) => assert_eq!(t, vec![r]),
                        (Outcome::ToolRefused(_), Err(())) => {}
                        _ => panic!("outcomes differ for script {a}{b}{c}{d}"),
                    }
                }
            }
        }
    }
}
