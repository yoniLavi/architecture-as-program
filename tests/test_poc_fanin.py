"""Fan-in, in the two restricted forms the runtime now has, and no others.

* The **per-item map**: a sub-graph node declaring `"each": true` is applied to
  each element of a list, each element in its own isolated child run.
* The **positional join**: a node with several data inputs, each fed by exactly
  one edge naming its position, run once when all hold a value.

What is still refused, and tested as refused: a second arrival at one input (a
merge of streams, whose result would depend on arrival order).

Covers the `signal-graph-runtime` requirements "A sub-graph node may be applied to
each element of a list" and "A node may join several inputs by position", and the
`trust-typing` requirements "A join's output trust is bounded by the meet of its
inputs" and "A per-item map lifts trust element-wise".
"""

from __future__ import annotations

import copy

import pytest

from poc.contracts import ContractViolation
from poc.graph import AssemblyError, assemble, validate_graph_dict, validate_graph_dicts
from poc.llm import StubLLM
from poc.nodes import REGISTRY
from poc.runtime import ExecutionError, execute
from poc.trace import validate_document
from poc.values import Untrusted, Variant

# ── A join: Split fans out to Left and Right, Merge joins them ───────

JOIN = {
    "name": "JoinDemo",
    "parameters": ["Req"],
    "capabilities": [],
    "nodes": [
        {"name": "Split", "inputs": ["Req"], "output": "Seed"},
        {"name": "Left", "inputs": ["Seed"], "output": "A"},
        {"name": "Right", "inputs": ["Seed"], "output": "B"},
        {"name": "Merge", "inputs": ["A", "B"], "output": "Done"},
    ],
    "data_edges": [
        {"from": "Split", "to": "Left"},
        {"from": "Split", "to": "Right"},
        {"from": "Left", "to": "Merge", "to_input": 0},
        {"from": "Right", "to": "Merge", "to_input": 1},
    ],
}


@pytest.fixture
def join_impls(monkeypatch):
    for name, impl in {
        "Split": lambda req: f"seed({req})",
        "Left": lambda seed: f"L[{seed}]",
        "Right": lambda seed: f"R[{seed}]",
        "Merge": lambda a, b: f"{a}+{b}",
    }.items():
        monkeypatch.setitem(REGISTRY, name, impl)


def _run(graph: dict, value: object = "x", **kw):
    return execute(assemble(graph, backend=StubLLM()), value, **kw)


def _with(graph: dict, **changes) -> dict:
    out = copy.deepcopy(graph)
    out.update(changes)
    return out


def test_a_join_validates():
    assert validate_graph_dict(JOIN) == []


def test_a_join_runs_once_with_its_inputs_by_position(join_impls):
    result = _run(JOIN)
    assert result.terminals == {"Merge": "L[seed(x)]+R[seed(x)]"}
    assert result.order.count("Merge") == 1
    assert result.received["Merge"] == ("L[seed(x)]", "R[seed(x)]")


def test_arrival_order_does_not_change_the_output_or_the_trace(join_impls):
    """The same graph with its edges — and so the order values arrive at the join
    — listed every which way: the output and the whole trace are identical."""
    baseline = _run(JOIN)
    reversed_edges = _with(JOIN, data_edges=list(reversed(JOIN["data_edges"])))
    reversed_nodes = _with(JOIN, nodes=list(reversed(JOIN["nodes"])))
    for variant in (reversed_edges, reversed_nodes):
        result = _run(variant)
        assert result.terminals == baseline.terminals
        assert result.order == baseline.order
        assert result.trace.to_dict() == baseline.trace.to_dict()


def test_swapping_the_positions_swaps_the_arguments(join_impls):
    """Position is what an edge names, so renaming it is a real change — the
    opposite of the arrival-order case above."""
    swapped = copy.deepcopy(JOIN)
    swapped["nodes"][3]["inputs"] = ["B", "A"]
    swapped["data_edges"][2]["to_input"] = 1
    swapped["data_edges"][3]["to_input"] = 0
    assert _run(swapped).terminals == {"Merge": "R[seed(x)]+L[seed(x)]"}


