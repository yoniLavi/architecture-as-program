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


def test_the_page_offers_misplaced_for_every_grant():
    """Value-bound grants, 4.3: needed by the task, but held by the wrong node."""
    for r in _records():
        text = page.page(r)
        assert text.count("not-needed / misplaced") == len(r["final_graph"]["capabilities"])
    assert page.SCALE == ("needed", "wider", "not-needed", "misplaced")
    assert page.verdict_template(_records()[0])["scale"]["grants"][-1] == "misplaced"


def test_a_verdict_file_may_record_misplaced_with_a_note():
    r = next(r for r in _records() if r["unit"] == "user_task_0.D2")
    filled = page.verdict_template(r)
    pay = "Payments<[any], uncapped>"
    filled["grants"][pay] = {"verdict": "misplaced", "note": "belongs on a library SendMoney"}
    filled["outcome"] = {"verdict": "reject", "note": ""}
    assert page.check_verdicts(filled) == []
    filled["grants"][pay]["verdict"] = "elsewhere"
    assert page.check_verdicts(filled) == [
        f"{pay}: 'elsewhere' is not on the scale ['needed', 'wider', 'not-needed', 'misplaced']"
    ]


def test_verdict_files_already_written_are_untouched_and_still_read():
    """Written once, never regenerated: the committed files keep the scale they list,
    and are checked against today's, so `misplaced` is open to the author in them too."""
    for path in sorted(page.VERDICTS.glob("user_task_*.json")):
        if path.name.endswith(".judges.json"):
            continue
        data = json.loads(path.read_text())
        assert data["scale"]["grants"] == ["needed", "wider", "not-needed"]
        assert page.check_verdicts(data) == []


def test_the_judges_and_the_registered_reviewer_keep_their_scales():
    from poc.architect import registration, reviewer
    from poc.slice import judges

    assert judges.SCALE == ("needed", "wider", "not-needed")
    assert reviewer.VERDICTS == ("needed", "wider", "not-needed")
    registered = json.loads(registration.REGISTRATION_PATH.read_text())
    assert registration.task_hashes() == registered["task_sha256"]
    for path in sorted(page.VERDICTS.glob("*.judges.json")):
        for judged in json.loads(path.read_text())["judges"].values():
            assert all(v["verdict"] in judges.SCALE for v in judged["grants"].values())


def test_a_verdict_file_is_written_once_and_never_regenerated(tmp_path, monkeypatch):
    monkeypatch.setattr(page, "PAGES", tmp_path / "pages")
    monkeypatch.setattr(page, "VERDICTS", tmp_path / "verdicts")
    first = page.write()
    assert first
    filled = page.VERDICTS / first[0]
    filled.write_text('{"filled": true}\n')
    assert page.write() == []
    assert filled.read_text() == '{"filled": true}\n'
