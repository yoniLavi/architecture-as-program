"""Tests for scripts/check-spec-restructure.py (change update-openspec-to-2).

A dropped normative sentence fails; a moved one passes; a reworded one fails.
"""

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load():
    spec = importlib.util.spec_from_file_location(
        "check_spec_restructure", ROOT / "scripts" / "check-spec-restructure.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


check = _load()

BEFORE = """\
### Requirement: Trust is not raised by coercion
The type system SHALL reject an untrusted value where a clean one is
required. A discharger MUST be declared. This sentence is not normative.

#### Scenario: Rejected
- **WHEN** an untrusted value is offered
- **THEN** it is rejected
"""

MOVED = """\
### Requirement: Trust is not raised by coercion
The type system SHALL reject an untrusted value where a clean one is required.

#### Scenario: Rejected
- **WHEN** an untrusted value is offered
- **THEN** it is rejected

#### Scenario: Declared discharger
- **WHEN** a node raises trust
- **THEN** A discharger MUST be declared.
"""


def test_moved_into_a_scenario_passes():
    assert check.missing(BEFORE, MOVED) == []


def test_dropped_sentence_fails():
    dropped = MOVED.replace("- **THEN** A discharger MUST be declared.\n", "")
    assert check.missing(BEFORE, dropped) == ["A discharger MUST be declared"]


def test_reworded_sentence_fails():
    reworded = MOVED.replace("A discharger MUST be declared", "A discharger SHALL be declared")
    assert check.missing(BEFORE, reworded) == ["A discharger MUST be declared"]


def test_non_normative_sentences_are_not_required():
    assert check.normative(BEFORE) == [
        "The type system SHALL reject an untrusted value where a clean one is required",
        "A discharger MUST be declared",
    ]


def test_requirement_names_are_not_sentences():
    text = "### Requirement: The runtime SHALL do a thing\nIt SHALL.\n"
    assert check.normative(text) == ["It SHALL"]


def test_main_exit_codes(tmp_path):
    before, after = tmp_path / "before.md", tmp_path / "after.md"
    before.write_text(BEFORE)
    after.write_text(MOVED)
    assert check.main(["x", str(before), str(after)]) == 0
    after.write_text(MOVED.replace("MUST be declared", "MUST be named"))
    assert check.main(["x", str(before), str(after)]) == 1