def test_a_join_precondition_reads_its_inputs_by_position(join_impls):
    graph = copy.deepcopy(JOIN)
    graph["nodes"][3]["requires"] = ["len(in0) > 0", "len(in1) > 100"]
    with pytest.raises(ContractViolation) as caught:
        _run(graph)
    assert caught.value.predicate == "len(in1) > 100" and caught.value.blame == "caller"


def test_the_trace_of_a_join_is_schema_valid(join_impls):
    assert validate_document(_run(JOIN).trace.to_dict()) == []


# ── What validation rejects about a join ─────────────────────────────


def _errors_without(graph: dict, mutate) -> list[str]:
    g = copy.deepcopy(graph)
    mutate(g)
    return validate_graph_dict(g)


def test_an_edge_into_a_join_must_name_its_position():
    errors = _errors_without(JOIN, lambda g: g["data_edges"][2].pop("to_input"))
    assert any("must name its join position" in e for e in errors), errors


def test_a_join_position_no_edge_feeds_is_rejected():
    errors = _errors_without(JOIN, lambda g: g["data_edges"].pop(3))
    assert any("join position 1 of node 'Merge'" in e and "0 edges" in e for e in errors), errors


def test_two_edges_into_one_join_position_are_rejected():
    def mutate(g):
        g["nodes"].append({"name": "AlsoLeft", "inputs": ["Seed"], "output": "A"})
        g["data_edges"] += [
            {"from": "Split", "to": "AlsoLeft"},
            {"from": "AlsoLeft", "to": "Merge", "to_input": 0},
        ]

    errors = _errors_without(JOIN, mutate)
    assert any("join position 0" in e and "2 edges" in e for e in errors), errors


def test_a_position_out_of_range_is_rejected():
    errors = _errors_without(JOIN, lambda g: g["data_edges"][3].__setitem__("to_input", 2))
    assert any("names join position 2" in e for e in errors), errors


def test_a_position_is_type_checked_against_its_own_input():
    def mutate(g):  # feed B into the A position and A into the B position
        g["data_edges"][2]["to_input"], g["data_edges"][3]["to_input"] = 1, 0

    errors = _errors_without(JOIN, mutate)
    assert sum("type mismatch" in e for e in errors) == 2, errors


EXCLUSIVE = {
    "name": "NeverFires",
    "parameters": ["Req"],
    "capabilities": [],
    "nodes": [
        {"name": "Decide", "inputs": ["Req"], "output": "yes: A | no: B"},
        {"name": "OnYes", "inputs": ["A"], "output": "A2"},
        {"name": "OnNo", "inputs": ["B"], "output": "B2"},
        {"name": "Merge", "inputs": ["A2", "B2"], "output": "Done"},
    ],
    "data_edges": [
        {"from": "Decide.yes", "to": "OnYes"},
        {"from": "Decide.no", "to": "OnNo"},
        {"from": "OnYes", "to": "Merge", "to_input": 0},
        {"from": "OnNo", "to": "Merge", "to_input": 1},
    ],
}


def test_a_join_across_mutually_exclusive_branches_is_rejected():
    errors = validate_graph_dict(EXCLUSIVE)
    assert any("mutually exclusive branches of 'Decide'" in e for e in errors), errors
    with pytest.raises(AssemblyError):
        assemble(EXCLUSIVE, backend=StubLLM())


def test_a_join_within_one_branch_is_accepted():
    graph = copy.deepcopy(EXCLUSIVE)
    graph["nodes"][2] = {"name": "OnNo", "inputs": ["B"], "output": "Done"}
    graph["nodes"].insert(2, {"name": "AlsoYes", "inputs": ["A"], "output": "B2"})
    graph["data_edges"] = [
        {"from": "Decide.yes", "to": "OnYes"},
        {"from": "Decide.yes", "to": "AlsoYes"},
        {"from": "Decide.no", "to": "OnNo"},
        {"from": "OnYes", "to": "Merge", "to_input": 0},
        {"from": "AlsoYes", "to": "Merge", "to_input": 1},
    ]
    assert validate_graph_dict(graph) == []


