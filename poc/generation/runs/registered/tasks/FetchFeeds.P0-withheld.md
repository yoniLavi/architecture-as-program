You are implementing the body of one node of a signal graph, as a Rust crate compiled to a WebAssembly component. The target is `wasm32-unknown-unknown` with wit-bindgen 0.59 and no WASI adapter.

## The node

```
FetchFeeds : (SubscriptionList) -> Untrusted<FeedBatch>
  with HTTPClient<['simonwillison.net', 'rss.arxiv.org', 'bytecodealliance.org', 'lobste.rs']>
```

It declares no contract beyond its types.

This node uses these interfaces:

- `aap:caps/http-client@0.1.0`

The component must export exactly this function:

```wit
export run: func(subscriptions: subscription-list) -> feed-batch;
```

## What to return

Return two files, each in its own fenced code block, in this order:

1. `wit/world.wit`, in a ```wit block. It declares `package gen:node;` and one world named `node`, containing the `use` of the types the export names, an `import` for each interface the body calls, and the export above. Name interfaces in full: `import aap:caps/inference-llm@0.1.0;`, `use aap:caps/types@0.1.0.{raw-message};`.
2. `src/lib.rs`, in a ```rust block: the complete source of the crate.

Anything outside those two blocks is ignored.

## The crate you are completing

`Cargo.toml` is fixed, and you cannot add dependencies:

```toml
[package]
name = "generated_node"
version = "0.1.0"
edition = "2021"

[lib]
crate-type = ["cdylib"]

[dependencies]
wit-bindgen = "0.59"

[profile.release]
opt-level = "s"
lto = true
panic = "abort"
strip = true

[workspace]
```

`src/lib.rs` starts from this skeleton:

```rust
wit_bindgen::generate!({
    path: "wit",
    world: "node",
    generate_all,
});

struct Node;

impl Guest for Node {
    // fn run(...) -> ... { ... }
}

export!(Node);
```

How wit-bindgen names things: a type named in your world's `use` is generated at the crate root; any other type of the package is at `crate::aap::caps::types::`. An imported interface such as `aap:caps/kb-read` is the module `crate::aap::caps::kb_read`. Kebab-case WIT names become CamelCase types and variant cases, and snake_case functions and fields. A WIT `string` parameter of an imported function is `&str` in Rust; a returned `string` is `String`; `list<T>` is `Vec<T>`; `option<T>` is `Option<T>`; `result<T, E>` is `Result<T, E>`.

## The Rust types your signature names

As wit-bindgen generates them:

```rust
pub struct SubscriptionList {
    pub urls: Vec<String>,
}

pub struct FeedBatch {
    pub documents: Vec<FeedDocument>,
    pub failures: Vec<FetchFailure>,
}

pub struct FeedDocument {
    pub url: String,
    pub body: String,
}

pub struct FetchFailure {
    pub url: String,
    pub error: String,
}
```

## The `aap:caps` WIT package

Present in the crate at `wit/deps/caps/caps.wit`:

