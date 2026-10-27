"""Record what the subscribed feeds serve, without triaging it.

    uv run --group poc python -m poc.feeds.archive --record --once
    uv run --group poc python -m poc.feeds.archive --record --every 1h
    uv run --group poc python -m poc.feeds.archive --coverage

The service has hours of operating history, not weeks. Most of what a fortnight
of operation would show — items seen, triaged, kept; de-duplication across ticks;
the same history under another model or tier — does not need a fortnight of
*triage*. It needs a fortnight of *feeds*, which can then be replayed through the
service as many times as wanted (`poc/serve.py --replay`). This module records
them. It is the only part that must run in real time.

**What a recording tick does.** It fetches each subscribed feed through an
`HTTPClient` built from the graph's own allowlist — the same handle class, the
same allowlist check on every redirect hop, the same size cap and timeout — and
writes the raw body to `var/archive/<UTC timestamp>/<feed digest>.xml`. It calls
no model and parses nothing. A feed that fails is recorded as a failure, with its
reason, because a feed that failed at 03:00 is part of the history too.

**The index.** `var/archive/index.jsonl` holds one line per tick: when, and for
each feed whether it was fetched, how many bytes, and why not. Replay reads it;
the coverage summary reads it. A gap between two ticks — no recorder running —
is visible as a gap there, and is reported as one rather than smoothed over.

**Who runs it.** The working session, not the system: the author chose not to
install a launchd or cron job (27 October 2026). Each session that works on the
service starts the recorder in the background first. So the archive grows only
while a session runs, and the gaps between sessions are gaps in it.

**One at a time.** A recorder holds `var/archive/record.lock` (an `flock`, like
the driver's) for its life; a second exits with code 3 and records nothing.

It runs at low priority (`poc/polite.py`), like everything long-running here.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from itertools import pairwise
from pathlib import Path

from ..feed_nodes import SUBSCRIPTIONS_KEY
from ..graph import load_graph_dict
from ..handles import HTTPClient, WallTime, World
from ..polite import lower_priority
from ..serve import (
    DEFAULT_SUBSCRIPTIONS,
    EXIT_CONFIG,
    EXIT_LOCKED,
    EXIT_OK,
    GRAPH,
    VAR_DIR,
    ConfigError,
    Lock,
    LockHeld,
    _interval,
    allowlist,
    check_subscriptions,
)

LOCK_NAME = "record.lock"
INDEX_NAME = "index.jsonl"


def archive_dir(var_dir: Path) -> Path:
    return var_dir / "archive"


def feed_file(url: str) -> str:
    """The file a feed's body is archived under: a digest of its URL, so the name
    is stable across ticks and says nothing a path could misread."""
    return hashlib.sha256(url.encode()).hexdigest()[:16] + ".xml"


def tick_name(moment: WallTime) -> str:
    return datetime.fromtimestamp(moment.seconds, tz=UTC).strftime("%Y-%m-%dT%H%M%SZ")


def subscriptions(var_dir: Path, default: Sequence[str] = DEFAULT_SUBSCRIPTIONS) -> list[str]:
    """What the service is subscribed to: its subscriptions store if the driver
    has seeded one, else the defaults it would seed. Read only — seeding the store
    is the driver's act, not the recorder's."""
    store = World(state_dir=var_dir / "state").store("subscriptions")
    raw = store.get(SUBSCRIPTIONS_KEY)
    if raw is None:
        return list(default)
    return [u.strip() for u in raw.splitlines() if u.strip() and not u.strip().startswith("#")]


def _now() -> WallTime:
    ns = time.time_ns()
    return WallTime(seconds=ns // 1_000_000_000, nanoseconds=ns % 1_000_000_000)


@dataclass
class Recorder:
    """One recorder's setup. The defaults are the real service; tests override
    the directory, the graph's allowlist, the feeds and the clock."""

    var_dir: Path = VAR_DIR
    graph: dict | None = None
    feeds: Sequence[str] | None = None
    clock: object | None = None  # Callable[[], WallTime]; None reads the real clock
    live_http: bool = True

    def _graph(self) -> dict:
        return self.graph if self.graph is not None else load_graph_dict(GRAPH)

    def _feeds(self) -> list[str]:
        return list(self.feeds) if self.feeds is not None else subscriptions(self.var_dir)

    def now(self) -> WallTime:
        return self.clock() if self.clock is not None else _now()  # type: ignore[operator]

    def tick(self) -> dict:
        """Fetch every feed once and archive what came back. Returns the index
        entry, already appended."""
        graph = self._graph()
        feeds = self._feeds()
        check_subscriptions(feeds, graph)
        http = HTTPClient(allowlist(graph), live=self.live_http)
        moment = self.now()
        name = tick_name(moment)
        root = archive_dir(self.var_dir)
        directory = root / name
        directory.mkdir(parents=True, exist_ok=True)
        entries = []
        for url in feeds:
            result = http.fetch(url)
            if result.ok:
                path = directory / feed_file(url)
                path.write_text(result.body)
                entries.append(
                    {
                        "url": url,
                        "ok": True,
                        "file": path.name,
                        "bytes": len(result.body.encode()),
                    }
                )
            else:
                entries.append({"url": url, "ok": False, "error": result.error})
        entry = {
            "tick": name,
            "seconds": moment.seconds,
            "nanoseconds": moment.nanoseconds,
            "feeds": entries,
        }
        with (root / INDEX_NAME).open("a") as index:
            index.write(json.dumps(entry, ensure_ascii=False) + "\n")
        return entry


