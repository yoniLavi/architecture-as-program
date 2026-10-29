"""A `display` string reads the same in the PDF and in the web copies.

Papers interpolate non-integer figures from a pre-formatted `display` block because
typst and pandoc format one float differently. This holds that the pre-formatted
string survives both renderers unchanged, using the real generation report's p-value
(add-paper-3, task 1.1a). Skipped without typst, pandoc or pdftotext.
"""

import json
import shutil
import subprocess

import pytest

from poc.generation import report

pytestmark = pytest.mark.skipif(
    any(shutil.which(tool) is None for tool in ("typst", "pandoc", "pdftotext")),
    reason="typst, pandoc and pdftotext are all needed",
)


@pytest.fixture
def figure():
    return report.scientific(1.0886790573745067e-40)


def test_a_display_string_survives_typst_and_pandoc_alike(tmp_path, figure):
    (tmp_path / "data.json").write_text(json.dumps({"display": {"p": figure}}))
    (tmp_path / "doc.typ").write_text(
        '#let gd = json("data.json").display\nThe test gives $p = $ #gd.p here.\n'
    )
    subprocess.run(
        ["typst", "compile", "doc.typ", "doc.pdf"], cwd=tmp_path, check=True, capture_output=True
    )
    pdf = subprocess.run(
        ["pdftotext", "doc.pdf", "-"], cwd=tmp_path, check=True, capture_output=True, text=True
    ).stdout
    md = subprocess.run(
        ["pandoc", "doc.typ", "-f", "typst", "-t", "markdown"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    assert figure in md
    assert figure in " ".join(pdf.split())
