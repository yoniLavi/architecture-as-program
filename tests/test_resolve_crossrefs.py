"""Tests for the cross-reference filter (scripts/resolve-crossrefs.lua).

The Markdown and HTML copies of the paper are built by pandoc, not typst, and
the filter is what turns `@sec:open` into `§7.6` there. When pandoc 3.11 stopped
attaching a heading's label to the heading itself, every section reference
silently fell back to its bare label ("§open") for weeks: the PDF stayed right,
so nothing looked wrong. These tests pin the resolved form, so a toolchain change
that breaks it again fails the suite rather than the published web copy.
"""

import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
FILTER = ROOT / "scripts" / "resolve-crossrefs.lua"

pytestmark = pytest.mark.skipif(shutil.which("pandoc") is None, reason="pandoc not installed")

SOURCE = """#set heading(numbering: "1.1")

= Design <sec:design>

== Security <sec:security>

= Limits <sec:threats>

See @sec:design, @sec:security and @sec:threats.
"""


def _render(tmp_path: Path, to: str) -> str:
    src = tmp_path / "doc.typ"
    src.write_text(SOURCE, encoding="utf-8")
    return subprocess.run(
        ["pandoc", str(src), "-f", "typst", "-t", to, f"--lua-filter={FILTER}"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout


def test_section_references_resolve_to_numbers(tmp_path):
    out = _render(tmp_path, "markdown")
    assert "See §1, §1.1 and §2." in out


def test_no_section_reference_falls_back_to_its_label(tmp_path):
    out = _render(tmp_path, "markdown")
    for label in ("§design", "§security", "§threats"):
        assert label not in out


def test_html_headings_carry_their_labels_as_anchors(tmp_path):
    # On the heading element itself, not on a stray empty span after it.
    out = _render(tmp_path, "html")
    for label in ("sec:design", "sec:security", "sec:threats"):
        assert re.search(rf'<h\d[^>]*id="{label}"', out), label
