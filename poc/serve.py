"""The driver: run the feed-triage graph once, or on an interval.

Until now every graph in this repository was driven by a test. This module is
what drives one from the world instead: a timer fires, the graph runs against
real feeds and a real model, and a digest appears on disk. It is deliberately
thin. It assembles `graphs/feed-triage.json` with a `World` rooted at `var/`,
executes one `Tick`, and writes down what happened — nothing about fetching,
triaging or publishing lives here, because all of that is the graph.

    uv run --group poc python -m poc.serve --once            # one tick, then exit
    uv run --group poc python -m poc.serve --every 1h        # tick on an interval
    uv run --group poc python -m poc.serve --report          # what the runs so far show

What the driver holds that no node does: the authority to *set up* the world. It
seeds the subscriptions store on first run, it chooses which backend answers
`LLMClient<inference>`, and it owns the lock. Those are an operator's decisions,
made outside the graph, and they are the whole of what is.

Everything written goes under `var/` (gitignored): state stores, digests, one
directory per run with its trace, and the lock. Nothing is written elsewhere, and
the only network traffic is the allowlisted feed fetches and the model backend.

Exit codes: 0 the tick ran; 1 it failed; 2 the configuration is wrong (a
subscription outside the graph's allowlist); 3 another driver holds the lock;
4 the model backend's usage window is exhausted — stop, and run again later.
"""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import sys
import time
import traceback
from collections.abc import Iterable, Mapping
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit

from type_parser import TApp, TList, TString, parse_type

from . import digest, feed_policy
from .feed_nodes import SUBSCRIPTIONS_KEY
from .feed_values import Tick
from .graph import REPO_ROOT, AssemblyError, assemble, load_graph_dict
from .handles import WallTime, World
from .llm import ClaudeCLIBackend, LLMBackend, StubLLM, UsageLimitReached
from .runtime import ExecutionResult, execute

VAR_DIR = REPO_ROOT / "var"
GRAPH = "feed-triage"
CHILD_GRAPH = "triage-item"

EXIT_OK = 0
EXIT_FAILED = 1
EXIT_CONFIG = 2
EXIT_LOCKED = 3
EXIT_USAGE_LIMIT = 4

# The feeds a fresh `var/` is seeded with. The graph's `HTTPClient` allowlist is
# the set of their hosts: changing this list means changing that type, in
# `graphs/feed-triage.json`, which is the point — what the service may reach is
# written in the graph, and a subscription outside it is refused before a run.
DEFAULT_SUBSCRIPTIONS: tuple[str, ...] = (
    "https://simonwillison.net/atom/everything/",
    "https://rss.arxiv.org/rss/cs.PL",
    "https://rss.arxiv.org/rss/cs.CR",
    "https://bytecodealliance.org/feed.xml",
    "https://lobste.rs/t/plt.rss",
)

# The nodes with a component port, by graph: what `--tier confined` runs as WASM.
# The pure nodes (`ParseFeeds`, `LimitBatch`, `SelectItems`, `SkipItem`) hold no
# capability and stay on the host tier.
CONFINED_NODES: dict[str, tuple[str, ...]] = {
    "FeedTriage": (
        "StartRun",
        "LoadSubscriptions",
        "FetchFeeds",
        "DropSeen",
        "ComposeDigest",
        "PublishDigest",
        "RecordSeen",
    ),
    "TriageItem": ("ClassifyItem", "SummariseItem"),
}


class ConfigError(RuntimeError):
    """The service is set up in a way the graph does not permit."""


class LockHeld(RuntimeError):
    """Another driver is running against the same `var/`."""


# ── Configuration ──────────────────────────────────────────────────


