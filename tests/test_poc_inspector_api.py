"""Contract tests for the graph inspector's execution API.

These pin, on the Python side and with no UI built, every behaviour the inspector
(and the paper's report of it) relies on:

* the canonical graphs are served **byte-for-byte** — the UI's rendering source
  is the file the validator checks, not a re-serialisation of it;
* a run answers with the runtime's own structured trace, schema-valid;
* a corpus mutation case answers with the validator's rejection **and the same
  pinned reason class** the evaluation harness guards;
* the prompt-injection scenario endpoint reports the same facts
  `poc/evaluate.py` pins (sole trust discharge, the free-text residual).

Covers the `graph-inspector` spec requirements added by `add-graph-inspector-ui`:
  - The inspector renders the canonical graph sources (serving side)
  - Execution is triggered server-side through the existing runtime
  - The corpus build does not depend on the UI toolchain (these tests are it)

Confined-tier cases are gated on wasmtime exactly as the sandbox suite is; the
host-tier contract runs everywhere.
"""

from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request

import pytest

from poc.evaluate import CORPUS
from poc.graph import GRAPHS_DIR
from poc.inspector_api import (
    ApiError,
    case_graph,
    corpus_index,
    graph_file,
    graph_index,
    injection_scenario,
    run_case,
    serve,
)
from poc.sandbox import available
from poc.trace import validate_document

sandboxed = pytest.mark.skipif(
    not available(), reason="wasmtime not installed (`uv sync --group poc`)"
)

MUTATIONS = {c.name: c for c in CORPUS if c.kind == "mutation"}


# ── Serving the canonical sources ────────────────────────────────────


def test_graph_index_lists_every_canonical_graph():
    _, payload = graph_index()
    entries = {g["file"]: g["name"] for g in payload["graphs"]}
    assert entries == {
        "customer-support": "CustomerSupport",
        "support-platform": "SupportPlatform",
    }


@pytest.mark.parametrize("stem", ["customer-support", "support-platform"])
def test_graph_file_is_byte_identical_to_the_canonical_source(stem):
    """The single-source-of-truth contract: the API serves the file, not a parse
    of it. Byte parity is what makes 'rendered from the canonical source' a
    checkable claim rather than a habit."""
    assert graph_file(stem) == (GRAPHS_DIR / f"{stem}.json").read_bytes()


def test_graph_file_refuses_the_schema_and_unknown_stems():
    for stem in ("schema", "no-such-graph"):
        with pytest.raises(ApiError) as e:
            graph_file(stem)
        assert e.value.status == 404


# ── The corpus, runnable ─────────────────────────────────────────────


def test_corpus_index_mirrors_the_harness_corpus():
    _, payload = corpus_index()
    assert [c["name"] for c in payload["cases"]] == [c.name for c in CORPUS]
    by_name = {c["name"]: c for c in payload["cases"]}
    for case in CORPUS:
        assert by_name[case.name]["expected"] == case.expected
        assert by_name[case.name]["reason"] == case.reason


def test_case_graph_serves_the_mutated_graph_for_a_mutation_case():
    """The rejection display needs the graph that was rejected. It is derived from
    the canonical base by the same mutation the harness runs — here, the laundering
    case's widened consumer input is visible in what the API serves."""
    _, payload = case_graph("launder_trust")
    mutated = payload["graph"]
    canonical = json.loads((GRAPHS_DIR / "customer-support.json").read_text())
    assert mutated != canonical
    assert mutated["name"] == canonical["name"]


def test_run_of_a_canonical_case_returns_the_runtime_trace():
    status, payload = run_case({"case": "customer-support", "message": "Why was I charged twice?"})
    assert status == 200
    assert payload["graph"] == "CustomerSupport"
    assert payload["tier"] == "host"
    trace = payload["trace"]
    assert validate_document(trace) == []
    assert trace["graph"] == "CustomerSupport"
    order = [n["node"] for n in trace["nodes"]]
    assert order[:2] == ["ReceiveMessage", "ParseMessage"]
    assert payload["terminals"]  # the run reached a terminal


def test_run_of_the_platform_nests_the_subgraph_trace():
    status, payload = run_case({"case": "support-platform", "message": "billing question"})
    assert status == 200
    nodes = {n["node"]: n for n in payload["trace"]["nodes"]}
    sub = nodes["CustomerSupport"]
    assert sub["tier"] == "graph"
    assert sub["subgraph"]["graph"] == "CustomerSupport"
    assert validate_document(payload["trace"]) == []