def read_index(var_dir: Path) -> list[dict]:
    """Every recorded tick, in time order. A line that does not parse (a recorder
    killed mid-write) is skipped: it names no tick a replay could read."""
    path = archive_dir(var_dir) / INDEX_NAME
    if not path.exists():
        return []
    ticks = []
    for line in path.read_text().splitlines():
        try:
            ticks.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return sorted(ticks, key=lambda t: (t["seconds"], t["nanoseconds"]))


def coverage(ticks: Iterable[dict], interval: float) -> dict:
    """The recorded span, and how much of it the recording covers.

    A tick is taken to cover the `interval` that follows it, up to the next tick.
    Any stretch between two ticks longer than 1.5 intervals is a gap, listed with
    its length. Coverage is what fraction of the span from the first tick to the
    last tick's interval had a tick in it."""
    times = [t["seconds"] for t in ticks]
    if not times:
        return {"ticks": 0, "span_hours": 0.0, "covered_fraction": 0.0, "gaps": []}
    gaps = []
    covered = 0.0
    for a, b in pairwise(times):
        step = b - a
        covered += min(step, interval)
        if step > 1.5 * interval:
            gaps.append(
                {
                    "from": datetime.fromtimestamp(a, tz=UTC).isoformat(),
                    "to": datetime.fromtimestamp(b, tz=UTC).isoformat(),
                    "hours": round(step / 3600, 2),
                }
            )
    covered += interval
    span = times[-1] - times[0] + interval
    return {
        "ticks": len(times),
        "first": datetime.fromtimestamp(times[0], tz=UTC).isoformat(),
        "last": datetime.fromtimestamp(times[-1], tz=UTC).isoformat(),
        "span_hours": round(span / 3600, 2),
        "covered_fraction": round(covered / span, 3),
        "gaps": gaps,
    }


def failures(ticks: Iterable[dict]) -> dict[str, dict[str, int]]:
    """url → {reason: count} over every recorded fetch that failed."""
    out: dict[str, dict[str, int]] = {}
    for tick in ticks:
        for feed in tick["feeds"]:
            if not feed["ok"]:
                reasons = out.setdefault(feed["url"], {})
                reasons[feed["error"]] = reasons.get(feed["error"], 0) + 1
    return out


def describe(entry: dict) -> str:
    fetched = sum(1 for f in entry["feeds"] if f["ok"])
    size = sum(f.get("bytes", 0) for f in entry["feeds"])
    failed = [f"{f['url']} ({f['error']})" for f in entry["feeds"] if not f["ok"]]
    line = f"[{entry['tick']}] recorded {fetched}/{len(entry['feeds'])} feeds, {size} bytes"
    return line + (f"; failed: {', '.join(failed)}" if failed else "")


def record(recorder: Recorder, interval: float | None, *, limit: int | None = None) -> int:
    """Record once (`interval` None) or on an interval, holding the lock
    throughout. A tick that raises is reported and the loop carries on."""
    try:
        with Lock(archive_dir(recorder.var_dir), LOCK_NAME):
            done = 0
            while True:
                try:
                    print(describe(recorder.tick()), flush=True)
                except ConfigError:
                    raise
                except Exception as e:  # a full disk, a bug: say so, try again next tick
                    print(f"recording tick failed: {type(e).__name__}: {e}", flush=True)
                done += 1
                if interval is None or (limit is not None and done >= limit):
                    return EXIT_OK
                time.sleep(interval)
    except LockHeld as e:
        print(f"error: {e}", file=sys.stderr)
        return EXIT_LOCKED
    except ConfigError as e:
        print(f"error: {e}", file=sys.stderr)
        return EXIT_CONFIG
    except KeyboardInterrupt:
        return EXIT_OK


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="poc.feeds.archive", description=__doc__.split("\n\n")[0])
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--record", action="store_true", help="fetch and archive the feeds")
    mode.add_argument("--coverage", action="store_true", help="summarise what has been recorded")
    parser.add_argument("--once", action="store_true", help="with --record: one tick, then exit")
    parser.add_argument(
        "--every", type=_interval, default=3600.0, metavar="INTERVAL", help="default 1h"
    )
    parser.add_argument("--var", type=Path, default=VAR_DIR)
    parser.add_argument("--no-nice", action="store_true", help="do not lower priority")
    parser.add_argument("--export", type=Path, help="with --coverage: also write it here")
    args = parser.parse_args(argv)

    if args.coverage:
        ticks = read_index(args.var)
        summary = {
            **coverage(ticks, args.every),
            "interval_hours": round(args.every / 3600, 3),
            "failures": failures(ticks),
        }
        text = json.dumps(summary, indent=2) + "\n"
        if args.export:
            args.export.parent.mkdir(parents=True, exist_ok=True)
            args.export.write_text(text)
        print(text, end="")
        return EXIT_OK

    lower_priority(not args.no_nice)
    return record(Recorder(var_dir=args.var), None if args.once else args.every)


if __name__ == "__main__":
    raise SystemExit(main())
