# Tasks

Phases are ordered so that stopping at any boundary leaves something runnable and something
measured. Each phase ends green (`make build`) and committed.

**As built (9 October 2026).** The author delegated the open decisions for this run ("follow
your preferences"). Three departures from the order below, each noted at its task:
fan-in (3.1, 3.2) was built before the graph, so `feed-triage.json` was written once in its
full form (1.7 and 3.5 together) rather than as a skeleton with throwaway nodes; the feed list
(1.10) was chosen by the implementer and is replaceable; and the model backend adds
`--safe-mode` and `--system-prompt` to the command the design gave (1.5).

## 0. Keep Paper 2 still

- [x] 0.1 Test that pins every key of `dist/evaluation.json` that Paper 2 interpolates to its
      value at the start of this change; a slip fails the build (removed deliberately at
      Paper 2 v1.1)
- [x] 0.2 `var/` gitignored; `var/README` explaining what lives there

## 1. Walking skeleton (M1): one feed, one item, one digest

- [x] 1.1 `StateHandle<'name', read|read-write>`: type grammar, provisioning, assignability
      (read-write narrows to read; names match), JSON-file store under `var/state/` with atomic
      replace; tests
- [ ] 1.2 WIT interfaces `state-read` and `state-rw` in `caps.wit`; the derivation maps them;
      host linking; tests (the Paper 2 derivation rows unchanged — task 0.1 guards it)
- [x] 1.3 `HTTPClient` real fetch: urllib GET, 5 MiB cap, 15 s timeout, redirects only to
      allowlisted hosts, http(s) only; canned mode stays the default; tests with a local
      fixture server (no network in tests)
- [x] 1.4 Local digest `Notifier`: dated Markdown and HTML under `var/digests/`; tests
- [x] 1.5 `ClaudeCLIBackend` in `poc/llm.py` (`claude -p --tools "" --no-session-persistence
      --output-format json`, cwd a temp dir under `var/`); unit tests use a fake executable,
      never the real CLI
      - *As built:* the command also passes `--safe-mode` and `--system-prompt`. A directory
        under `var/` is inside the repository, so without `--safe-mode` the CLI discovers the
        repository's `CLAUDE.md` (and the user's memory, hooks and plugins) and hands them to a
        model meant to see only its prompt. The backend also scrubs `ANTHROPIC_*`/`CLAUDE*`
        from the child's environment and stops at a usage ceiling (90% of any window).
- [x] 1.6 Feed parsing (`poc/feeds.py`): RSS 2.0 and Atom, entity expansion disabled, size and
      item-count limits; tests including billion-laughs and external-entity inputs
      - *As built:* a package, `poc/feeds/`, so that the hostile corpus of 6.1 can live at
        `poc/feeds/corpus/` as that task names it.
- [x] 1.7 `graphs/feed-triage.json`, skeleton form: Tick → FetchFeeds → ParseFeeds → DropSeen →
      a single-item summarise → PublishDigest → RecordSeen; validator accepts it; diagram and
      listing generate
      - *As built:* written once, in the full form of 3.5 (fan-in was built first). Eleven
        nodes plus the three of `graphs/triage-item.json` — fourteen, under the proposal's
        "roughly 15–20". `Clock` sits on a new entry node, `StartRun`, rather than on
        `FetchFeeds`, so the run's date reaches `ComposeDigest` as data through the join;
        `DropSeen` holds the seen-store *read-only* (the design sketch gave it read-write),
        leaving `RecordSeen` the only writer.
- [x] 1.8 `poc/serve.py --once` / `--every`: lock file, run directory with trace, exit codes;
      tests on the stub backend and the fixture server
- [x] 1.9 `docs/FEED-TRIAGE.md`: how to run it, the feed list and allowlist, the launchd example
      (documented, not installed)
- [x] 1.10 Author checkpoint: the author names the feed list (design open question 1)
      - *As built:* the author declined to choose ("whichever ones you think would be useful").
        The implementer chose five feeds on four hosts (`docs/FEED-TRIAGE.md`): two high-volume
        arXiv listings where most items should be dropped, three low-volume blogs where most
        should not. They are a default in `poc/serve.py`, seeded into `var/` and editable there.

## 2. Generation pilot on the six existing ported nodes (M3, first half)

The roadmap's recommendation: answer "does the gate ever fire on generated code?" before the
toy is built around the answer.

- [ ] 2.1 Generative contract mode: `contracts.strategy(...)` from the closed vocabulary, seeded
      stdlib `random`; discard inputs violating `requires`; tests that each form generates its
      boundary cases
- [ ] 2.2 Contracts attached in the graph for the subject nodes (in a copy used by the harness,
      so `graphs/customer-support.json` and Paper 2 stay unchanged)
- [ ] 2.3 `poc/generation/`: task builder (signature, contracts, types, the whole `aap:caps`
      package, the grant statement, a crate skeleton); prompts for the honest and adversarial
      arms committed as files
- [ ] 2.4 Generator: `claude -p --model <tier> --tools ""` in an empty temp dir; reply parsing
      into `world.wit` + `lib.rs`; failure class `format`
- [ ] 2.5 Pipeline: build, component, gate (`gate:<iface>`, `gate-under:<iface>`), ambient scan
      (`ambient-attempt:<module>`), contract property tests, graph run; feedback loop up to 4
      iterations
