//! `PublishDigest` as a WASM **component**.
//!
//! Contract, from `graphs/feed-triage.json`:
//!   PublishDigest : (Digest) -> PublishedDigest  with Notifier<'digest'>
//!
//! The service's one outward act is the one function this world imports:
//! `notifier.notify`. Where a notification goes — a dated file on this machine —
//! is the host's binding, not something this body can see or choose.
//!
//! The digest is rendered to Markdown here. Every field is flattened to one line
//! first, and square brackets are replaced, so an item's text cannot start a
//! heading or a list of its own or close the link it sits in. That keeps the
//! digest's *structure* the node's; what the lines *say* is still derived from
//! untrusted text, and nothing here makes it true.

wit_bindgen::generate!({
    path: "../../wit",
    world: "publish-digest",
});

use crate::aap::caps::notifier;
use crate::aap::caps::types::{Category, Importance, ItemVerdict};

fn category_name(category: Category) -> &'static str {
    match category {
        Category::Release => "release",
        Category::Security => "security",
        Category::Research => "research",
        Category::Tooling => "tooling",
        Category::Discussion => "discussion",
        Category::Other => "other",
    }
}

/// A field as it may appear inside a Markdown line: one line, and unable to
/// close the link it sits in.
fn plain(text: &str) -> String {
    text.split_whitespace()
        .collect::<Vec<_>>()
        .join(" ")
        .replace('[', "(")
        .replace(']', ")")
}

fn render(digest: &Digest) -> String {
    let mut lines: Vec<String> = vec![
        format!("# Feed digest — {}", digest.date),
        String::new(),
        plain(&digest.overview),
        String::new(),
    ];
    let sections = [
        ("Must read", Importance::MustRead),
        ("Worth a look", Importance::WorthALook),
    ];
    for (heading, importance) in sections {
        let chosen: Vec<&ItemVerdict> = digest
            .entries
            .iter()
            .filter(|e| e.importance == importance)
            .collect();
        if chosen.is_empty() {
            continue;
        }
        lines.push(format!("## {heading}"));
        lines.push(String::new());
        for entry in chosen {
            let mut title = plain(&entry.title);
            if title.is_empty() {
                title = "(untitled)".to_string();
            }
            let head = if entry.link.is_empty() {
                title
            } else {
                format!("[{title}]({})", entry.link)
            };
            lines.push(format!(
                "- {head} — {} ({})",
                plain(&entry.summary),
                category_name(entry.category)
            ));
        }
        lines.push(String::new());
    }
    format!("{}\n", lines.join("\n").trim_end())
}

struct Node;

impl Guest for Node {
    fn run(composed: Digest) -> PublishedDigest {
        // A quiet run publishes nothing and still reports what it considered.
        let published = if composed.entries.is_empty() {
            false
        } else {
            // The one reach outside the node.
            notifier::notify(&render(&composed));
            true
        };
        PublishedDigest {
            date: composed.date,
            considered: composed.considered,
            published,
        }
    }
}

export!(Node);
