# The feed-triage service

A small service that runs on your own machine. On a timer it fetches a fixed list of
RSS and Atom feeds, drops the items it has already seen, asks a model to classify and
summarise each new one, and writes the items worth reading to a dated digest file. It
is the *useful toy* of `docs/ROADMAP.md`: the first graph in this repository driven by
the world rather than by a test.

It exists to test two claims the demonstrator paper left open — that the model
survives a real program, and that an agent can write node bodies the architecture
then bounds. This page is how to run it. What it shows is reported in
`dist/evaluation-feed.md` and `dist/generation.md`.

## Run it

```sh
uv sync --group poc                                    # once: wasmtime, for the confined tier
uv run --group poc python -m poc.serve --once          # one tick: fetch, triage, publish, exit
uv run --group poc python -m poc.serve --every 1h      # tick every hour until interrupted
uv run --group poc python -m poc.serve --report        # what the runs so far show
```

A tick that finds something writes `var/digests/<date>.md` and `var/digests/<date>.html`;
open the HTML page in a browser. A tick that finds nothing new writes no digest.

| Flag | Default | Meaning |
|---|---|---|
| `--backend claude\|stub` | `claude` | What answers the model calls: the local `claude` CLI, or the deterministic stub (no model, no cost — for trying the plumbing). |
| `--model` | `haiku` | Model alias passed to the CLI. |
| `--tier host\|confined` | `host` | Run the capability-holding nodes as Python, or as WASM components that import only the interfaces their `with` clause grants. |
| `--var DIR` | `var/` | Where the service keeps everything it writes. |

Exit codes: `0` the tick ran; `1` it failed (see `var/runs/<id>/error.txt`); `2` the
configuration is wrong; `3` another driver holds the lock; `4` the model backend's usage
window is exhausted — nothing is wrong, run again later.

## What it costs

No API key is used and none is needed. The `claude` backend calls the `claude` CLI you
are already logged into, in print mode, on your subscription. Each call is made with no
tools, no session, and none of your `CLAUDE.md`, memory, hooks or plugins
(`--tools "" --safe-mode --no-session-persistence`), in an empty directory under
`var/llm/` that is removed afterwards. An `ANTHROPIC_API_KEY` in the environment is
deliberately *not* passed through, since the CLI would bill it per token in preference
to the subscription.

A tick triages at most 20 items, each costing one or two short model calls, plus one
for the digest's opening. The CLI reports how much of each usage window is spent; once
any window reaches 90% the backend stops making calls and the tick ends with exit code
`4`. Items not yet triaged are not marked seen, so nothing is lost: the next tick picks
them up.

## The feeds, and the allowlist

A fresh `var/` is seeded with these subscriptions:

| Feed | Why |
|---|---|
| `https://simonwillison.net/atom/everything/` | LLM tooling and agent practice, frequent |
| `https://rss.arxiv.org/rss/cs.PL` | new programming-languages papers |
| `https://rss.arxiv.org/rss/cs.CR` | new security papers — high volume, so triage has work to do |
| `https://bytecodealliance.org/feed.xml` | WebAssembly and the component model |
| `https://lobste.rs/t/plt.rss` | programming-language discussion |

They were chosen on 9 October 2026 as a default the author can replace: two firehoses
where most items should be dropped, and three low-volume feeds where most should not.

The list lives in `var/state/subscriptions.json`, one URL per line under the key
`feeds`; edit that file to change it. **The service cannot change it**: the node that
reads the list holds `StateHandle<'subscriptions', read>`, and no node holds a writer.

Which *hosts* the service may contact is not in that file. It is in the graph, in the
type of the one capability that reaches the network:

```
HTTPClient<['simonwillison.net', 'rss.arxiv.org', 'bytecodealliance.org', 'lobste.rs']>
```

A subscription on any other host is refused before a run, with exit code `2`. To follow
a feed on a new host, add the host to that type in `graphs/feed-triage.json` (it appears
three times: in `parameters`, in `capabilities`, and on `FetchFeeds`). A redirect that
leaves the list is refused the same way as a direct request would be.

## What it writes, and where

Everything goes under `var/`, which is gitignored. Nothing is written anywhere else,
and the only network traffic is the feed fetches and the model backend.

```
var/state/subscriptions.json   the feed list (you edit this)
var/state/seen.json            item id → the date it was considered
var/digests/2026-10-09.md      the day's digest; later ticks the same day append to it
var/digests/2026-10-09.html    the same, as a page
var/runs/<timestamp>/run.json  what one tick did: counts, outcome, fetch failures
var/runs/<timestamp>/trace.json  the run's execution trace (poc/trace-schema.json)
var/serve.lock                 held while a driver runs
```

