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

from graph_validator import validate_files


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
        files = sorted(p for p in (root / "graphs").glob("*.json") if p.name != "schema.json")
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
            bad["nodes"][1]["output"] = "ok: WrongType | error: ValidationError"
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
                    "consumes an `Untrusted<_>` input but emits a non-`Untrusted` output" in e
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
            good["data_edges"].append({"from": "Ingest", "to": "PassThrough"})
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
            good["data_edges"].append({"from": "PassThrough", "to": "SanitiseTwice"})
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
            bad["data_edges"] = [e for e in bad["data_edges"] if e["from"] != "Sanitise.error"]
            # Also drop Report, the now-orphan consumer, so we don't
            # also trigger an unrelated "unused data input" error.
            bad["nodes"] = [n for n in bad["nodes"] if n["name"] != "Report"]
            paths = _write({"broken.json": bad}, Path(td))
            errors = validate_files(paths)
            self.assertTrue(
                any("variant 'error' but no edge consumes it" in e for e in errors),
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

    def test_http_superset_allowlist_passes(self):
        """A parent may route an HTTP handle whose allowlist is a superset of
        what the sub-graph declares — the first narrowing over a scope that is
        a set rather than a mode or a name."""
        errors = self._run(
            child_param="HTTPClient<['feeds.example.com']>",
            parent_passed="HTTPClient<['feeds.example.com', 'blog.example.net']>",
        )
        cross_errors = [e for e in errors if "sub-graph" in e]
        self.assertEqual(cross_errors, [], msg=f"All errors: {errors}")

    def test_http_subset_allowlist_fails(self):
        """Scenario: a parent cannot route a narrower allowlist than the child
        declares — composition must not grant a child reach the parent's own
        handle does not have."""
        errors = self._run(
            child_param="HTTPClient<['feeds.example.com', 'blog.example.net']>",
            parent_passed="HTTPClient<['feeds.example.com']>",
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
            paths = _write({"child.json": child, "parent.json": parent}, Path(td))
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
            paths = _write({"child.json": child, "parent.json": parent}, Path(td))
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
            paths = _write({"child.json": child, "parent.json": parent}, Path(td))
            self.assertEqual(validate_files(paths), [])


class TestCrossGraphOutputCheck(unittest.TestCase):
    """The output half of the sub-graph signature check. A sub-graph node's declared
    boundary output must equal the union of the referenced graph's terminal output
    types — the check that closes the `ServiceOutcome` gap. Structural, not nominal:
    the graph spells the union, and the check compares member sets."""

    def _multi_terminal_child(self) -> dict:
        """A child whose two exclusive branches terminate at different types, so its
        honest boundary output is the union `Delivered | Escalated`."""
        return {
            "name": "Service",
            "parameters": ["Request", "DBHandle<'x', read>"],
            "capabilities": ["DBHandle<'x', read>"],
            "nodes": [
                {
                    "name": "Route",
                    "inputs": ["Request", "DBHandle<'x', read>"],
                    "output": "reply: Answer | escalate: Answer",
                },
                {"name": "Reply", "inputs": ["Answer"], "output": "Delivered"},
                {"name": "Escalate", "inputs": ["Answer"], "output": "Escalated"},
            ],
            "data_edges": [
                {"from": "Route.reply", "to": "Reply"},
                {"from": "Route.escalate", "to": "Escalate"},
            ],
        }

    def _parent(self, declared_output: str) -> dict:
        return {
            "name": "Platform",
            "parameters": ["Request", "DBHandle<'x', read>", "DBHandle<'log', append>"],
            "capabilities": ["DBHandle<'x', read>", "DBHandle<'log', append>"],
            "nodes": [
                {
                    "name": "Service",
                    "inputs": ["Request", "DBHandle<'x', read>"],
                    "output": declared_output,
                },
                {
                    "name": "Record",
                    "inputs": [declared_output, "DBHandle<'log', append>"],
                    "output": "Logged",
                },
            ],
            "data_edges": [{"from": "Service", "to": "Record"}],
        }

    def _run(self, child: dict, parent: dict) -> list[str]:
        with tempfile.TemporaryDirectory() as td:
            paths = _write({"child.json": child, "parent.json": parent}, Path(td))
            return validate_files(paths)

    def test_honest_union_output_passes(self):
        """Scenario: the canonical graphs still validate. The sub-graph node declares
        the union of the child's terminals, so nothing objects."""
        errors = self._run(self._multi_terminal_child(), self._parent("Delivered | Escalated"))
        self.assertEqual(errors, [], msg=f"unexpected errors: {errors}")

    def test_union_output_is_order_insensitive(self):
        """Structural, not textual: the members are compared as a set, so reversing
        the union still validates."""
        errors = self._run(self._multi_terminal_child(), self._parent("Escalated | Delivered"))
        self.assertEqual(errors, [], msg=f"unexpected errors: {errors}")

    def test_narrowed_output_rejected_without_edge_mismatch(self):
        """Scenario: a mismatched declared output is rejected at assembly time. The
        node claims only `Delivered`, hiding the escalation terminal. Every edge still
        type-checks (the `Record` input is narrowed in lockstep), so the rejection is
        the output-side cross-graph check, not an edge type mismatch."""
        errors = self._run(self._multi_terminal_child(), self._parent("Delivered"))
        self.assertTrue(
            any("declared output" in e and "terminal output types" in e for e in errors),
            msg=f"expected output-side cross-graph rejection; got: {errors}",
        )
        self.assertFalse(
            any("type mismatch" in e for e in errors),
            msg=f"should not be caught as an edge type mismatch; got: {errors}",
        )

    def test_widened_output_rejected(self):
        """An output claiming *more* than the terminals emit is equally a lie: the
        member sets differ, so the union with a spurious extra member is rejected."""
        errors = self._run(
            self._multi_terminal_child(), self._parent("Delivered | Escalated | Extra")
        )
        self.assertTrue(
            any("declared output" in e and "terminal output types" in e for e in errors),
            msg=f"expected output-side rejection of the widened union; got: {errors}",
        )


class TestCapabilityIdentities(unittest.TestCase):
    """Graph-source capability identity: a node may name a distinct instance of a
    capability it holds. The validator's sole semantic rule mirrors the runtime's
    assembly-time rejection — an identity may be declared only for a capability the
    node's `inputs` names."""

    def _graph_with_identity(self, node_name: str, cap: str, label: str) -> dict:
        g = _good_single_graph()
        for n in g["nodes"]:
            if n["name"] == node_name:
                n["capability_identities"] = {cap: label}
        return g

    def _run(self, graph: dict) -> list[str]:
        with tempfile.TemporaryDirectory() as td:
            paths = _write({"g.json": graph}, Path(td))
            return validate_files(paths)

    def test_valid_identity_accepted(self):
        # `Store` holds `DBHandle<'store', read>`; naming an instance of it is fine.
        errors = self._run(self._graph_with_identity("Store", "DBHandle<'store', read>", "primary"))
        self.assertEqual(errors, [], msg=f"unexpected errors: {errors}")

    def test_identity_for_unheld_capability_rejected(self):
        # `Ingest` does not hold the DB capability, so an identity for it is invalid.
        errors = self._run(self._graph_with_identity("Ingest", "DBHandle<'store', read>", "x"))
        self.assertTrue(
            any("does not hold" in e for e in errors),
            msg=f"expected unheld-capability rejection; got: {errors}",
        )

    def test_identity_for_unknown_capability_rejected(self):
        errors = self._run(self._graph_with_identity("Store", "DBHandle<'nope', read>", "x"))
        self.assertTrue(
            any("not a declared capability" in e for e in errors),
            msg=f"expected unknown-capability rejection; got: {errors}",
        )

    def test_malformed_identity_field_rejected(self):
        g = _good_single_graph()
        for n in g["nodes"]:
            if n["name"] == "Store":
                n["capability_identities"] = ["not", "a", "map"]
        self.assertTrue(
            any("must be an object" in e for e in self._run(g)),
            msg="expected shape rejection for a non-object identity field",
        )

    def test_empty_identity_label_rejected(self):
        errors = self._run(self._graph_with_identity("Store", "DBHandle<'store', read>", ""))
        self.assertTrue(
            any("must be a non-empty string" in e for e in errors),
            msg=f"expected empty-label rejection; got: {errors}",
        )

    def test_no_identity_declaration_is_clean(self):
        """A graph with no identity declarations validates exactly as before."""
        self.assertEqual(self._run(_good_single_graph()), [])


class TestTrustLattice(unittest.TestCase):
    """The two-point trust lattice (`Untrusted ⊑ Trusted`) exercised
    directly: an edge is rejected exactly when it demands more trust
    than the source supplies (upward coercion), and a node body may
    raise trust only when it is a declared discharger. Both halves use
    the same lattice order, so these tables pin the whole discipline."""

    UNTRUSTED = "Untrusted<Payload>"
    TRUSTED = "Payload"

    def _two_node_edge(self, src_out: str, tgt_in: str) -> list[str]:
        """A Src → Tgt graph with the given source-output and
        target-input types. Tgt always emits `Untrusted<Result>` so its
        own body never raises trust — isolating the *edge* check."""
        graph = {
            "name": "Pipeline",
            "parameters": ["RawInput"],
            "capabilities": [],
            "nodes": [
                {"name": "Src", "inputs": ["RawInput"], "output": src_out},
                {"name": "Tgt", "inputs": [tgt_in], "output": "Untrusted<Result>"},
            ],
            "data_edges": [{"from": "Src", "to": "Tgt"}],
        }
        with tempfile.TemporaryDirectory() as td:
            paths = _write({"pipeline.json": graph}, Path(td))
            return validate_files(paths)

    def _lattice_errors(self, errors: list[str]) -> list[str]:
        return [e for e in errors if "upward coercion" in e or "laundering" in e]

    def test_edge_trust_matrix(self):
        """Data shapes match in every cell (both carry `Payload`); only
        the trust levels vary. Upward coercion — untrusted source into a
        clean requirement — is the single rejected cell."""
        cases = [
            # (src_out, tgt_in, should_reject)
            (self.TRUSTED, self.TRUSTED, False),  # clean → clean
            (self.TRUSTED, self.UNTRUSTED, False),  # clean → untrusted (forget trust)
            (self.UNTRUSTED, self.UNTRUSTED, False),  # untrusted → untrusted (carry)
            (self.UNTRUSTED, self.TRUSTED, True),  # untrusted → clean: UPWARD COERCION
        ]
        for src_out, tgt_in, should_reject in cases:
            with self.subTest(src=src_out, tgt=tgt_in):
                errors = self._two_node_edge(src_out, tgt_in)
                lattice = self._lattice_errors(errors)
                # No case should ever be a plain data-type mismatch: the
                # carried shapes are equal, so trust is the only variable.
                self.assertFalse(
                    any("type mismatch" in e for e in errors),
                    msg=f"unexpected data mismatch; errors: {errors}",
                )
                if should_reject:
                    self.assertTrue(lattice, msg=f"expected upward-coercion error; got: {errors}")
                else:
                    self.assertEqual(lattice, [], msg=f"unexpected trust error; got: {errors}")

    def _single_node(self, in_t: str, out_t: str, discharges: bool) -> list[str]:
        node = {"name": "Only", "inputs": [in_t], "output": out_t}
        if discharges:
            node["discharges_trust"] = True
        graph = {
            "name": "G",
            "parameters": [in_t],
            "capabilities": [],
            "nodes": [node],
            "data_edges": [],
        }
        with tempfile.TemporaryDirectory() as td:
            paths = _write({"g.json": graph}, Path(td))
            return validate_files(paths)

    def test_node_body_trust_matrix(self):
        """A node raises trust only legitimately at a declared discharger;
        every other upward move is a lattice violation, and a discharger
        with nothing to discharge is flagged as an unused annotation."""
        U, T = self.UNTRUSTED, self.TRUSTED
        # (in, out, discharges) -> substring expected in errors, or None
        cases = [
            (U, T, False, "upward coercion"),  # launder: untrusted → clean, no discharge
            (U, T, True, None),  # legitimate discharge
            (U, U, False, None),  # pass-through untrusted
            (T, T, False, None),  # clean → clean
            (T, U, False, None),  # clean → untrusted (adding restriction is free)
            (T, T, True, "annotation is unused"),  # discharger with no untrusted input
        ]
        for in_t, out_t, discharges, expected in cases:
            with self.subTest(in_t=in_t, out_t=out_t, discharges=discharges):
                errors = self._single_node(in_t, out_t, discharges)
                trust = [
                    e
                    for e in errors
                    if "upward coercion" in e or "laundering" in e or "annotation is unused" in e
                ]
                if expected is None:
                    self.assertEqual(trust, [], msg=f"unexpected trust error; got: {errors}")
                else:
                    self.assertTrue(
                        any(expected in e for e in trust),
                        msg=f"expected {expected!r}; got: {errors}",
                    )

    def test_discharger_mediated_flow_is_accepted(self):
        """An untrusted source reaching a clean consumer *through* a
        declared discharger is fully well-typed — the discharge is the
        sanctioned upward move the lattice provides."""
        graph = {
            "name": "Mediated",
            "parameters": ["RawInput"],
            "capabilities": [],
            "nodes": [
                {"name": "Src", "inputs": ["RawInput"], "output": "Untrusted<Payload>"},
                {
                    "name": "Discharge",
                    "inputs": ["Untrusted<Payload>"],
                    "output": "CleanPayload",
                    "discharges_trust": True,
                },
                {"name": "Sink", "inputs": ["CleanPayload"], "output": "Receipt"},
            ],
            "data_edges": [
                {"from": "Src", "to": "Discharge"},
                {"from": "Discharge", "to": "Sink"},
            ],
        }
        with tempfile.TemporaryDirectory() as td:
            paths = _write({"mediated.json": graph}, Path(td))
            self.assertEqual(validate_files(paths), [])

    def test_random_labellings_reject_exactly_upward_coercion(self):
        """Property check: over many random two-node trust labellings with
        matching data shapes, an edge is rejected on trust grounds iff it
        is an upward-coercion edge (untrusted source, clean requirement)."""
        import random

        rng = random.Random(20260715)
        levels = [self.TRUSTED, self.UNTRUSTED]
        for _ in range(60):
            src_out = rng.choice(levels)
            tgt_in = rng.choice(levels)
            is_upward = src_out == self.UNTRUSTED and tgt_in == self.TRUSTED
            errors = self._two_node_edge(src_out, tgt_in)
            lattice = self._lattice_errors(errors)
            self.assertEqual(
                bool(lattice),
                is_upward,
                msg=f"src={src_out} tgt={tgt_in} upward={is_upward}; errors={errors}",
            )


if __name__ == "__main__":
    unittest.main()
