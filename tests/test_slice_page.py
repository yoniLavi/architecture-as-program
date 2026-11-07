"""The human-review pages (`add-vertical-slice`, task 4.2). Stdlib-only; calls no model."""

from __future__ import annotations

import json

from poc.architect import labels
from poc.slice import page


def _records() -> list[dict]:
    return [json.loads(p.read_text()) for p in sorted(page.RUNS.glob("*.json"))]


def test_the_committed_pages_are_what_the_records_render():
    for r in _records():
        assert (page.PAGES / f"{r['unit']}.md").read_text() == page.page(r) + "\n"


def test_a_page_asks_for_a_verdict_on_every_grant_and_shows_no_label():
    for r in _records():
        text = page.page(r)
        for cap in r["final_graph"]["capabilities"]:
            assert f"### `{cap}`" in text
        assert text.count("**Your verdict**") == len(r["final_graph"]["capabilities"]) + 1
        assert "label" not in text.lower()
        assert ("**A hand-built graph.**" in text) == bool(r.get("hand_built"))
    assert labels.approved()


def test_a_verdict_file_is_written_once_and_never_regenerated(tmp_path, monkeypatch):
    monkeypatch.setattr(page, "PAGES", tmp_path / "pages")
    monkeypatch.setattr(page, "VERDICTS", tmp_path / "verdicts")
    first = page.write()
    assert first
    filled = page.VERDICTS / first[0]
    filled.write_text('{"filled": true}\n')
    assert page.write() == []
    assert filled.read_text() == '{"filled": true}\n'