Deleting `var/` resets the service; it will treat every item as new.

## Running it on a schedule

`--every` keeps a process alive. To run a tick on a timer instead, use the system
scheduler with `--once`. Neither of the examples below is installed by anything in this
repository; installing one is your act.

**cron** (hourly, at a quarter past):

```cron
15 * * * * cd /path/to/architecture-as-program && /path/to/uv run --group poc python -m poc.serve --once >> var/cron.log 2>&1
```

**launchd** (macOS). Save as `~/Library/LaunchAgents/org.example.feed-triage.plist`, with
both paths replaced, then `launchctl load` it:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>             <string>org.example.feed-triage</string>
  <key>WorkingDirectory</key>  <string>/path/to/architecture-as-program</string>
  <key>ProgramArguments</key>
  <array>
    <string>/path/to/uv</string>
    <string>run</string> <string>--group</string> <string>poc</string>
    <string>python</string> <string>-m</string> <string>poc.serve</string>
    <string>--once</string>
  </array>
  <key>StartInterval</key>     <integer>3600</integer>
  <key>StandardOutPath</key>   <string>/path/to/architecture-as-program/var/launchd.log</string>
  <key>StandardErrorPath</key> <string>/path/to/architecture-as-program/var/launchd.log</string>
</dict>
</plist>
```

A scheduled tick needs the `claude` CLI on its `PATH` and logged in for the same user.
Two drivers cannot run at once: the second exits with code `3` and does nothing.

## The graph

`graphs/feed-triage.json` (eleven nodes) and `graphs/triage-item.json` (three), rendered
to `dist/graphs/` by `make build`.

```
StartRun ─▶ LoadSubscriptions ─▶ FetchFeeds ─▶ ParseFeeds ─▶ DropSeen ─▶ LimitBatch ─▶ TriageItem (each) ─▶ SelectItems ─┐
  Clock      StateHandle<          HTTPClient<    (pure)       StateHandle<   (pure)       LLMClient<           (pure)         │
   │         'subscriptions',      [allowlist]>                'seen', read>               inference>                          ▼
   │          read>                                                                                                     ComposeDigest ─▶ PublishDigest ─▶ RecordSeen
   └────────────────────────────────────── RunInfo ──────────────────────────────────────────────────────────────────▶  LLMClient<       Notifier<        StateHandle<
                                                                                                                         inference>       'digest'>        'seen', read-write>

TriageItem, run once per item:
  Untrusted<FeedItem> ─▶ ClassifyItem ─┬─ keep ─▶ SummariseItem ─▶ ItemVerdict
                         LLMClient<    │          LLMClient<inference>
                         inference>    └─ drop ─▶ SkipItem ──────▶ ItemVerdict
                         discharges trust          (pure)
```

Four things about that shape are the security argument, and each is asserted in
`tests/test_poc_feed_triage.py` rather than only drawn here:

- **One node holds outbound HTTP, and no model is upstream of it.** Nothing a model says
  can become a URL that is fetched. An item that says *fetch `evil.example/?d=…`* has no
  wiring to travel on.
- **Each item is triaged in a run of its own.** `TriageItem` is a per-item map: the
  runtime runs the child graph once per item, and no node inside it receives a second.
  An instruction in one item cannot read another.
- **No model holds a tool.** Every `LLMClient` here is `inference`: a node can be
  *misled* by an item and has nothing to act with.
- **Only the last node can mark an item seen.** `DropSeen` reads the store; only
  `RecordSeen` holds the writer, and it runs after the digest is published. A tick that
  fails anywhere records nothing, and the next one considers the same items again.

What the shape does **not** give: a truthful digest. An item's text reaches the models
that classify, summarise and introduce it, and an item written to mislead them can make
the digest say something false, or get itself listed as a must-read. That is the same
free-text residual the demonstrator paper reports, and the hostile-feed evaluation
measures it rather than assuming it away.

Three limits of the service as built, stated here because a reader running it will meet
them:

- **The reader's interests are fixed in a node body.** `ClassifyItem`'s prompt names
  them; changing them means editing `poc/feed_nodes.py` (and the Rust body, on the
  confined tier). They are not a setting, because no data path carries a setting there.
- **A feed the parser refuses contributes nothing, quietly.** A feed that declares a
  `DOCTYPE` is refused whole (that is the defence against entity-expansion attacks); it
  shows up in a run's counts as zero items, not as an error.
- **A model call that keeps failing blocks its batch.** One element's failure fails the
  tick, and since nothing is recorded, the same item is tried again next time. A
  transient failure heals itself; a permanent one would need the item's id added to
  `var/state/seen.json` by hand.
