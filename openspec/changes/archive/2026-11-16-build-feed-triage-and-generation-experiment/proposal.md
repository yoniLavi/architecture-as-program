# Build the feed-triage service and run the node-generation experiment

## Why

Paper 2 shows that graph-level capability analysis and confinement can be implemented. It does
not show that anyone can *build software this way*. Two of the thesis's load-bearing claims are
still untested at any useful scale, and §5 of Paper 2 records both:

- **Code as compiled artifact.** One node body was generated, uncontrolled and unmeasured. The
  claim that an agent writes node bodies from signatures and contracts, and that the
  architecture bounds what that code can reach, has no evidence behind it.
- **The model survives a real program.** Nine nodes, one domain, no state, no fan-in, no clock,
  driven by a test harness rather than by the world.

`docs/ROADMAP.md` names the cheapest way to attack both together: a small service someone
actually runs, with the generation experiment run on its nodes. This change builds that
service and runs the experiment as far as one change can, so that there is a working
artifact and measured numbers to show. It covers roadmap milestones M1–M4. M5, Paper 3 itself,
stays out of scope.

## What Changes

**The service (M1, M2).** A feed-triage service as a canonical graph, `graphs/feed-triage.json`,
of roughly 15–20 nodes. On a timer it fetches an allowlisted set of RSS/Atom feeds, drops items
already seen, and classifies and summarises each new item with an LLM. It then selects what
matters and writes one dated digest to a local file and HTML page. Nothing leaves the machine
except the allowlisted feed fetches.

It needs four things the runtime lacks today:
- **Node-local state as a capability:** `StateHandle<'name', read|read-write>`, a typed WIT
  interface backed by a host-side store. It adds no new language construct.
- **Real outbound HTTP:** the `HTTPClient` handle performs fetches, with the existing allowlist
  plus a size cap, a timeout, and no redirect that leaves the allowlist.
- **A driver:** `poc/serve.py` ticks the graph, either once (for cron or launchd) or in a loop.
- **Fan-in, in two restricted forms**, with the design settled deliberately in `design.md`
  rather than by accident:
  - *per-item map*: a sub-graph node applied to each element of a `List<T>`, each element in its
    own isolated run;
  - *positional join*: a node with several data inputs on named positions, run once all have
    arrived, whose output trust is bounded by the **meet** of its inputs.

  Merging streams of one type, which raises the order-sensitivity question, stays open.

The LLM nodes run through a new backend that calls `claude -p` on the author's existing
subscription. The deterministic stub remains the default for tests and CI, so no build or test
calls a model and none incurs a cost.

**The generation experiment (M3).** A harness gives `claude -p` only a node's signature,
contracts, type definitions, and the `aap:caps` WIT package. The model runs with no tools and no
access to the repository, which mechanises the isolation discipline. It must emit a Rust body
and the component's world. The existing pipeline then builds the component, holds its imports
against the set derived from the node's `with` clause, runs property tests derived from the
contract (the generative contract mode, built here), and runs the graph.

Every trial is recorded:
- **Arms:** an honest prompt and an adversarial prompt.
- **Controls:** the gate off, to show the gate does the work; and the hand-written bodies, to
  show the gate is not flaky.
- **Models:** Claude tiers (Haiku, Sonnet, Opus).
- **Measures:** first-try success, iterations to green, and the catch rate by interface. The
  report separates *no attempt* from *attempted and caught*, and separates an ungranted import
  (caught by the gate) from an ambient call, which is inert on `wasm32-unknown-unknown` and
  caught at run time.

One model family is a stated limit, not a hidden one.

**The adversarial evaluation (M4).** A corpus of hostile feed items: exfiltration
instructions, attempts to read other items, digest impersonation, attempts to write state,
oversized and malformed feeds, and XML entity attacks. It is run against the service on both
tiers and evaluated in AgentDojo's threat model beside CaMeL's defence. The result is pinned in
the build the way Paper 2's injection scenario is.

**Attenuation at the routing point.** A handle routed to a sub-graph is wrapped in a facade
limited to the child's declared scope, keeping the caretaker so revocation still reaches it.
This is **held until Paper 2 publishes**: it makes Paper 2's "checked, not enforced" an
understatement, so it lands together with Paper 2 version 1.1.

**A demo.** The inspector renders the feed-triage graph, the per-item map, and the join, and
links each day's digest. It gets a mention in Paper 3, never a section.

**Not in this change:** principal binding (a one-user service does not exercise it), Paper 3's
prose, general FRP combinators, stream merge, and any paid API call.

## Impact

- **Specs:**
  - `signal-graph-runtime`: state capability, real HTTP, driver, per-item map, positional join,
    routed-handle attenuation, the Claude CLI backend, the local digest notifier.
  - `trust-typing`: the join's output trust is bounded by the meet of its inputs; the map lifts
    trust per element.
  - `evaluation`: separate feed-triage and generation artifacts; Paper 2's figures unmoved.
  - New `feed-triage-service`: the service itself.
  - New `node-generation`: the experiment harness.
- **Code:**
  - `poc/` gains `serve.py`, `feeds.py`, a `generation/` package, new node bodies (Python and
    Rust), and WIT interfaces for state.
  - `scripts/graph_validator.py` gains the map and join rules.
  - `graphs/feed-triage.json` is new.
- **Paper 2 is unchanged by this change.** Its figures come from the existing `CORPUS`,
  `DERIVED_NODES` and tier table, and none of them moves. The toy's evidence goes to
  `dist/evaluation-feed.{md,json}` and `dist/generation.{md,json}`. The one change that would
  alter a Paper 2 claim (attenuation) is held, as above.
- **Operations:**
  - Runtime state, fetched feeds, and digests live under a gitignored `var/` in the repository.
  - Nothing is written outside the working directory. A launchd example is documented, not
    installed.
- **Cost:** none beyond the author's subscription. The `claude -p` calls stop if the session
  limit is reached, and the harness resumes from its recorded trials.
