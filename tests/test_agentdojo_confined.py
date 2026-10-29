"""The node library on the confined tier (task 3.4).

Each authority-holding library entry is a WASM component whose world imports
exactly the interface its capability kind maps to. Three claims, each a test:

* **the derivation gate**: for every node of every oracle graph that has a
  component, the interfaces derived from its `with` clause equal the component's
  actual capability imports, and the gate fires when they do not;
* **scope at the crossing**: a refused payment traps through the component before
  the bank is touched;
* **the tiers agree**: every oracle run gives the same record on both tiers.

Needs `wasmtime` (the `poc` group); the tier comparison also needs `agentdojo`."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from poc.sandbox import available

pytestmark = pytest.mark.skipif(not available(), reason="needs wasmtime (the poc group)")

from poc.agentdojo.confined import COMPONENTS  # noqa: E402
from poc.agentdojo.library import CATALOGUE, bodies, confinable  # noqa: E402
from poc.agentdojo.standins import OracleModel  # noqa: E402
from poc.bank import MemoryBank  # noqa: E402
from poc.graph import assemble  # noqa: E402
from poc.handles import CapabilityError, World  # noqa: E402
from poc.runtime import execute  # noqa: E402
from poc.sandbox.host import capability_imports  # noqa: E402
from poc.sandbox.interfaces import interface_for, interfaces_for_node  # noqa: E402

GRAPHS = Path(__file__).resolve().parent.parent / "poc" / "agentdojo" / "graphs"
ORACLE = [json.loads(p.read_text()) for p in sorted(GRAPHS.glob("banking-*.json"))]


def _gate(graph: dict, node: dict) -> tuple[list[str], list[str]]:
    derived = interfaces_for_node(node, graph["capabilities"])
    return derived, capability_imports(COMPONENTS[node["uses"]])


@pytest.mark.parametrize(
    ("graph", "node"),
    [(g, n) for g in ORACLE for n in g["nodes"] if n["name"] in confinable(g)],
    ids=lambda v: v["name"],
)
def test_each_confined_node_imports_exactly_what_its_clause_derives(graph, node):
    derived, actual = _gate(graph, node)
    assert derived == actual and len(actual) == 1


def test_every_component_is_held_to_its_entrys_kind():
    """One example clause per entry: the gate at the catalogue, not only the oracles."""
    example = {
        "SendMoney": "Payments<['X'], '1'>",
        "ScheduleTransaction": "Payments<['X'], '1', recurring>",
        "UpdateScheduledTransaction": "ScheduledPayments<['Rent'], [amount]>",
        "UpdateUserInfo": "UserProfile<[street]>",
        "Respond": "ResponseChannel<user-session>",
        "Extract": "LLMClient<inference>",
    }
    for entry, component in COMPONENTS.items():
        clause = example.get(entry, f"DBHandle<'{CATALOGUE[entry].scope}x', read>")
        assert capability_imports(component) == [interface_for(clause)], entry


def test_the_gate_fires_on_a_component_held_to_another_clause():
    """A gate that cannot fail proves nothing: hold the payment component to a
    profile-update clause, and it imports an interface that clause does not grant."""
    graph = next(g for g in ORACLE if g["name"] == "BankingUserTask15")
    node = dict(next(n for n in graph["nodes"] if n["uses"] == "UpdateUserInfo"))
    node["uses"] = "SendMoney"
    derived, actual = _gate(graph, node)
    assert derived != actual


def test_a_refused_payment_traps_through_the_component_before_the_bank():
    graph = next(g for g in ORACLE if g["name"] == "BankingUserTask15")
    graph = json.loads(json.dumps(graph))
    for n in graph["nodes"]:
        if n["name"] == "Refund":
            n["params"]["fields"]["recipient"] = "US133000000121212121212"
    bank = MemoryBank(
        transactions=[dict(id=5, sender="GB29NWBK60161331926819", recipient="me",
                           amount=10.0, subject="x", date="d", recurring=False)],
        scheduled=[dict(id=7, sender="a", recipient="b", amount=1.0, subject="Rent",
                        date="d", recurring=False)],
        user={"street": "s", "city": "c"},
    )  # fmt: skip
    confined = confinable(graph)
    assembled = assemble(graph, backend=OracleModel({}), world=World(bank=bank), sandbox=confined)
    with pytest.raises(CapabilityError, match="outside the handle's payees"):
        execute(assembled, {"prompt": "x"}, impls=bodies(graph, confined))
    assert "send_money" not in [w[0] for w in bank.writes]


def _normalised(record: dict) -> dict:
    """Numbers compare as floats: a confined body sends `amount` as a WIT `f64`."""
    out = dict(record)
    out["calls"] = [
        {**c, "args": {k: float(v) if type(v) in (int, float) else v for k, v in c["args"].items()}}
        for c in record["calls"]
    ]
    return out


def test_every_oracle_run_gives_the_same_record_on_both_tiers():
    pytest.importorskip("agentdojo")
    from poc.agentdojo import harness

    committed = json.loads(harness.ORACLE_RECORD.read_text())["runs"]
    graphs = {name: harness.load_graph(name) for name in harness.ORACLE_GRAPHS}
    by_name = {g["name"]: g for g in graphs.values()}
    for host in committed:
        g = by_name[host["graph"]]
        confined = harness.run_pair(
            g,
            host["user_task"],
            host["injection_task"],
            fooled=host["model"] == "fooled",
            sandbox=tuple(confinable(g)),
        ).as_dict()
        assert _normalised(confined) == _normalised(host), (host["graph"], host["injection_task"])
