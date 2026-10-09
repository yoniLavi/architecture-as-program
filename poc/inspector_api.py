"""The graph inspector's execution API — transport, not semantics.

A thin HTTP layer over the existing runtime, for the inspector UI (`ui/`) to
consume. Everything it serves is something the repository already has:

* the canonical graph JSONs, byte-for-byte as they sit in `graphs/` — the UI
  renders the same files the validator checks and the runtime executes, so its
  view cannot drift from the source of truth;
* the evaluation corpus (`poc/evaluate.py`), so the same cases whose verdicts the
  build pins are runnable interactively — a mutation case answers with the
  validator's rejection and its pinned reason class;
* runs through the same `assemble`/`execute` path the tests exercise, answering
  with the structured trace (`poc/trace.py`) of that run;
* the prompt-injection scenario via `evaluate.run_injection` — the very function
  the evaluation harness pins — on both enforcement tiers.

What it deliberately is not: an execution engine (the UI embeds none; WASM
components run under the server's wasmtime), a graph store (read-and-run only —
no mutation, no state, no auth; anything more is a new proposal), or a place
where semantics could accrete. Handlers are plain functions returning
`(status, payload)` so the contract tests (`tests/test_poc_inspector_api.py`)
cover them with and without a socket, and never need the UI built.

Run:  uv run --group poc python -m poc.inspector_api [--port 8123]
(The host tier needs no wasmtime; confined-tier runs do, hence the poc group.)
"""

from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from .demo import ADVERSARIAL, BENIGN, SANDBOXED_NODES, STORES
from .evaluate import CORPUS, Case, classify, run_injection
from .graph import (
    GRAPHS_DIR,
    AssemblyError,
    assemble,
    load_graph_dict,
    validate_graph_dict,
    validate_graph_dicts,
)
from .llm import StubLLM
from .runtime import execute
from .sandbox import available as sandbox_available
from .values import CustomerRequest, HTTPRoute
from .variants import UNSAFE_VARIANTS

DEFAULT_PORT = 8123

# One store map serves both canonical graphs: the customer-support knowledge base
# from the demo, plus the billing/audit stores the platform's own leaves append to.
INSPECTOR_STORES = {**STORES, "billing": {}, "audit": {}}

# Which nodes run confined when a run asks for the confined tier, per graph name.
# `assemble` takes the entry graph's own set; `execute` carries the whole mapping
# so a nested sub-graph's nodes resolve to their tiers (the demo's set for
# CustomerSupport — the platform's own leaves have no ported components).
SANDBOX_CONFIG: dict[str, frozenset[str]] = {
    "CustomerSupport": frozenset(SANDBOXED_NODES),
}

TIER_HOST = "host"
TIER_CONFINED = "confined"

# How a JSON request body becomes the graph's boundary value. The API's one
# domain-aware seam: the same narrowing the demo and the tests perform inline.
_BOUNDARY_BUILDERS = {
    "CustomerSupport": lambda p: CustomerRequest(
        session_id=p.get("session_id", "user-session"),
        body=p.get("message") or BENIGN,
    ),
    "SupportPlatform": lambda p: HTTPRoute(
        path=p.get("path", "/customer/message"),
        session_id=p.get("session_id", "user-session"),
        body=p.get("message") or BENIGN,
    ),
}

_CASES: dict[str, Case] = {c.name: c for c in CORPUS}


class ApiError(Exception):
    """A client-visible failure: carries the HTTP status and message to answer with."""

    def __init__(self, status: int, message: str):
        self.status = status
        self.message = message
        super().__init__(message)


# ── Handlers: plain functions, (status, payload) ─────────────────────


def graph_index() -> tuple[int, dict]:
    """The canonical graphs, by declared name and file stem."""
    graphs = []
    for path in sorted(GRAPHS_DIR.glob("*.json")):
        if path.name == "schema.json":
            continue
        graphs.append({"name": json.loads(path.read_text())["name"], "file": path.stem})
    return 200, {"graphs": graphs}


def graph_file(stem: str) -> bytes:
    """One canonical graph file, byte-for-byte — served unmodified so the UI's
    rendering source is provably the file the validator checks (the contract test
    asserts byte parity)."""
    path = GRAPHS_DIR / f"{stem}.json"
    if stem == "schema" or not path.exists():
        raise ApiError(404, f"no canonical graph {stem!r}")
    return path.read_bytes()