@dataclass
class Config:
    """One driver's setup. The defaults are the real service; tests override the
    directory, the backend, the graph's allowlist and the clock."""

    var_dir: Path = VAR_DIR
    backend: LLMBackend = field(default_factory=ClaudeCLIBackend)
    live_http: bool = True
    # url → body, served instead of the network when `live_http` is false.
    web: Mapping[str, str] = field(default_factory=dict)
    confined: bool = False
    graph: dict = field(default_factory=lambda: load_graph_dict(GRAPH))
    # The per-item child graph `TriageItem`, as the runtime will resolve it.
    child: dict = field(default_factory=lambda: load_graph_dict(CHILD_GRAPH))
    subscriptions: tuple[str, ...] = DEFAULT_SUBSCRIPTIONS
    clock: object | None = None  # Callable[[], WallTime]; None reads the real clock
    # graph name → the nodes to run confined; overrides `confined` when given.
    sandbox: Mapping[str, Iterable[str]] | None = None
    # node name → a component file to run in place of that node's committed one.
    # How a generated body is put into a live run: the node's `with` clause, its
    # host bindings and everything around it stay exactly as they are, and only
    # the body changes. Confined-tier nodes only — a body is interchangeable
    # because it is a component with a fixed import set.
    substitute: Mapping[str, Path] = field(default_factory=dict)

    def now(self) -> WallTime:
        if self.clock is not None:
            return self.clock()  # type: ignore[operator]
        ns = time.time_ns()
        return WallTime(seconds=ns // 1_000_000_000, nanoseconds=ns % 1_000_000_000)

    def today(self) -> str:
        return datetime.fromtimestamp(self.now().seconds, tz=UTC).strftime("%Y-%m-%d")


def allowlist(graph: dict) -> frozenset[str]:
    """The hosts the graph's `HTTPClient` capability names."""
    hosts: set[str] = set()
    for cap in graph["capabilities"]:
        ast = parse_type(cap)
        if isinstance(ast, TApp) and ast.head == "HTTPClient" and ast.args:
            arg = ast.args[0]
            if isinstance(arg, TList):
                hosts |= {i.value for i in arg.items if isinstance(i, TString)}
    return frozenset(hosts)


def retarget(graph: dict, hosts: Iterable[str]) -> dict:
    """The same graph with its `HTTPClient` allowlist replaced by `hosts`.

    The allowlist is part of a capability *type*, so pointing the service at a
    different set of hosts — a fixture server in a test, the hostile corpus in the
    evaluation — is an edit to the graph, made here in one named place rather than
    by a backdoor in the handle. The canonical graph on disk is never rewritten."""
    new = "HTTPClient<[" + ", ".join(f"'{h}'" for h in sorted(hosts)) + "]>"
    text = json.dumps(graph)
    for cap in graph["capabilities"]:
        ast = parse_type(cap)
        if isinstance(ast, TApp) and ast.head == "HTTPClient":
            text = text.replace(json.dumps(cap)[1:-1], json.dumps(new)[1:-1])
    return json.loads(text)


def check_subscriptions(urls: Iterable[str], graph: dict) -> None:
    """Every subscription must be reachable under the graph's allowlist. Checked
    before a run, so a mistyped feed is a configuration error with a name on it
    rather than a capability refusal halfway through a tick."""
    allowed = allowlist(graph)
    outside = sorted(
        u for u in urls if (urlsplit(u).hostname or "").lower() not in {h.lower() for h in allowed}
    )
    if outside:
        raise ConfigError(
            f"subscription(s) outside the graph's HTTP allowlist {sorted(allowed)}: {outside}. "
            f"Reaching a new host means adding it to the HTTPClient type in graphs/{GRAPH}.json."
        )


# ── The lock ───────────────────────────────────────────────────────


class Lock:
    """An exclusive advisory lock on `var/serve.lock`, held for a driver's life.

    `flock`, not a pid file: the kernel releases it when the process dies, so a
    crashed driver cannot leave the service locked out of itself."""

    def __init__(self, var_dir: Path):
        self._path = var_dir / "serve.lock"
        self._fd: int | None = None

    def __enter__(self) -> Lock:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(self._path, os.O_RDWR | os.O_CREAT, 0o644)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as e:
            os.close(fd)
            raise LockHeld(f"another driver holds {self._path}") from e
        os.ftruncate(fd, 0)
        os.write(fd, f"{os.getpid()}\n".encode())
        self._fd = fd
        return self

    def __exit__(self, *_exc: object) -> None:
        if self._fd is not None:
            fcntl.flock(self._fd, fcntl.LOCK_UN)
            os.close(self._fd)
            self._fd = None


# ── One tick ───────────────────────────────────────────────────────


@dataclass
class RunRecord:
    """What one tick did, as written to `var/runs/<id>/run.json`."""

    run_id: str
    outcome: str  # "ok" | "failed" | "usage-limit"
    started: str
    seconds: float
    backend: str
    tier: str
    error: str | None = None
    counts: dict[str, int] = field(default_factory=dict)
    fetch_failures: list[dict[str, str]] = field(default_factory=list)
    digest: str | None = None
    # node → {component, sha256, imports}, for a run with a body swapped in.
    substituted: dict[str, dict] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "outcome": self.outcome,
            "started": self.started,
            "seconds": round(self.seconds, 3),
            "backend": self.backend,
            "tier": self.tier,
            "error": self.error,
            "counts": self.counts,
            "fetch_failures": self.fetch_failures,
            "digest": self.digest,
            "substituted": self.substituted,
        }