# A join one of whose positions is conditional: it fires on some runs only.
HALF = {
    "name": "SometimesFires",
    "parameters": ["Req"],
    "capabilities": [],
    "nodes": [
        {"name": "Split", "inputs": ["Req"], "output": "Seed"},
        {"name": "Decide", "inputs": ["Seed"], "output": "yes: A | no: B"},
        {"name": "OnNo", "inputs": ["B"], "output": "Done"},
        {"name": "Side", "inputs": ["Seed"], "output": "S"},
        {"name": "Merge", "inputs": ["A", "S"], "output": "Done"},
    ],
    "data_edges": [
        {"from": "Split", "to": "Decide"},
        {"from": "Split", "to": "Side"},
        {"from": "Decide.yes", "to": "Merge", "to_input": 0},
        {"from": "Decide.no", "to": "OnNo"},
        {"from": "Side", "to": "Merge", "to_input": 1},
    ],
}


def test_a_run_that_ends_with_a_join_still_waiting_is_refused(monkeypatch):
    """Validation accepts this graph: the join can fire. On a run where it does
    not, the value it holds is not dropped silently — the run is refused."""
    assert validate_graph_dict(HALF) == []
    answers = iter(["yes", "no"])
    for name, impl in {
        "Split": lambda req: req,
        "Decide": lambda seed: Variant(next(answers), seed),
        "OnNo": lambda b: "declined",
        "Side": lambda seed: "side",
        "Merge": lambda a, s: f"{a}+{s}",
    }.items():
        monkeypatch.setitem(REGISTRY, name, impl)
    assert _run(HALF).terminals == {"Merge": "x+side"}
    with pytest.raises(ExecutionError, match=r"join still waiting.*'Merge'"):
        _run(HALF)


def test_a_second_arrival_at_one_input_is_still_refused(monkeypatch):
    """Merging two streams into one position stays out: which arrived first would
    decide the result."""
    graph = {
        "name": "Merges",
        "parameters": ["Req"],
        "capabilities": [],
        "nodes": [
            {"name": "Split", "inputs": ["Req"], "output": "Seed"},
            {"name": "Left", "inputs": ["Seed"], "output": "A"},
            {"name": "Right", "inputs": ["Seed"], "output": "A"},
            {"name": "Sink", "inputs": ["A"], "output": "Done"},
        ],
        "data_edges": [
            {"from": "Split", "to": "Left"},
            {"from": "Split", "to": "Right"},
            {"from": "Left", "to": "Sink"},
            {"from": "Right", "to": "Sink"},
        ],
    }
    for name in ("Split", "Left", "Right", "Sink"):
        monkeypatch.setitem(REGISTRY, name, lambda v: v)
    with pytest.raises(ExecutionError, match="would run a second time"):
        _run(graph)


# ── The trust meet at a join ─────────────────────────────────────────


def _trust_join(output: str, *, discharges: bool = False) -> dict:
    merge = {"name": "Merge", "inputs": ["A", "Untrusted<B>", "C"], "output": output}
    if discharges:
        merge["discharges_trust"] = True
    return {
        "name": "TrustJoin",
        "parameters": ["Req"],
        "capabilities": [],
        "nodes": [
            {"name": "Split", "inputs": ["Req"], "output": "Seed"},
            {"name": "Clean1", "inputs": ["Seed"], "output": "A"},
            {"name": "Tainted", "inputs": ["Seed"], "output": "Untrusted<B>"},
            {"name": "Clean2", "inputs": ["Seed"], "output": "C"},
            merge,
        ],
        "data_edges": [
            {"from": "Split", "to": "Clean1"},
            {"from": "Split", "to": "Tainted"},
            {"from": "Split", "to": "Clean2"},
            {"from": "Clean1", "to": "Merge", "to_input": 0},
            {"from": "Tainted", "to": "Merge", "to_input": 1},
            {"from": "Clean2", "to": "Merge", "to_input": 2},
        ],
    }