def corpus_index() -> tuple[int, dict]:
    """The evaluation corpus, as runnable cases. The same `Case` records the
    harness pins, so what the UI offers and what the build guards cannot diverge."""
    return 200, {
        "cases": [
            {
                "name": c.name,
                "kind": c.kind,
                "expected": c.expected,
                "reason": c.reason,
                "note": c.note,
                "base": c.base,
            }
            for c in CORPUS
        ]
    }


def _case_graph(case: Case) -> dict:
    """The graph a corpus case validates: the canonical file for a canonical case,
    the mutation applied to its base for a mutation case — derived on demand from
    the same `UNSAFE_VARIANTS` the harness runs, never stored separately."""
    if case.kind == "canonical":
        return load_graph_dict(case.name)
    return UNSAFE_VARIANTS[case.name](load_graph_dict(case.base))


def case_graph(name: str) -> tuple[int, dict]:
    case = _CASES.get(name)
    if case is None:
        raise ApiError(404, f"no corpus case {name!r}")
    return 200, {"case": name, "graph": _case_graph(case)}


def _validate_case(case: Case, graph: dict) -> list[str]:
    """Validate exactly as the harness does — alone, or batched with the graphs a
    cross-graph case names — so a rejection here lands in the same pinned reason
    class as in `dist/evaluation.md`."""
    if case.with_graphs:
        others = [load_graph_dict(g) for g in case.with_graphs]
        return validate_graph_dicts([graph, *others])
    return validate_graph_dict(graph)


def _value_summary(value: object) -> dict:
    return {"type": type(value).__name__, "repr": repr(value)}


def run_case(payload: dict) -> tuple[int, dict]:
    """Assemble and execute a corpus case; answer with the run's own trace.

    A case that fails validation answers 422 with the validator's errors and the
    reason class they classify into — the assembly-time gate, made visible."""
    name = str(payload.get("case"))
    case = _CASES.get(name)
    if case is None:
        raise ApiError(404, f"no corpus case {name!r}")

    tier = payload.get("tier", TIER_HOST)
    if tier not in (TIER_HOST, TIER_CONFINED):
        raise ApiError(400, f"tier must be {TIER_HOST!r} or {TIER_CONFINED!r}, got {tier!r}")
    if tier == TIER_CONFINED and not sandbox_available():
        raise ApiError(
            409, "the confined tier needs wasmtime (`uv sync --group poc`); run the host tier"
        )

    graph = _case_graph(case)
    errors = _validate_case(case, graph)
    if errors:
        return 422, {
            "rejected": True,
            "case": case.name,
            "reason_class": classify(errors, case.reason),
            "errors": errors,
        }

    graph_name = graph["name"]
    builder = _BOUNDARY_BUILDERS.get(graph_name)
    if builder is None:
        raise ApiError(400, f"no boundary-input builder for graph {graph_name!r}")
    boundary = builder(payload)

    sandbox = SANDBOX_CONFIG if tier == TIER_CONFINED else {}
    try:
        assembled = assemble(
            graph,
            backend=StubLLM(),
            stores=INSPECTOR_STORES,
            sandbox=sandbox.get(graph_name, ()),
        )
        result = execute(assembled, boundary, sandbox=sandbox)
    except AssemblyError as e:
        return 422, {
            "rejected": True,
            "case": case.name,
            "reason_class": classify(e.errors, case.reason),
            "errors": e.errors,
        }

    return 200, {
        "case": case.name,
        "graph": graph_name,
        "tier": tier,
        "input": _value_summary(boundary),
        "trace": result.trace.to_dict(include_timing=False),
        "terminals": {n: _value_summary(v) for n, v in result.terminals.items()},
    }


def _injection_dict(inj) -> dict:
    return {
        "path": list(inj.path),
        "tiers": dict(inj.tiers),
        "received_type": inj.received_type,
        "is_untrusted": inj.is_untrusted,
        "adversarial_text_present": inj.adversarial_text_present,
        "out_of_scope_call_refused": inj.out_of_scope_call_refused,
        "trace": inj.trace.to_dict(include_timing=False),
    }


def injection_scenario() -> tuple[int, dict]:
    """The prompt-injection scenario on both tiers, via the same `run_injection`
    the evaluation harness pins. If wasmtime is absent the confined half is null,
    stated rather than faked — the host half is a real run either way."""
    graph = load_graph_dict("customer-support")
    confined = _injection_dict(run_injection(set(SANDBOXED_NODES))) if sandbox_available() else None
    return 200, {
        "adversarial_message": ADVERSARIAL,
        "discharge_node": next(n["name"] for n in graph["nodes"] if n.get("discharges_trust")),
        "host": _injection_dict(run_injection(set())),
        "confined": confined,
    }


