"""The model judges standing in for the author (`add-vertical-slice`, task 4.3).

Stdlib-only; calls no model. The judges' files are what their committed raw replies
split into, they cover every grant, and the author's own files stay unfilled.
"""

from __future__ import annotations

import json

import pytest

from poc.slice import judges, page


def test_the_judges_files_are_what_the_raw_replies_split_into():
    raws = {p.stem: json.loads(p.read_text()) for p in sorted(judges.RAW.glob("*.json"))}
    assert sorted(raws) == ["A", "B"]
    for name, reply in raws.items():
        assert judges.check(reply) == []
        for unit in judges.units():
            got = json.loads((page.VERDICTS / f"{unit}.judges.json").read_text())
            mine = got["judges"][name]
            assert mine["grants"] == reply["units"][unit]["grants"]
            assert mine["outcome"] == reply["units"][unit]["outcome"]
            assert "Opus" not in mine["saw"] and "without the labels" in mine["saw"]


def test_the_authors_own_verdict_files_stay_unfilled():
    for unit in judges.units():
        own = json.loads((page.VERDICTS / f"{unit}.json").read_text())
        assert own["reviewer"] == "the author" and own["date"] is None


def test_a_reply_missing_a_grant_is_refused_not_repaired(tmp_path, monkeypatch):
    reply = json.loads((judges.RAW / "A.json").read_text())
    unit = next(iter(judges.units()))
    reply["units"][unit]["grants"].popitem()
    monkeypatch.setattr(judges, "RAW", tmp_path)
    with pytest.raises(ValueError, match="no verdict on the scale"):
        judges.record("C", reply, model="m", date="d")
    assert not list(tmp_path.iterdir())
