"""Stage two of the architect, and the validator in its loop (tasks 1.2, 1.3).
Stdlib-only: no model, no AgentDojo."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from poc.agentdojo.library import CATALOGUE, RECORDS
from poc.architect import mapping, verdicts
from poc.architect.abstract import NOT_JSON, SHAPE
from poc.architect.mapping import Inexpressible

GRAPHS = Path(__file__).resolve().parent.parent / "poc" / "agentdojo" / "graphs"
ORACLES = sorted(p for p in GRAPHS.glob("banking-user-task-*.json"))


def test_the_worked_example_is_a_valid_library_graph():
    graph = {"name": "Example", **mapping.EXAMPLE}
    assert verdicts.check(graph) == []


def test_the_example_justifies_every_grant_from_its_own_task():
    task = (
        "Send 25.00 to my sister, DE75512108001245126199, for the concert ticket, "
        "and tell me when it's done."
    )
    assert task in mapping.system()
    caps = set(mapping.EXAMPLE["capabilities"])
    for node in mapping.EXAMPLE["nodes"]:
        held = [i for i in node["inputs"] if i in caps]
        assert sorted(node.get("because", {})) == sorted(held)
        assert all(q in task for q in node.get("because", {}).values())


@pytest.mark.parametrize("path", ORACLES, ids=lambda p: p.stem)
def test_the_oracle_graphs_pass_the_loop_s_check(path):
    assert verdicts.check(json.loads(path.read_text())) == []


def test_the_catalogue_shows_every_entry_and_record():
    shown = mapping.system()
    for name in [*CATALOGUE, *RECORDS]:
        assert f"`{name}`" in shown, name
    assert "{{" not in shown


def test_the_catalogue_shows_shapes_and_no_bank_values():
    # The values a reader would return are tool output; the architect sees none.
    shown = mapping.system()
    for value in ("'me'", "Spotify", "GB29NWBK60161331926819", "Rent", "2022-03"):
        assert value not in shown, value


def test_a_good_reply_becomes_a_graph_with_the_given_name():
    graph, reasons = mapping.parse(json.dumps(mapping.EXAMPLE), "ArchitectTask0")
    assert reasons == [] and graph["name"] == "ArchitectTask0"


def test_inexpressible_is_an_answer_not_a_failure():
    out, reasons = mapping.parse('{"inexpressible": "no node changes a password"}', "X")
    assert reasons == [] and out == Inexpressible("no node changes a password")


@pytest.mark.parametrize(
    ("reply", "cls"),
    [
        ("nothing", NOT_JSON),
        ('{"nodes": []}', SHAPE),
        (json.dumps({**mapping.EXAMPLE, "extra": 1}), SHAPE),
    ],
)
def test_a_malformed_reply_earns_its_reason(reply, cls):
    graph, reasons = mapping.parse(reply, "X")
    assert graph is None and cls in {r.cls for r in reasons}


def _example() -> dict:
    return {"name": "Example", **copy.deepcopy(mapping.EXAMPLE)}


def test_a_never_granted_kind_is_classed_as_such():
    g = _example()
    g["parameters"].append("Credentials")
    g["capabilities"].append("Credentials")
    g["nodes"][2]["inputs"].append("Credentials")
    assert "never-granted kind" in {r.cls for r in verdicts.check(g)}


def test_an_edge_type_mismatch_is_classed_by_the_paper_s_signature():
    g = _example()
    g["nodes"][1]["output"] = "StandingOrder"
    classes = {r.cls for r in verdicts.check(g)}
    assert "edge type-compatibility" in classes


def test_a_library_misuse_is_classed_library():
    g = _example()
    g["nodes"][1]["params"]["fields"].pop("date")
    reasons = verdicts.check(g)
    assert [r.cls for r in reasons] == ["library"]
    assert "missing ['date']" in reasons[0].detail


def test_details_carry_no_temporary_file_name():
    g = _example()
    g["nodes"][1]["output"] = "StandingOrder"
    assert not any(".json:" in r.detail for r in verdicts.check(g))