def _check_substitutes(config: Config, confined: Mapping[str, Iterable[str]]) -> dict[str, dict]:
    """Hold each substituted component to its node's `with` clause before the run,
    and return what was substituted, for the run record.

    The gate is not skipped because the body came from somewhere unusual: a
    substituted component is held to exactly the import set derived from the
    graph, by the same derivation as every committed one, and a component that
    over-imports is refused here rather than at its first crossing."""
    if not config.substitute:
        return {}
    from .sandbox.feed_nodes import FEED_COMPONENTS
    from .sandbox.host import imports_of
    from .sandbox.interfaces import expected_imports

    graphs = {config.graph["name"]: config.graph, config.child["name"]: config.child}
    stems = {GRAPH: config.graph, CHILD_GRAPH: config.child}
    running_confined = {n for g in graphs for n in confined.get(g, ())}
    record: dict[str, dict] = {}
    for node, path in config.substitute.items():
        if node not in FEED_COMPONENTS:
            raise ConfigError(f"no component port for node {node!r}; nothing to substitute")
        if node not in running_confined:
            raise ConfigError(
                f"{node!r} is not running on the confined tier, so a substituted component "
                f"would not be used; run with --tier confined"
            )
        stem, _artifact = FEED_COMPONENTS[node]
        expected = expected_imports(stems[stem], node)
        actual = imports_of(path)
        if actual != expected:
            raise ConfigError(
                f"the component substituted for {node!r} imports {actual}, but the node's "
                f"`with` clause derives {expected}; it was not run"
            )
        record[node] = {
            "component": str(path),
            "sha256": hashlib.sha256(Path(path).read_bytes()).hexdigest(),
            "imports": actual,
        }
    return record


@contextmanager
def _substituted(config: Config):
    """Load each substituted component in place of its node's committed artifact,
    for the body of the `with`."""
    if not config.substitute:
        yield
        return
    from .sandbox.feed_nodes import FEED_COMPONENTS
    from .sandbox.host import substituted

    swaps = {FEED_COMPONENTS[node][1]: Path(path) for node, path in config.substitute.items()}
    with substituted(swaps):
        yield


def _world(config: Config) -> World:
    return World(
        web=dict(config.web),
        live_http=config.live_http,
        state_dir=config.var_dir / "state",
        publishers={"digest": digest.publisher(config.var_dir / "digests", config.today)},
        clock=config.clock,  # type: ignore[arg-type]
    )


def _seed_subscriptions(world: World, config: Config) -> list[str]:
    """Seed the subscriptions store on first run, and return what it holds.

    This is the driver acting as the operator: it writes the store the graph's
    nodes can only read."""
    store = world.store("subscriptions")
    if store.get(SUBSCRIPTIONS_KEY) is None:
        store.put(SUBSCRIPTIONS_KEY, "\n".join(config.subscriptions) + "\n")
    raw = store.get(SUBSCRIPTIONS_KEY) or ""
    return [u.strip() for u in raw.splitlines() if u.strip() and not u.strip().startswith("#")]


def _counts(result: ExecutionResult, model_calls: int) -> tuple[dict[str, int], list[dict]]:
    """Read the run's numbers off what each node received. Nothing is counted by
    a node on the driver's behalf: the trace of what flowed is the record."""
    received = result.received
    batch = received["ParseFeeds"].value  # type: ignore[union-attr]
    selection = received["ComposeDigest"][0]  # type: ignore[index]
    report = result.terminals["RecordSeen"]
    counts = {
        "feeds": len(received["FetchFeeds"].urls),  # type: ignore[union-attr]
        "fetched": len(batch.documents),
        "fetch_failures": len(batch.failures),
        "items_parsed": len(received["DropSeen"]),  # type: ignore[arg-type]
        "items_new": len(received["LimitBatch"]),  # type: ignore[arg-type]
        "items_triaged": len(received["TriageItem"]),  # type: ignore[arg-type]
        "items_kept": len(selection.entries),
        "items_recorded": report.recorded,  # type: ignore[union-attr]
        "published": int(received["RecordSeen"].published),  # type: ignore[union-attr]
        "model_calls": model_calls,
    }
    failures = [{"url": f.url, "error": f.error} for f in batch.failures]
    return counts, failures


def _usage_limit(error: BaseException) -> bool:
    """True if `error`, or anything it was raised from, is the backend saying the
    subscription's window is spent."""
    seen: set[int] = set()
    current: BaseException | None = error
    while current is not None and id(current) not in seen:
        if isinstance(current, UsageLimitReached):
            return True
        seen.add(id(current))
        current = current.__cause__ or current.__context__
    return False