def test_one_untrusted_input_among_clean_ones_taints_the_join():
    errors = validate_graph_dict(_trust_join("Done"))
    assert any("'Merge' raises trust without discharging" in e for e in errors), errors


def test_a_tainted_join_with_an_untrusted_output_is_accepted():
    assert validate_graph_dict(_trust_join("Untrusted<Done>")) == []


def test_a_tainted_join_may_emit_clean_only_as_a_declared_discharger():
    assert validate_graph_dict(_trust_join("Done", discharges=True)) == []


def test_the_trace_labels_a_joins_input_by_the_meet(monkeypatch):
    for name, impl in {
        "Split": lambda req: req,
        "Clean1": lambda s: "a",
        "Tainted": lambda s: Untrusted("b"),
        "Clean2": lambda s: "c",
        "Merge": lambda a, b, c: Untrusted(f"{a}{b.value}{c}"),
    }.items():
        monkeypatch.setitem(REGISTRY, name, impl)
    result = _run(_trust_join("Untrusted<Done>"))
    merge = next(n for n in result.trace.nodes if n.node == "Merge")
    assert (merge.input_trust, merge.output_trust) == ("untrusted", "untrusted")


# ── The per-item map ─────────────────────────────────────────────────

CHILD = {
    "name": "PerItem",
    "parameters": ["Untrusted<Item>"],
    "capabilities": [],
    "nodes": [
        {
            "name": "Judge",
            "inputs": ["Untrusted<Item>"],
            "output": "Verdict",
            "discharges_trust": True,
        }
    ],
    "data_edges": [],
}

PARENT = {
    "name": "MapDemo",
    "parameters": ["Req"],
    "capabilities": [],
    "nodes": [
        {"name": "Gather", "inputs": ["Req"], "output": "List<Untrusted<Item>>"},
        {
            "name": "PerItem",
            "inputs": ["List<Untrusted<Item>>"],
            "output": "List<Verdict>",
            "each": True,
            "discharges_trust": True,
        },
        {"name": "Collect", "inputs": ["List<Verdict>"], "output": "Done"},
    ],
    "data_edges": [
        {"from": "Gather", "to": "PerItem"},
        {"from": "PerItem", "to": "Collect"},
    ],
}

GRAPHS = {"PerItem": CHILD}


@pytest.fixture
def map_impls(monkeypatch):
    seen: list[object] = []

    def judge(item):
        seen.append(item)
        if item.value == "boom":
            raise RuntimeError("cannot judge this one")
        return f"ok:{item.value}"

    for name, impl in {
        "Gather": lambda req: tuple(Untrusted(x) for x in req),
        "Judge": judge,
        "Collect": lambda verdicts: list(verdicts),
    }.items():
        monkeypatch.setitem(REGISTRY, name, impl)
    return seen


def test_a_map_validates_against_its_child():
    assert validate_graph_dicts([PARENT, CHILD]) == []


def test_three_elements_run_three_isolated_child_runs_in_order(map_impls):
    result = _run(PARENT, ["a", "b", "c"], graphs=GRAPHS)
    assert result.terminals == {"Collect": ["ok:a", "ok:b", "ok:c"]}
    runs = result.elements["PerItem"]
    assert len(runs) == 3
    # No node in any child run received more than one element.
    assert [r.received for r in runs] == [
        {"Judge": Untrusted("a")},
        {"Judge": Untrusted("b")},
        {"Judge": Untrusted("c")},
    ]
    assert result.tiers["PerItem"] == "graph"


def test_an_empty_list_runs_no_child_and_emits_an_empty_list(map_impls):
    result = _run(PARENT, [], graphs=GRAPHS)
    assert result.terminals == {"Collect": []}
    assert result.elements["PerItem"] == [] and map_impls == []