@pytest.mark.parametrize("name", sorted(MUTATIONS))
def test_run_of_a_mutation_case_is_rejected_with_its_pinned_reason_class(name):
    """The assembly-time gate, surfaced: each unsafe case answers 422, classified
    into the same reason class the evaluation harness pins for it — so the
    inspector's rejection display and `dist/evaluation.md` cannot tell different
    stories about why a wiring was refused."""
    status, payload = run_case({"case": name})
    assert status == 422
    assert payload["rejected"] is True
    assert payload["reason_class"] == MUTATIONS[name].reason
    assert payload["errors"]


def test_run_refuses_unknown_cases_and_bad_tiers():
    with pytest.raises(ApiError) as e:
        run_case({"case": "no-such-case"})
    assert e.value.status == 404
    with pytest.raises(ApiError) as e:
        run_case({"case": "customer-support", "tier": "memory-safe"})
    assert e.value.status == 400


@sandboxed
def test_confined_run_reports_sandbox_tiers_in_the_trace():
    status, payload = run_case({"case": "customer-support", "tier": "confined"})
    assert status == 200
    tiers = {n["node"]: n["tier"] for n in payload["trace"]["nodes"]}
    assert tiers["ReceiveMessage"] == "host"
    assert tiers["ParseMessage"] == "sandbox"
    assert validate_document(payload["trace"]) == []


# ── The injection scenario ───────────────────────────────────────────


def _raisers(trace: dict) -> list[str]:
    out = []
    for node in trace["nodes"]:
        if node["input_trust"] == "untrusted" and node["output_trust"] == "trusted":
            out.append(node["node"])
        if node.get("subgraph"):
            out.extend(_raisers(node["subgraph"]))
    return out


def test_injection_scenario_reports_the_pinned_facts_on_the_host_tier():
    _, payload = injection_scenario()
    assert payload["discharge_node"] == "ParseMessage"
    host = payload["host"]
    assert validate_document(host["trace"]) == []
    # Trust is raised only at the declared discharge node — the walkthrough's
    # taint step reads exactly this from the trace.
    assert _raisers(host["trace"]) == ["ParseMessage"]
    # The residual, honestly present: adversarial text reaches the tool-capable
    # node through a permitted field, and the out-of-scope call is refused.
    assert host["adversarial_text_present"] is True
    assert host["out_of_scope_call_refused"] is True
    assert host["is_untrusted"] is False


@sandboxed
def test_injection_scenario_contrasts_the_two_tiers():
    _, payload = injection_scenario()
    confined = payload["confined"]
    assert confined is not None
    assert _raisers(confined["trace"]) == ["ParseMessage"]
    # Same structure, different enforcement: the recorded difference between the
    # two runs is the tier field, which is what the UI's contrast view shows.
    host_tiers = payload["host"]["tiers"]
    assert set(confined["tiers"]) == set(host_tiers)
    assert confined["tiers"]["ParseMessage"] == "sandbox"
    assert host_tiers["ParseMessage"] == "host"


# ── Over the wire ────────────────────────────────────────────────────
#
# The handlers are covered directly above; one thread-backed server exercise pins
# the transport itself: routing, status codes, and that the graph bytes survive
# HTTP unmodified.


@pytest.fixture(scope="module")
def api_base():
    server = serve(port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()
    server.server_close()


def _get(url: str):
    with urllib.request.urlopen(url) as resp:
        return resp.status, resp.read()


def test_http_graph_serving_is_unmodified(api_base):
    status, body = _get(f"{api_base}/api/graphs/customer-support")
    assert status == 200
    assert body == (GRAPHS_DIR / "customer-support.json").read_bytes()


def test_http_run_round_trip(api_base):
    req = urllib.request.Request(
        f"{api_base}/api/run",
        data=json.dumps({"case": "customer-support"}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        payload = json.loads(resp.read())
    assert validate_document(payload["trace"]) == []


def test_http_rejection_surfaces_with_422(api_base):
    req = urllib.request.Request(
        f"{api_base}/api/run",
        data=json.dumps({"case": "launder_trust"}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with pytest.raises(urllib.error.HTTPError) as e:
        urllib.request.urlopen(req)
    assert e.value.code == 422
    payload = json.loads(e.value.read())
    assert payload["reason_class"] == "trust lattice"


def test_http_unknown_route_is_404(api_base):
    with pytest.raises(urllib.error.HTTPError) as e:
        _get(f"{api_base}/api/nope")
    assert e.value.code == 404