def tick(config: Config) -> RunRecord:
    """Assemble the graph, run one `Tick`, and record it under `var/runs/`.

    Does not take the lock — `run_once` and `run_every` do — so a caller that
    already holds it can tick repeatedly."""
    stamp = datetime.fromtimestamp(config.now().seconds, tz=UTC)
    run_id = stamp.strftime("%Y%m%dT%H%M%SZ")
    run_dir = config.var_dir / "runs" / run_id
    suffix = 1
    while run_dir.exists():  # two ticks in one second (tests, a fast loop)
        suffix += 1
        run_dir = config.var_dir / "runs" / f"{run_id}-{suffix}"
    run_dir.mkdir(parents=True)

    record = RunRecord(
        run_id=run_dir.name,
        outcome="failed",
        started=stamp.strftime("%Y-%m-%dT%H:%M:%SZ"),
        seconds=0.0,
        backend=type(config.backend).__name__,
        tier="confined" if config.confined else "host",
    )
    began = time.perf_counter()
    calls_before = len(getattr(config.backend, "calls", []))
    try:
        world = _world(config)
        check_subscriptions(_seed_subscriptions(world, config), config.graph)
        # The service's own invariants (one fetch node, no model upstream of it,
        # fetched content labelled untrusted). A graph that breaks one is not run.
        shape = feed_policy.problems(config.graph, config.child)
        if shape:
            raise ConfigError("the graph breaks the service's invariants:\n  " + "\n  ".join(shape))
        child_sandbox = config.sandbox or (
            {name: nodes for name, nodes in CONFINED_NODES.items()} if config.confined else {}
        )
        graph = assemble(
            config.graph,
            backend=config.backend,
            world=world,
            sandbox=child_sandbox.get(config.graph["name"], ()),
        )
        resolve = {config.child["name"]: config.child}
        record.substituted = _check_substitutes(config, child_sandbox)
        with _substituted(config):
            result = execute(graph, Tick(), graphs=resolve, sandbox=child_sandbox)
        model_calls = len(getattr(config.backend, "calls", [])) - calls_before
        record.counts, record.fetch_failures = _counts(result, model_calls)
        record.outcome = "ok"
        if record.counts["published"]:
            record.digest = f"digests/{config.today()}.md"
        (run_dir / "trace.json").write_text(json.dumps(result.trace.to_dict(), indent=1) + "\n")
    except ConfigError as e:
        record.error = f"ConfigError: {e}"
        raise
    except Exception as e:
        record.outcome = "usage-limit" if _usage_limit(e) else "failed"
        record.error = f"{type(e).__name__}: {e}"
        (run_dir / "error.txt").write_text(traceback.format_exc())
    finally:
        record.seconds = time.perf_counter() - began
        (run_dir / "run.json").write_text(json.dumps(record.to_dict(), indent=1) + "\n")
    return record


def _exit_code(record: RunRecord) -> int:
    return {"ok": EXIT_OK, "usage-limit": EXIT_USAGE_LIMIT}.get(record.outcome, EXIT_FAILED)


def run_once(config: Config) -> int:
    try:
        with Lock(config.var_dir):
            record = tick(config)
    except LockHeld as e:
        print(f"error: {e}", file=sys.stderr)
        return EXIT_LOCKED
    except (ConfigError, AssemblyError) as e:
        print(f"error: {e}", file=sys.stderr)
        return EXIT_CONFIG
    print(describe(record))
    return _exit_code(record)


def run_every(config: Config, interval: float, *, limit: int | None = None) -> int:
    """Tick, sleep, repeat, holding the lock throughout. A failed tick is recorded
    and the loop carries on: a service that stopped at the first dead feed would
    not be one. `limit` bounds the number of ticks (for tests)."""
    try:
        with Lock(config.var_dir):
            done = 0
            code = EXIT_OK
            while limit is None or done < limit:
                record = tick(config)
                print(describe(record), flush=True)
                code = _exit_code(record)
                done += 1
                if limit is None or done < limit:
                    time.sleep(interval)
            return code
    except LockHeld as e:
        print(f"error: {e}", file=sys.stderr)
        return EXIT_LOCKED
    except (ConfigError, AssemblyError) as e:
        print(f"error: {e}", file=sys.stderr)
        return EXIT_CONFIG
    except KeyboardInterrupt:
        return EXIT_OK


