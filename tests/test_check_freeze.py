"""Tests for the published-paper half of the freeze guard (scripts/check-freeze.py).

As with the hedge guard, the point is the failure path: a guard that only ever
passes is indistinguishable from none. Each test copies Paper 1's real marker and
stored artifacts into a temporary directory and damages one thing.

Covers the `paper-corpus` requirement added by `mark-published-papers`:
  - A published frozen paper is served from its published artifacts
"""

import hashlib
import importlib.util
import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
PAPER = ROOT / "papers" / "01-vision"


def _load():
    spec = importlib.util.spec_from_file_location(
        "check_freeze", ROOT / "scripts" / "check-freeze.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


check_freeze = _load()


@pytest.fixture
def paper(tmp_path):
    """A copy of Paper 1's marker and published store, safe to damage."""
    shutil.copy(PAPER / "PUBLISHED.json", tmp_path / "PUBLISHED.json")
    shutil.copytree(PAPER / "published", tmp_path / "published")
    return tmp_path


def test_the_real_published_paper_passes():
    assert check_freeze.published_problems(PAPER) == []


def test_every_listed_artifact_is_guarded():
    """The marker covers every file served for the paper, figures included."""
    marker = json.loads((PAPER / "PUBLISHED.json").read_text())
    served = {
        p.relative_to(PAPER / "published").as_posix()
        for p in (PAPER / "published").rglob("*")
        if p.is_file()
    }
    assert set(marker["artifacts"]) == served
    assert marker["record_file"]["path"] in marker["artifacts"]


def test_an_altered_artifact_fails(paper):
    html = paper / "published" / "proposal.html"
    html.write_bytes(html.read_bytes() + b"\n")
    problems = check_freeze.published_problems(paper)
    assert any("proposal.html" in p and "SHA-256" in p for p in problems)


def test_a_missing_artifact_fails(paper):
    (paper / "published" / "graphs" / "customer-support.svg").unlink()
    problems = check_freeze.published_problems(paper)
    assert any("customer-support.svg" in p and "missing" in p for p in problems)


def test_an_unlisted_file_fails(paper):
    (paper / "published" / "extra.md").write_text("added later\n")
    problems = check_freeze.published_problems(paper)
    assert any("extra.md" in p and "not listed" in p for p in problems)


def test_a_rehashed_but_replaced_pdf_still_fails_on_the_record_md5(paper):
    """Updating the SHA-256 to match a new PDF is not enough: the served PDF must
    still be the file the publication record holds."""
    pdf = paper / "published" / "lavi-2026-architecture-as-program.pdf"
    pdf.write_bytes(pdf.read_bytes() + b"%rebuilt\n")
    marker_path = paper / "PUBLISHED.json"
    marker = json.loads(marker_path.read_text())
    marker["artifacts"][pdf.name] = hashlib.sha256(pdf.read_bytes()).hexdigest()
    marker_path.write_text(json.dumps(marker))
    problems = check_freeze.published_problems(paper)
    assert any("publication record" in p for p in problems)


def test_a_missing_marker_fails(paper):
    (paper / "PUBLISHED.json").unlink()
    assert check_freeze.published_problems(paper)


def test_a_marker_listing_nothing_fails(paper):
    marker_path = paper / "PUBLISHED.json"
    marker = json.loads(marker_path.read_text())
    marker["artifacts"] = {}
    marker_path.write_text(json.dumps(marker))
    problems = check_freeze.published_problems(paper)
    assert any("lists no artifacts" in p for p in problems)


# The source half. A history rewrite once left FREEZE_REF naming a commit no fresh
# clone had, and the guard skipped itself there without failing.


def _is_shallow() -> bool:
    out = subprocess.run(
        ["git", "rev-parse", "--is-shallow-repository"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    return out.returncode != 0 or out.stdout.strip() == "true"


def test_the_marker_and_the_guard_name_the_same_commit():
    marker = json.loads((PAPER / "PUBLISHED.json").read_text())
    assert marker["source_commit"] == check_freeze.FREEZE_REF


@pytest.mark.skipif(_is_shallow(), reason="a shallow checkout cannot see the freeze commit")
def test_the_freeze_commit_is_reachable_from_head():
    reachable = subprocess.run(
        ["git", "merge-base", "--is-ancestor", check_freeze.FREEZE_REF, "HEAD"],
        cwd=ROOT,
        capture_output=True,
    )
    assert reachable.returncode == 0


@pytest.mark.skipif(_is_shallow(), reason="a shallow checkout skips by design")
def test_an_unreachable_freeze_commit_fails_in_a_full_clone(monkeypatch, capsys):
    monkeypatch.setattr(check_freeze, "FREEZE_REF", "0" * 40)
    assert check_freeze.main() == 1
    assert "not reachable from HEAD" in capsys.readouterr().err