# ── The feed-triage service ──────────────────────────────────────────
#
# Kept under its own routes (`/api/feed/…`) rather than folded into the corpus
# ones above: those serve the cases Paper 2's evaluation pins, and what the
# inspector says about them is part of that paper's record. Everything here comes
# from `poc/evaluate_feed.py` — the same cases, the same runner, the same
# classification — so, as above, what the UI offers and what the build guards
# cannot diverge.


def feed_cases() -> tuple[int, dict]:
    """The feed evaluation's two corpora: rewirings of the graphs, and hostile feeds."""
    from . import evaluate_feed as ef
    from .feeds.corpus import CASES

    return 200, {
        "corpus": [
            {
                "name": c.name,
                "kind": c.kind,
                "expected": c.expected,
                "reason": c.reason,
                "note": c.note,
                "validator_accepts": c.validator_accepts,
            }
            for c in ef.FEED_CORPUS
        ],
        "hostile": [
            {"name": c.name, "verdict": c.verdict, "attack": c.attack, "outcome": c.outcome}
            for c in CASES
        ],
    }


def _feed_case(name: str):
    from . import evaluate_feed as ef

    case = next((c for c in ef.FEED_CORPUS if c.name == name), None)
    if case is None:
        raise ApiError(404, f"no feed corpus case {name!r}")
    return case


def feed_case_graphs(name: str) -> tuple[int, dict]:
    """The two graphs a feed corpus case validates: the canonical pair, with the
    case's rewiring applied to whichever of them it rewrites."""
    from . import evaluate_feed as ef

    case = _feed_case(name)
    parent, child = ef._graphs_for(case.name)
    return 200, {"case": name, "parent": parent, "child": child}


def run_feed(payload: dict) -> tuple[int, dict]:
    """One tick of the feed-triage service, through `evaluate_feed`'s own runners.

    `case` names a feed corpus case (default: the canonical graph). A rewiring
    that is rejected answers 422 with the errors, the reason class, and *which
    layer* rejected it — the validator, or only the service's own shape check.

    A graph that is accepted is run for one tick. With `hostile` naming a hostile
    feed, the tick is that case — the feed served from the fixture server, the
    model fooled — and the answer carries the facts the build pins for it.
    Otherwise it is a tick over the sample feeds on the stub model."""
    from . import evaluate_feed as ef
    from . import feed_policy
    from .feeds.corpus import CASES

    case = _feed_case(str(payload.get("case") or ef.PARENT_STEM))
    tier = payload.get("tier", TIER_HOST)
    if tier not in (TIER_HOST, TIER_CONFINED):
        raise ApiError(400, f"tier must be {TIER_HOST!r} or {TIER_CONFINED!r}, got {tier!r}")
    if tier == TIER_CONFINED and not sandbox_available():
        raise ApiError(
            409, "the confined tier needs wasmtime (`uv sync --group poc`); run the host tier"
        )

    parent, child = ef._graphs_for(case.name)
    errors = validate_graph_dicts([parent, child])
    validator_accepts = not errors
    if not errors:
        errors = feed_policy.problems(parent, child)
    if errors:
        return 422, {
            "rejected": True,
            "case": case.name,
            "reason_class": ef.classify(errors, case.reason, ef.FEED_SIGNATURES),
            "validator_accepts": validator_accepts,
            "errors": errors,
        }
    if case.kind != "canonical":
        # An accepted rewiring (the safe variant) validates and assembles; its
        # rewritten types have no node bodies, so there is nothing to run.
        return 200, {"case": case.name, "accepted": True, "ran": False}

    confined = tier == TIER_CONFINED
    hostile_name = payload.get("hostile")
    if hostile_name:
        hostile = next((c for c in CASES if c.name == hostile_name), None)
        if hostile is None:
            raise ApiError(404, f"no hostile feed case {hostile_name!r}")
        facts, markdown, result = ef.run_hostile_traced(hostile, confined=confined)
        verdict = hostile.verdict
    else:
        result, sent, _backend = ef.benign_tick(confined=confined)
        facts, markdown, verdict = None, (sent[-1] if sent else ""), None

    from . import digest

    return 200, {
        "case": case.name,
        "graph": parent["name"],
        "tier": tier,
        "hostile": hostile_name or None,
        "verdict": verdict,
        "facts": facts,
        "trace": None if result is None else result.trace.to_dict(include_timing=False),
        "terminals": {}
        if result is None
        else {n: _value_summary(v) for n, v in result.terminals.items()},
        "digest": {
            "markdown": markdown,
            "html": digest.render_html(markdown, title="Feed digest") if markdown else "",
        },
    }