def describe(record: RunRecord) -> str:
    c = record.counts
    if record.outcome != "ok":
        return f"[{record.run_id}] {record.outcome}: {record.error}"
    wrote = f"wrote {record.digest}" if record.digest else "quiet (nothing selected)"
    return (
        f"[{record.run_id}] ok in {record.seconds:.1f}s — {c['fetched']}/{c['feeds']} feeds, "
        f"{c['items_new']} new of {c['items_parsed']}, {c['items_triaged']} triaged, "
        f"{c['items_kept']} kept, {c['model_calls']} model calls; {wrote}"
    )


# ── The report ─────────────────────────────────────────────────────


def report(var_dir: Path = VAR_DIR) -> dict:
    """Summarise every recorded run: how many, how they ended, what they moved."""
    records = []
    for path in sorted((var_dir / "runs").glob("*/run.json")):
        try:
            records.append(json.loads(path.read_text()))
        except (OSError, json.JSONDecodeError):
            continue
    outcomes: dict[str, int] = {}
    errors: dict[str, int] = {}
    totals: dict[str, int] = {}
    fetch_failures: dict[str, int] = {}
    for r in records:
        outcomes[r["outcome"]] = outcomes.get(r["outcome"], 0) + 1
        if r.get("error"):
            kind = r["error"].split(":", 1)[0]
            errors[kind] = errors.get(kind, 0) + 1
        for key, value in (r.get("counts") or {}).items():
            totals[key] = totals.get(key, 0) + int(value)
        for failure in r.get("fetch_failures") or []:
            fetch_failures[failure["url"]] = fetch_failures.get(failure["url"], 0) + 1
    digests = sorted(p.name for p in (var_dir / "digests").glob("*.md"))
    return {
        "runs": len(records),
        "first": records[0]["started"] if records else None,
        "last": records[-1]["started"] if records else None,
        "outcomes": dict(sorted(outcomes.items())),
        "failures_by_class": dict(sorted(errors.items())),
        "fetch_failures_by_feed": dict(sorted(fetch_failures.items())),
        "totals": dict(sorted(totals.items())),
        "digests": digests,
        "backends": sorted({r["backend"] for r in records}),
        "tiers": sorted({r["tier"] for r in records}),
    }


# ── Command line ───────────────────────────────────────────────────


def _interval(text: str) -> float:
    units = {"s": 1.0, "m": 60.0, "h": 3600.0}
    try:
        return float(text[:-1]) * units[text[-1]]
    except (KeyError, ValueError, IndexError) as e:
        raise argparse.ArgumentTypeError(f"not an interval like 30m or 1h: {text!r}") from e


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="poc.serve", description=__doc__.split("\n\n")[0])
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--once", action="store_true", help="run one tick and exit")
    mode.add_argument("--every", type=_interval, metavar="INTERVAL", help="tick every 30m, 1h, …")
    mode.add_argument("--report", action="store_true", help="summarise the recorded runs")
    parser.add_argument(
        "--backend",
        choices=("claude", "stub"),
        default="claude",
        help="what answers LLMClient<inference>: the local Claude CLI (default) or the "
        "deterministic stub",
    )
    parser.add_argument("--model", default="haiku", help="model alias for the Claude CLI backend")
    parser.add_argument(
        "--tier",
        choices=("host", "confined"),
        default="host",
        help="run the capability-holding nodes as Python (host) or as WASM components (confined)",
    )
    parser.add_argument("--var", type=Path, default=VAR_DIR, help="the service's data directory")
    parser.add_argument("--export", type=Path, help="with --report: also write the summary here")
    parser.add_argument(
        "--substitute",
        action="append",
        default=[],
        metavar="NODE=COMPONENT",
        help="run a component file in place of NODE's committed body (confined tier; "
        "repeatable). The component is held to the node's `with` clause first.",
    )
    args = parser.parse_args(argv)

    if args.report:
        summary = report(args.var)
        text = json.dumps(summary, indent=2) + "\n"
        if args.export:
            args.export.write_text(text)
        print(text, end="")
        return EXIT_OK

    backend: LLMBackend = (
        StubLLM()
        if args.backend == "stub"
        else ClaudeCLIBackend(model=args.model, effort="low", workdir=args.var / "llm")
    )
    substitute = {}
    for item in args.substitute:
        node, _, path = item.partition("=")
        if not node or not path:
            parser.error(f"--substitute takes NODE=COMPONENT, got {item!r}")
        substitute[node] = Path(path)
    config = Config(
        var_dir=args.var,
        backend=backend,
        confined=args.tier == "confined",
        substitute=substitute,
    )
    if args.once:
        return run_once(config)
    return run_every(config, args.every)


if __name__ == "__main__":
    raise SystemExit(main())