```wit
package aap:caps@0.1.0;

/// Domain types that cross node boundaries in the CustomerSupport graph.
///
/// These mirror `poc/values.py` and the type strings in `graphs/customer-support.json`.
/// They are shared by the worlds below rather than redeclared per node, so a
/// producer and a consumer of `customer-query` cannot disagree about its shape.
interface types {
    /// The closed intent set. A WIT `enum` has no "other" case: this is the
    /// graph's "adversarial text cannot widen the intent set" property, enforced
    /// by the type rather than by a check in the node body.
    enum intent {
        billing-question,
        technical-support,
        account-change,
        general-inquiry,
        unknown,
    }

    /// Untrusted<RawMessage> — the boundary input. The `untrusted` taint is a
    /// graph-level (validator) property; WIT carries the payload, not the label.
    record raw-message {
        text: string,
    }

    /// CustomerQuery — what ParseMessage emits once trust is discharged.
    record customer-query {
        intent: intent,
        entities: list<string>,
        question: string,
    }

    /// ModeratedQuery — a CustomerQuery that has passed content moderation. The
    /// distinct type records, at the type level, that moderation has occurred;
    /// FetchContext accepts only this, so a wiring that skips moderation is
    /// ill-typed. The wrapper carries the query and nothing more.
    record moderated-query {
        query: customer-query,
    }

    /// PolicyViolation — ModerateContent's `violation` branch.
    record policy-violation {
        reason: string,
    }

    /// EscalationRequest — ModerateContent's `escalation` branch.
    record escalation-request {
        query: customer-query,
        reason: string,
    }

    /// The three-way sum ModerateContent emits, with the same role labels the
    /// graph's variant edges route on (`ok`, `violation`, `escalation`). As with
    /// `response-result`, the case names are the routing ports by construction.
    variant moderation-result {
        ok(moderated-query),
        violation(policy-violation),
        escalation(escalation-request),
    }

    /// ConversationContext — what the tool-capable node receives. Note what is
    /// absent: no raw message, no untrusted text field beyond the bounded
    /// question. The type is the attenuation.
    record conversation-context {
        intent: intent,
        question: string,
        knowledge: list<string>,
    }

    record agent-response {
        text: string,
    }

    record llm-error {
        message: string,
    }

    /// DeliveryConfirmation — what a reply node returns once the response channel
    /// has accepted a message. The `session-id` is the channel's identity, known to
    /// the host that provisioned the handle, not to the guest: the confined reply
    /// node receives it back across the boundary rather than fabricating it, which
    /// is how identity routing survives the WIT crossing (the send lands on exactly
    /// the instance the parent routed).
    record delivery-confirmation {
        session: string,
        delivered: bool,
    }

    /// The sum type `ok: AgentResponse | error: LLMError` from the graph, with
    /// the same role labels. The runtime routes on the case name, so the graph's
    /// variant edges (`GenerateResponse.ok`, `GenerateResponse.error`) and this
    /// variant's cases are the same names by construction.
    variant response-result {
        ok(agent-response),
        error(llm-error),
    }

    /// Reported by the hostile-node suite: did an attempted escape succeed?
    record escape-verdict {
        escaped: bool,
        detail: string,
    }

    /// What the heartbeat demonstrator returns: the time it read, how many
    /// characters its one permitted fetch returned, and whether the notification
    /// was accepted. Exists to exercise all three I/O capability kinds in one
    /// confined body ahead of the feed-triage graph that will use them for real.
    record heartbeat-report {
        seconds: u64,
        fetched: u32,
        notified: bool,
    }

    /// The boundary input: one firing of the driver's timer.
    record tick {
        reason: string,
    }

    /// What the run knows about itself: the date it publishes under and the
    /// instant it began, both read from the clock by the one node that holds it.
    record run-info {
        date: string,
        started: u64,
    }

    record subscription-list {
        urls: list<string>,
    }

    /// One fetched feed, unparsed: the URL asked for and the body that came back.
    record feed-document {
        url: string,
        body: string,
    }

    /// A feed that could not be fetched this run. Carried as data so one dead
    /// feed does not fail the tick, and so the run record says which.
    record fetch-failure {
        url: string,
        error: string,
    }

    /// Untrusted<FeedBatch> — everything the outside world sent this run.
    record feed-batch {
        documents: list<feed-document>,
        failures: list<fetch-failure>,
    }

    /// Untrusted<FeedItem> — one entry of one feed. `id` is a digest computed by
    /// the parser, never a string the feed chose, so it is safe as a store key.
    /// Every text field is bounded by the parser and is still adversarial data.
    record feed-item {
        id: string,
        feed: string,
        title: string,
        link: string,
        published: string,
        text: string,
    }

    /// The closed category set. As with `intent`: a feed item cannot talk the
    /// classifier into a seventh category, because there is no value for one.
    enum category {
        release,
        security,
        research,
        tooling,
        discussion,
        other,
    }

    /// The closed importance set the selection sorts on.
    enum importance {
        must-read,
        worth-a-look,
        skip,
    }

    /// ClassifiedItem — an item the classifier kept, with trust discharged. The
    /// item's text rides along: the free-text residual, bounded and still
    /// adversarial, exactly as `customer-query.question` is.
    record classified-item {
        item: feed-item,
        category: category,
        importance: importance,
    }

    /// DroppedItem — an item the classifier judged not worth a summary.
    record dropped-item {
        item: feed-item,
        category: category,
    }

    /// `keep: ClassifiedItem | drop: DroppedItem`, with the graph's role labels.
    variant classification {
        keep(classified-item),
        drop(dropped-item),
    }

    /// ItemVerdict — what one item's child run hands back to the parent.
    record item-verdict {
        id: string,
        feed: string,
        title: string,
        link: string,
        category: category,
        importance: importance,
        summary: string,
        kept: bool,
    }

    /// Selection — the items that made the digest, plus the id of every item
    /// considered, kept or not, so that all of them can be marked seen.
    record selection {
        entries: list<item-verdict>,
        considered: list<string>,
    }

    record digest {
        date: string,
        overview: string,
        entries: list<item-verdict>,
        considered: list<string>,
    }

    record published-digest {
        date: string,
        considered: list<string>,
        published: bool,
    }

    record run-report {
        date: string,
        recorded: u32,
    }
}

/// `LLMClient<inference>` — model access with no tool calling.
///
/// The attenuation is structural: this interface offers exactly one function,
/// and it returns a string. There is no tool-call case to receive and no tool
/// interface to invoke, so a node holding only this cannot act on what the model
/// says — only be influenced by it.
interface inference-llm {
    /// Ask the model. `system` is the instruction, `prompt` the material, and
    /// `task` a one-word label for the kind of request (`classify`, `moderate`,
    /// `triage`, `summarise`, `digest`): a hint a backend may route on, with no
    /// effect on what the node is permitted to do.
    infer: func(system: string, prompt: string, task: string) -> string;
}

/// `LLMClient<[lookup]>` — model access plus exactly the tools in the scope.
///
/// On the core-wasm tier a tool call came back as the tagged string
/// `"C" FS tool FS query` and the node body parsed it. Here it is a typed
/// `variant`: the host either returns text or a structured `tool-request`, and a
/// malformed third possibility is not representable.
interface tool-llm {
    /// A tool the model asked to invoke. Whether the node *can* invoke it is a
    /// separate question, answered by which tool interfaces are in its world.
    record tool-request {
        tool: string,
        query: string,
    }

    /// One round of the tool-orchestration loop: the model either answers, or
    /// asks for a tool.
    variant reply {
        text(string),
        call(tool-request),
    }

    generate: func(system: string, prompt: string) -> reply;
}

/// `DBHandle<'knowledge-base', read>` — read-only, scoped to one store.
///
/// There is no `write` function in the interface, so a node holding this handle
/// has no import through which to mutate the store. The read-only mode of the
/// graph type is the absence of a function, not a runtime permission check.
/// Returns a typed `list<string>` — the core-wasm tier returned 0x1E-joined text.
interface kb-read {
    lookup: func(query: string) -> list<string>;
}

/// `ResponseChannel<user-session>` — write-only sink for replies to one session.
///
/// `send` returns a `delivery-confirmation` rather than a bare bool: the host
/// channel knows its own session identity and stamps it on the confirmation, so a
/// confined reply node reports *which* session it delivered to without ever holding
/// that identity as data. There is no `read`/`history` function — the channel is
/// write-only, as the graph type says.
interface response-channel {
    use types.{delivery-confirmation};

    send: func(text: string) -> delivery-confirmation;
}

/// `EventEmitter<'support-queue'>` — write-only sink for one topic. As above:
/// defined here, held only by host-tier nodes (EscalateToHuman) so far.
interface event-emitter {
    emit: func(payload: string) -> bool;
}

/// `HTTPClient<[host, ...]>` — outbound HTTP, scoped to an allowlist of hosts.
///
/// The *interface* carries the operation; the *allowlist* lives in the handle the
/// host binds behind it, exactly as `LLMClient<[lookup]>`'s tool scope lives in
/// its handle. A confined node can therefore ask for any URL, and a request whose
/// host is outside the handle's allowlist is refused at the crossing — the same
/// shape as an out-of-scope tool call. This is the first capability kind whose
/// scope is a *set* rather than a mode or a name, which is what makes its
/// narrowing rule (superset may stand in for subset, never the reverse) worth
/// having.
interface http-client {
    /// Fetch a URL. Refusal (host outside the allowlist) is a trap at the
    /// boundary, not a value — a node cannot probe its own allowlist by
    /// collecting error strings.
    get: func(url: string) -> string;

    /// Fetch a URL, with a *transport* failure returned as a value: a timeout,
    /// an error status, a response over the size cap. A node reading several
    /// feeds survives one being down. A request outside the allowlist is still a
    /// trap, here as in `get` — that is not a failed fetch but a reach for
    /// authority the node was not granted, and it must not be collectable.
    fetch: func(url: string) -> result<string, string>;
}

/// `StateHandle<'name', read>` — look a key up in one named store.
///
/// The read-only mode is, as with `kb-read`, the absence of a function: there is
/// no `put` here, so a node holding this cannot change what the next run sees.
/// There is no way to list keys either — a node can ask about a key it already
/// knows, not enumerate the store.
interface state-read {
    get: func(key: string) -> option<string>;
}

/// `StateHandle<'name', read-write>` — read and change one named store.
///
/// A separate interface rather than `state-read` plus a writer, so that the
/// derivation maps one capability type to one interface and a node's mode is
/// readable off its import list.
interface state-rw {
    get: func(key: string) -> option<string>;
    put: func(key: string, value: string);
    delete: func(key: string);
}

/// `Notifier<'channel'>` — write-only sink for notifications to one channel.
/// The outbound side of the feed-triage toy: the simplest of the three kinds,
/// structurally a sibling of `event-emitter`.
interface notifier {
    notify: func(message: string) -> bool;
}
```

## The `wasi:clocks` WIT package

Present in the crate at `wit/deps/clocks/wall-clock.wit`:

```wit
package wasi:clocks@0.2.0;

interface wall-clock {
    record datetime {
        seconds: u64,
        nanoseconds: u32,
    }

    now: func() -> datetime;

    resolution: func() -> datetime;
}
```