def latest_digest() -> tuple[int, dict]:
    """The most recent digest the live service wrote under `var/digests/`, if any.

    Read-only, like everything here: the inspector links what the service
    published and has no way to publish."""
    from . import digest, serve

    page = digest.latest(serve.VAR_DIR / "digests")
    if page is None:
        raise ApiError(404, "the service has written no digest yet")
    markdown = page.with_suffix(".md").read_text()
    return 200, {"date": page.stem, "markdown": markdown, "html": page.read_text()}


def meta() -> tuple[int, dict]:
    """What this server can do right now — the UI reads this instead of guessing."""
    return 200, {
        "confined_tier_available": sandbox_available(),
        "sandboxed_nodes": sorted(SANDBOXED_NODES),
        "benign_message": BENIGN,
        "adversarial_message": ADVERSARIAL,
    }


# ── HTTP plumbing ────────────────────────────────────────────────────


class InspectorHandler(BaseHTTPRequestHandler):
    """Routes requests to the handlers above. CORS is wide open on purpose: the
    server binds loopback and serves public repository data; the Next.js dev
    server proxies to it, and a browser hitting it directly should also work."""

    server_version = "InspectorAPI/0"

    def _send(self, status: int, body: bytes, content_type: str = "application/json") -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, status: int, payload: dict) -> None:
        self._send(status, json.dumps(payload).encode())

    def _dispatch(self, handler) -> None:
        try:
            status, payload = handler()
        except ApiError as e:
            self._send_json(e.status, {"error": e.message})
        except Exception as e:  # a bug, not a client error — say which
            self._send_json(500, {"error": f"{type(e).__name__}: {e}"})
        else:
            self._send_json(status, payload)

    def do_OPTIONS(self) -> None:  # CORS preflight
        self._send(204, b"")

    def do_GET(self) -> None:
        path = urlparse(self.path).path.rstrip("/")
        parts = [p for p in path.split("/") if p]
        if parts == ["api", "graphs"]:
            self._dispatch(graph_index)
        elif len(parts) == 3 and parts[:2] == ["api", "graphs"]:
            try:
                self._send(200, graph_file(parts[2]))
            except ApiError as e:
                self._send_json(e.status, {"error": e.message})
        elif parts == ["api", "corpus"]:
            self._dispatch(corpus_index)
        elif len(parts) == 4 and parts[:2] == ["api", "corpus"] and parts[3] == "graph":
            self._dispatch(lambda: case_graph(parts[2]))
        elif parts == ["api", "meta"]:
            self._dispatch(meta)
        elif parts == ["api", "feed", "cases"]:
            self._dispatch(feed_cases)
        elif len(parts) == 5 and parts[:3] == ["api", "feed", "cases"] and parts[4] == "graphs":
            self._dispatch(lambda: feed_case_graphs(parts[3]))
        elif parts == ["api", "feed", "digest", "latest"]:
            self._dispatch(latest_digest)
        else:
            self._send_json(404, {"error": f"no route {path!r}"})

    def do_POST(self) -> None:
        path = urlparse(self.path).path.rstrip("/")
        try:
            length = int(self.headers.get("Content-Length", 0))
            payload = json.loads(self.rfile.read(length) or b"{}")
            if not isinstance(payload, dict):
                raise ValueError("body must be a JSON object")
        except (ValueError, json.JSONDecodeError) as e:
            self._send_json(400, {"error": f"bad request body: {e}"})
            return

        if path == "/api/run":
            self._dispatch(lambda: run_case(payload))
        elif path == "/api/scenario/injection":
            self._dispatch(injection_scenario)
        elif path == "/api/feed/run":
            self._dispatch(lambda: run_feed(payload))
        else:
            self._send_json(404, {"error": f"no route {path!r}"})

    def log_message(self, format: str, *args) -> None:  # quiet by default
        pass


def serve(host: str = "127.0.0.1", port: int = DEFAULT_PORT) -> ThreadingHTTPServer:
    """Bind and return the server (port 0 picks a free port — the tests do)."""
    return ThreadingHTTPServer((host, port), InspectorHandler)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = parser.parse_args()

    server = serve(args.host, args.port)
    tier = "host + confined" if sandbox_available() else "host only (wasmtime not installed)"
    print(f"inspector API listening on http://{args.host}:{server.server_address[1]}")
    print(f"enforcement tiers available: {tier}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
