"""Tests for scripts/graph_validator.py.

Each test builds graph dicts in memory, writes them to a temp
directory, and invokes the validator. Good-path fixtures confirm
the checks accept valid graphs; broken-path fixtures confirm the
checks surface the expected error class.
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from graph_validator import validate_files  # noqa: E402


def _good_single_graph() -> dict:
    """A minimal valid graph that exercises trust propagation and
    sum-type addressing without relying on the canonical graphs."""
    return {
        "name": "Pipeline",
        "parameters": ["RawInput", "DBHandle<'store', read>"],
        "capabilities": ["DBHandle<'store', read>"],
        "nodes": [
            {
                "name": "Ingest",
                "inputs": ["RawInput"],
                "output": "Untrusted<Payload>",
            },
            {
                "name": "Sanitise",
                "inputs": ["Untrusted<Payload>"],
                "output": "ok: CleanPayload | error: ValidationError",
                "discharges_trust": True,
            },
            {
                "name": "Store",
                "inputs": ["CleanPayload", "DBHandle<'store', read>"],
                "output": "StoreReceipt",
            },
            {
                "name": "Report",
                "inputs": ["ValidationError"],
                "output": "ErrorReport",
            },
        ],
        "data_edges": [
            {"from": "Ingest", "to": "Sanitise"},
            {"from": "Sanitise.ok", "to": "Store"},
            {"from": "Sanitise.error", "to": "Report"},
        ],
    }


def _write(graphs: dict[str, dict], tmp: Path) -> list[Path]:
    """Write each graph dict into tmp/<name>.json and return paths."""
    paths = []
    for filename, graph in graphs.items():
        p = tmp / filename
        p.write_text(json.dumps(graph))
        paths.append(p)
    return paths


class TestAcceptsGoodGraphs(unittest.TestCase):
    def test_canonical_graphs_pass(self):
        """The two canonical graphs in the proposal must validate."""
        root = Path(__file__).resolve().parent.parent
        files = sorted(
            p for p in (root / "graphs").glob("*.json") if p.name != "schema.json"
        )
        self.assertEqual(validate_files(files), [])

    def test_synthetic_good_graph_passes(self):
        with tempfile.TemporaryDirectory() as td:
            paths = _write({"pipeline.json": _good_single_graph()}, Path(td))
            self.assertEqual(validate_files(paths), [])


class TestStructuralChecks(unittest.TestCase):
    def test_missing_required_field(self):
        with tempfile.TemporaryDirectory() as td:
            bad = _good_single_graph()
            del bad["nodes"]
            paths = _write({"broken.json": bad}, Path(td))
            errors = validate_files(paths)
            self.assertTrue(any("missing required field: nodes" in e for e in errors))

    def test_capability_not_in_parameters(self):
        with tempfile.TemporaryDirectory() as td:
            bad = _good_single_graph()
            bad["capabilities"] = ["DBHandle<'other', read>"]
            paths = _write({"broken.json": bad}, Path(td))
            errors = validate_files(paths)
            self.assertTrue(any("not listed in parameters" in e for e in errors))

    def test_unused_capability(self):
        with tempfile.TemporaryDirectory() as td:
            bad = _good_single_graph()
            bad["parameters"].append("EventEmitter<'unused'>")
            bad["capabilities"].append("EventEmitter<'unused'>")
            paths = _write({"broken.json": bad}, Path(td))
            errors = validate_files(paths)
            self.assertTrue(
                any("declared but never used" in e for e in errors),
                msg=f"Expected unused-capability error; got: {errors}",
            )


class TestEdgeTypeCompatibility(unittest.TestCase):
    def test_edge_type_mismatch_flagged(self):
        with tempfile.TemporaryDirectory() as td:
            bad = _good_single_graph()
            # Break the Sanitise → Store edge by renaming the variant type
            bad["nodes"][1]["output"] = (
                "ok: WrongType | error: ValidationError"
            )
            paths = _write({"broken.json": bad}, Path(td))
            errors = validate_files(paths)
            self.assertTrue(
                any("type mismatch" in e for e in errors),
                msg=f"Expected edge-type mismatch error; got: {errors}",
            )

    def test_unknown_port(self):
        with tempfile.TemporaryDirectory() as td:
            bad = _good_single_graph()
            bad["data_edges"][1]["from"] = "Sanitise.typo"
            paths = _write({"broken.json": bad}, Path(td))
            errors = validate_files(paths)
            self.assertTrue(
                any("addresses unknown port" in e for e in errors),
                msg=f"Expected unknown-port error; got: {errors}",
            )

    def test_edge_on_non_sum_output_with_port(self):
        with tempfile.TemporaryDirectory() as td:
            bad = _good_single_graph()
            # Ingest has a non-sum output; addressing a port on it is wrong
            bad["data_edges"][0]["from"] = "Ingest.anything"
            paths = _write({"broken.json": bad}, Path(td))
            errors = validate_files(paths)
            self.assertTrue(
                any("is not a sum type" in e for e in errors),
                msg=f"Expected non-sum-type error; got: {errors}",
            )


class TestTrustPropagation(unittest.TestCase):
    def test_implicit_discharge_flagged(self):
        with tempfile.TemporaryDirectory() as td:
            bad = _good_single_graph()
            # Remove the discharges_trust flag from Sanitise
            del bad["nodes"][1]["discharges_trust"]
            paths = _write({"broken.json": bad}, Path(td))
            errors = validate_files(paths)
            self.assertTrue(
                any(
                    "consumes an `Untrusted<_>` input but emits a non-`Untrusted` output"
                    in e
                    for e in errors
                ),
                msg=f"Expected trust-discharge error; got: {errors}",
            )

    def test_stale_discharge_annotation_flagged(self):
        with tempfile.TemporaryDirectory() as td:
            bad = _good_single_graph()
            # Mark a node as discharging trust when it has no untrusted input
            bad["nodes"][2]["discharges_trust"] = True  # Store
            paths = _write({"broken.json": bad}, Path(td))
            errors = validate_files(paths)
            self.assertTrue(
                any("annotation is unused" in e for e in errors),
                msg=f"Expected stale-annotation error; got: {errors}",
            )

    def test_pass_through_untrusted_is_allowed(self):
        with tempfile.TemporaryDirectory() as td:
            good = _good_single_graph()
            # A node that carries Untrusted<T> through without discharging
            # should not need the flag.
            good["nodes"].append(
                {
                    "name": "PassThrough",
                    "inputs": ["Untrusted<Payload>"],
                    "output": "Untrusted<Payload>",
                }
            )
            # Wire it: the new node won't actually be reached in this
            # fixture but it must still typecheck.
            good["data_edges"].append(
                {"from": "Ingest", "to": "PassThrough"}
            )
            # Give PassThrough's output a consumer to keep the graph
            # internally consistent.
            good["nodes"].append(
                {
                    "name": "SanitiseTwice",
                    "inputs": ["Untrusted<Payload>"],
                    "output": "CleanPayload",
                    "discharges_trust": True,
                }
            )
            good["data_edges"].append(
                {"from": "PassThrough", "to": "SanitiseTwice"}
            )
            paths = _write({"ok.json": good}, Path(td))
            errors = validate_files(paths)
            # Filter out errors unrelated to trust (e.g. the new
            # SanitiseTwice output isn't consumed, which is fine here)
            trust_errors = [e for e in errors if "Untrusted" in e and "discharge" in e]
            self.assertEqual(trust_errors, [], msg=f"All errors: {errors}")


class TestVariantCompleteness(unittest.TestCase):
    def test_missing_variant_consumer_flagged(self):
        with tempfile.TemporaryDirectory() as td:
            bad = _good_single_graph()
            # Drop the edge that consumes the `error` variant
            bad["data_edges"] = [
                e for e in bad["data_edges"]
                if e["from"] != "Sanitise.error"
            ]
            # Also drop Report, the now-orphan consumer, so we don't
            # also trigger an unrelated "unused data input" error.
            bad["nodes"] = [n for n in bad["nodes"] if n["name"] != "Report"]
            paths = _write({"broken.json": bad}, Path(td))
            errors = validate_files(paths)
            self.assertTrue(
                any(
                    "variant 'error' but no edge consumes it" in e
                    for e in errors
                ),
                msg=f"Expected dead-variant error; got: {errors}",
            )

    def test_whole_output_consumed_unported_covers_all_variants(self):
        """If a downstream node consumes the full sum output (no port
        suffix), the validator should not flag individual variants as
        dead — they are all carried by the unported edge."""
        with tempfile.TemporaryDirectory() as td:
            graph = {
                "name": "Pipeline",
                "parameters": ["RawInput"],
                "capabilities": [],
                "nodes": [
                    {
                        "name": "Split",
                        "inputs": ["RawInput"],
                        "output": "a: AlphaPayload | b: BetaPayload",
                    },
                    {
                        "name": "Consumer",
                        "inputs": ["a: AlphaPayload | b: BetaPayload"],
                        "output": "Receipt",
                    },
                ],
                "data_edges": [{"from": "Split", "to": "Consumer"}],
            }
            paths = _write({"whole.json": graph}, Path(td))
            errors = validate_files(paths)
            variant_errors = [e for e in errors if "no edge consumes" in e]
            self.assertEqual(variant_errors, [], msg=f"All errors: {errors}")


class TestCrossGraphCapabilityNarrowing(unittest.TestCase):
    def _child_graph(self, param: str) -> dict:
        return {
            "name": "Child",
            "parameters": ["InTypeA", param],
            "capabilities": [param],
            "nodes": [
                {
                    "name": "Inner",
                    "inputs": ["InTypeA", param],
                    "output": "OutTypeA",
                }
            ],
            "data_edges": [],
        }

    def _parent_graph(self, passed: str) -> dict:
        return {
            "name": "Parent",
            "parameters": ["InTypeA", passed],
            "capabilities": [passed],
            "nodes": [
                {
                    "name": "Child",
                    "inputs": ["InTypeA", passed],
                    "output": "OutTypeA",
                }
            ],
            "data_edges": [],
        }

    def _run(self, child_param: str, parent_passed: str) -> list[str]:
        with tempfile.TemporaryDirectory() as td:
            paths = _write(
                {
                    "child.json": self._child_graph(child_param),
                    "parent.json": self._parent_graph(parent_passed),
                },
                Path(td),
            )
            return validate_files(paths)

    def test_wider_llm_tool_set_passes(self):
        errors = self._run(
            child_param="LLMClient<[lookup]>",
            parent_passed="LLMClient<[lookup, respond]>",
        )
        cross_errors = [e for e in errors if "sub-graph" in e]
        self.assertEqual(cross_errors, [], msg=f"All errors: {errors}")

    def test_narrower_llm_tool_set_fails(self):
        errors = self._run(
            child_param="LLMClient<[lookup, respond]>",
            parent_passed="LLMClient<[lookup]>",
        )
        self.assertTrue(
            any("is not assignable to expected" in e for e in errors),
            msg=f"Expected subtype failure; got: {errors}",
        )

    def test_db_read_write_passes_where_read_expected(self):
        errors = self._run(
            child_param="DBHandle<'kb', read>",
            parent_passed="DBHandle<'kb', read-write>",
        )
        cross_errors = [e for e in errors if "sub-graph" in e]
        self.assertEqual(cross_errors, [], msg=f"All errors: {errors}")

    def test_db_read_fails_where_read_write_expected(self):
        errors = self._run(
            child_param="DBHandle<'kb', read-write>",
            parent_passed="DBHandle<'kb', read>",
        )
        self.assertTrue(
            any("is not assignable to expected" in e for e in errors),
            msg=f"Expected subtype failure; got: {errors}",
        )

    def test_data_position_must_match_exactly(self):
        """Subtyping only applies to capability positions; data inputs
        still require strict equality."""
        with tempfile.TemporaryDirectory() as td:
            child = self._child_graph("DBHandle<'kb', read>")
            parent = self._parent_graph("DBHandle<'kb', read>")
            parent["nodes"][0]["inputs"][0] = "WrongType"
            paths = _write(
                {"child.json": child, "parent.json": parent}, Path(td)
            )
            errors = validate_files(paths)
            self.assertTrue(
                any("data type 'WrongType'" in e for e in errors),
                msg=f"Expected data mismatch; got: {errors}",
            )


class TestCrossGraphCheck(unittest.TestCase):
    def test_sub_graph_signature_mismatch_flagged(self):
        """If node X in graph A matches graph B's name, X's inputs
        must equal B's parameters."""
        with tempfile.TemporaryDirectory() as td:
            child = {
                "name": "Child",
                "parameters": ["InTypeA", "DBHandle<'x', read>"],
                "capabilities": ["DBHandle<'x', read>"],
                "nodes": [
                    {
                        "name": "Inner",
                        "inputs": ["InTypeA", "DBHandle<'x', read>"],
                        "output": "OutTypeA",
                    }
                ],
                "data_edges": [],
            }
            # Parent references Child but with a mismatched first input
            parent = {
                "name": "Parent",
                "parameters": ["InWrapper", "DBHandle<'x', read>"],
                "capabilities": ["DBHandle<'x', read>"],
                "nodes": [
                    {
                        "name": "Boundary",
                        "inputs": ["InWrapper"],
                        "output": "InTypeB",  # note: different type name
                    },
                    {
                        "name": "Child",
                        "inputs": ["InTypeB", "DBHandle<'x', read>"],
                        "output": "OutTypeA",
                    },
                ],
                "data_edges": [
                    {"from": "Boundary", "to": "Child"},
                ],
            }
            paths = _write(
                {"child.json": child, "parent.json": parent}, Path(td)
            )
            errors = validate_files(paths)
            self.assertTrue(
                any("used as a sub-graph" in e for e in errors),
                msg=f"Expected cross-graph signature error; got: {errors}",
            )

    def test_sub_graph_signature_match_passes(self):
        with tempfile.TemporaryDirectory() as td:
            child = {
                "name": "Child",
                "parameters": ["InTypeA", "DBHandle<'x', read>"],
                "capabilities": ["DBHandle<'x', read>"],
                "nodes": [
                    {
                        "name": "Inner",
                        "inputs": ["InTypeA", "DBHandle<'x', read>"],
                        "output": "OutTypeA",
                    }
                ],
                "data_edges": [],
            }
            parent = {
                "name": "Parent",
                "parameters": ["InTypeA", "DBHandle<'x', read>"],
                "capabilities": ["DBHandle<'x', read>"],
                "nodes": [
                    {
                        "name": "Child",
                        "inputs": ["InTypeA", "DBHandle<'x', read>"],
                        "output": "OutTypeA",
                    },
                ],
                "data_edges": [],
            }
            paths = _write(
                {"child.json": child, "parent.json": parent}, Path(td)
            )
            self.assertEqual(validate_files(paths), [])


if __name__ == "__main__":
    unittest.main()
