# Tasks

## 0. Approval, and the standing check

- [x] 0.1 **The author approves this change** (16 November 2026: "go ahead", when it was
      proposed as the home for the two archived changes' leftovers). There are no open
      questions: the tasks are the ones the author approved there
- [x] 0.2 **Standing, every session: the recorder** (formerly 0.3 of
      `strengthen-generation-evidence`, first started 27 October 2026, 18:32 UTC). Check
      `pgrep -fl poc.feeds.archive`, and never start a second recorder. If none runs, start
      one with
      `uv run --group poc python -m poc.feeds.archive --record --every 1h >> var/archive-recorder.log 2>&1`.
      It lowers its own priority. Gaps between sessions are gaps in the archive, and are
      reported as such. This task is ticked because it is a habit, not a deliverable

## 1. Live operation

- [ ] 1.1 The author starts the service (launchd or cron, the author's act). Verify: a run
      record in `var/runs/` dated after the start, and `poc.serve --report` shows it
- [ ] 1.2 After two weeks of live ticks: an operations summary committed (failures by class,
      any trace anomalies), from a committed export through `poc.serve --report --export`.
      Verify: `make evaluation-feed` shows it under live operation, and apart from replays

## 2. Replays

- [ ] 2.1 When the author releases the 28 October hold: replay the whole archive on the stub
      (both tiers) and on each Claude model (confined tier only), at low priority, and commit
      the exports. A replay resumes after a usage-ceiling stop, and refuses to resume under
      another backend, tier or model. For example:
      `uv run --group poc python -m poc.serve --replay var --model haiku --tier confined`, then
      `--report --var var/replays/claude-confined-haiku --export poc/feeds/history/replays/claude-confined-haiku.json`.
      Verify: the exports exist, and `dist/evaluation-feed.md` reports them as replayed
      history, never as operation

## 3. Close

- [ ] 3.1 `docs/ROADMAP.md` and `AGENTS.md` updated with what operation and the replays
      found; `make build` and `make spec-check` pass; archive (no capability is created)