def test_a_failing_element_fails_the_run_naming_its_index(map_impls):
    with pytest.raises(ExecutionError, match="element 1 of per-item node 'PerItem' failed"):
        _run(PARENT, ["a", "boom", "c"], graphs=GRAPHS)
    # The third element was never started, and nothing was emitted downstream.
    assert [i.value for i in map_impls] == ["a", "boom"]


def test_the_trace_nests_one_run_per_element(map_impls):
    result = _run(PARENT, ["a", "b"], graphs=GRAPHS)
    document = result.trace.to_dict()
    assert validate_document(document) == []
    node = document["nodes"][1]
    assert node["node"] == "PerItem" and "subgraph" not in node
    assert [run["nodes"][0]["node"] for run in node["elements"]] == ["Judge", "Judge"]
    # Trust rises inside each child run, at the child's discharger.
    assert [n.node for n in result.trace.walk() if n.raises_trust()] == [
        "PerItem",
        "Judge",
        "Judge",
    ]


def test_each_on_a_node_that_names_no_graph_is_refused_at_run_time(map_impls, monkeypatch):
    monkeypatch.setitem(REGISTRY, "PerItem", lambda items: items)
    with pytest.raises(ExecutionError, match="names no graph"):
        _run(PARENT, ["a"], graphs={})


def test_a_per_item_node_must_take_and_emit_lists():
    bad_in = copy.deepcopy(PARENT)
    bad_in["nodes"][0]["output"] = "Untrusted<Item>"
    bad_in["nodes"][1]["inputs"] = ["Untrusted<Item>"]
    assert any(
        "must take exactly one data input, a `List<_>`" in e for e in validate_graph_dict(bad_in)
    )
    bad_out = copy.deepcopy(PARENT)
    bad_out["nodes"][1]["output"] = "Verdict"
    bad_out["nodes"][2]["inputs"] = ["Verdict"]
    assert any("must emit a `List<_>`" in e for e in validate_graph_dict(bad_out))


def test_a_map_whose_element_type_is_not_the_childs_input_is_rejected():
    parent = copy.deepcopy(PARENT)
    parent["nodes"][0]["output"] = "List<Untrusted<Other>>"
    parent["nodes"][1]["inputs"] = ["List<Untrusted<Other>>"]
    errors = validate_graph_dicts([parent, CHILD])
    assert any("is not a list of 'Untrusted<Item>'" in e for e in errors), errors


def test_a_map_cannot_drop_the_elements_trust_label_on_the_way_in():
    """`List<Item>` into a child taking `Untrusted<Item>` is a different type, not
    a narrowing: the element-wise check is equality, trust included."""
    parent = copy.deepcopy(PARENT)
    parent["nodes"][0]["output"] = "List<Item>"
    parent["nodes"][1] = {
        "name": "PerItem",
        "inputs": ["List<Item>"],
        "output": "List<Verdict>",
        "each": True,
    }
    errors = validate_graph_dicts([parent, CHILD])
    assert any("is not a list of 'Untrusted<Item>'" in e for e in errors), errors


def test_a_map_cannot_launder_trust_past_its_child():
    """The child emits `Untrusted<Verdict>` and holds no discharger; the parent
    declares clean elements. Only a discharger inside the child can raise an
    element's trust, so the boundary types disagree and the graph is rejected."""
    child = copy.deepcopy(CHILD)
    child["nodes"][0] = {
        "name": "Judge",
        "inputs": ["Untrusted<Item>"],
        "output": "Untrusted<Verdict>",
    }
    errors = validate_graph_dicts([PARENT, child])
    assert any("does not match the union" in e and "Untrusted<Verdict>" in e for e in errors), (
        errors
    )


def test_the_runtime_refuses_a_map_the_validator_rejects(map_impls):
    child = copy.deepcopy(CHILD)
    child["nodes"][0] = {
        "name": "Judge",
        "inputs": ["Untrusted<Item>"],
        "output": "Untrusted<Verdict>",
    }
    with pytest.raises(AssemblyError):
        _run(PARENT, ["a"], graphs={"PerItem": child})
    assert map_impls == []
