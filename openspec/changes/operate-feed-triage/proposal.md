# Operating the feed-triage service: live ticks and model replays

> **Status: approved by the author, 16 November 2026** (task 0.1). It carries tasks that the
> author approved under two earlier changes, now archived. It adds no new work.

## Why

Two changes stayed open only for work that waits on time and on the author:
- `build-feed-triage-and-generation-experiment`: the author starts the service (8.1), then
  an operations summary two weeks later (8.3);
- `strengthen-generation-evidence`: the model replays of the feed archive (3.3), held by
  the author on 28 October 2026 "for a longer archive".

Everything else in both is built, and both were archived on 16 November 2026, so that
their capabilities reach `openspec/specs/`. Both leftovers run on the same archive and
driver, so this one change holds them, and the open changes stop multiplying.

The state on 16 November 2026:
- the service has never run live. The last run in `var/runs/` is from 9 October 2026;
- the recorder has run since 27 October 2026, 18:32 UTC. It records 5 of 5 feeds hourly,
  and `var/archive/` holds 323 snapshots;
- the stub replay over the first 21 ticks is done, and recorded in the archived change.

## What Changes

No code or behaviour changes. The tasks are:
- **the recorder as a standing check** (formerly `strengthen-generation-evidence` 0.3):
  each session confirms that one recorder runs, and never starts a second;
- **live operation** (formerly 8.1 and 8.3): the author starts the service, and an
  operations summary is committed two weeks later;
- **model replays** (formerly 3.3): when the author releases the hold, the stub replay is
  redone over the whole archive, the Claude models are replayed on the confined tier, and
  the exports are committed.

**Not in this change:**
- any spec change (`skip_specs`). The behaviour is already specified in
  `feed-triage-service` and `evaluation`;
- Paper 2 v1.1, which the author set aside on 16 November 2026;
- any paid spend. Replays run on the subscription, at low priority.

## Capabilities

### New Capabilities
None.

### Modified Capabilities
None.

## Impact

- **Records:** exports under `poc/feeds/history/`; `dist/evaluation-feed.md` through
  `make evaluation-feed`.
- **Docs:** `docs/ROADMAP.md` and `AGENTS.md`, whose pointers to the recorder's standing
  task move here.
- **End condition:** archived when 1.2 and 2.1 are done, or when the author drops either.
  It does not stay open indefinitely.