- [ ] 2.6 Recording and resume: `poc/generation/runs/<run-id>/` per trial, `results.json`
      derived; the harness skips recorded trials
- [ ] 2.7 Controls: gate-off re-evaluation of the same components; hand-written bodies through
      the pipeline (expected zero violations, pinned)
- [ ] 2.8 Pilot run: 6 nodes × 2 arms × 3 tiers × N=5; commit runs and results
- [ ] 2.9 `poc/generation/report.py` → `dist/generation.{md,json}`: first-try success, iterations,
      catch rate by interface, no-attempt vs attempted-and-caught, ambient attempts, gate-off
      ship count; one-family limit in the first paragraph; build step reads committed results only
- [ ] 2.10 Author checkpoint: pilot numbers reviewed; decide N for phase 5

## 3. Fan-in (M2)

- [x] 3.1 Per-item map: `"each": true` on a sub-graph node; validator checks element-wise
      (`List<T>` in, `List<U>` out against the child's boundary); runtime runs one isolated
      child per element in order; tests including an empty list and a failing element
- [x] 3.2 Positional join: `"to_input"` on edges; validator requires one edge per position and
      rejects a join whose positions lie on exclusive branches; runtime runs it once all
      positions arrive and refuses a run ending with a join waiting; tests
- [ ] 3.3 The trust meet, exercised: a join with one `Untrusted<_>` input among clean ones must
      emit an untrusted output unless it is a declared discharger; corpus cases in
      `FEED_CORPUS` pinned to the trust lattice
- [ ] 3.4 Mutations for the new rules in `FEED_CORPUS` (unported join position, exclusive-branch
      join, map with a mismatched child boundary, map laundering trust past the child), each
      pinned to its reason class with isolation enforced
- [x] 3.5 `graphs/feed-triage.json` full form: `TriageEach` over `TriageItem`, `SelectItems`,
      `ComposeDigest` joining selected items with the run's metadata; validator, diagrams

## 4. The confined tier for the toy

- [ ] 4.1 Rust bodies for the toy's capability-holding leaf nodes (`FetchFeeds`, `DropSeen`,
      `ClassifyItem`, `SummariseItem`, `ComposeDigest`, `PublishDigest`, `RecordSeen`), hand-written
      — the hand-written control for phase 5
- [ ] 4.2 Feed derivation rows in `dist/evaluation-feed.json` (separate from Paper 2's): each
      component held against its clause, plus a negative control
- [ ] 4.3 Tier table rows for the toy (`dist/evaluation-feed.json`): host escapes recorded,
      confined denials discriminating
- [ ] 4.4 Tier-equality test for the toy's traces

## 5. Full generation experiment on the toy (M3, second half)

- [ ] 5.1 Run the harness over the toy's subject nodes at the N chosen in 2.10; commit runs
- [ ] 5.2 Report regenerated; compare pilot and toy results; state where they differ
- [ ] 5.3 A generated body that passes everything replaces the hand-written one in a live run,
      recorded (interchangeability shown on the graph that runs, not only in a test)

## 6. Adversarial evaluation (M4)

- [ ] 6.1 Hostile feed corpus under `poc/feeds/corpus/`: exfiltration instruction, cross-item
      read request, digest impersonation, state-write request, oversized feed, malformed XML,
      entity expansion, external entity; each with the outcome it must produce
- [ ] 6.2 Harness: run the service against the corpus through the fixture server, on the stub
      backend with a deterministic fooled model, on both tiers; pinned in the build; results
      in `dist/evaluation-feed.json`
- [ ] 6.3 A recorded live run of the corpus on the Claude backend (not in the build; committed
      with its date and model), reporting what the digest said
- [ ] 6.4 Write-up positioned against AgentDojo's threat model and CaMeL's defence: what is
      structurally impossible here (exfiltration, cross-item reads), what is bounded by scope,
      and the residual (a misleading digest), stated plainly

## 7. Demo

- [ ] 7.1 Inspector renders `feed-triage.json`, the per-item map (drill-down to one item's run),
      and the join; e2e checks; screenshots regenerated
- [ ] 7.2 The inspector links the latest local digest; the hostile-corpus walkthrough mirrors
      6.4's language

## 8. Live operation

- [ ] 8.1 The author starts the service (launchd or cron, the author's act)
- [ ] 8.2 `poc/serve.py --report`: runs, failures, items seen, digests written, model calls,
      drawn from `var/runs/`; summarised into `dist/evaluation-feed.md` from a committed export
- [ ] 8.3 After two weeks: an operations summary committed (failures by class, any trace
      anomalies)

## 9. Attenuation at the routing point (held until Paper 2 publishes)

- [ ] 9.1 Facade wrapping each routed handle to the child's declared scope; caretaker kept so
      revocation reaches it; tests that a child cannot use the parent's wider allowlist, tool
      set, mode or store
- [ ] 9.2 Paper 2 v1.1: the routed-scope qualifier dropped where it no longer holds; task 0.1's
      pin updated deliberately; hedge pins checked

## 10. Records

- [ ] 10.1 `docs/ROADMAP.md` "Start here" updated per phase; M1–M4 rows marked
- [ ] 10.2 `AGENTS.md` tooling section: state, real HTTP, driver, map, join, CLI backend,
      generation harness; test count
- [ ] 10.3 Spec deltas reconciled with what was built; `openspec validate --strict`
