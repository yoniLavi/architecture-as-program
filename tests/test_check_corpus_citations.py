"""The stamp check: no stamped paper cites an unpublished corpus paper."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location(
    "check_corpus_citations", REPO_ROOT / "scripts" / "check-corpus-citations.py"
)
check = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(check)

BIB = """@misc{lavi_first_2026,
\ttitle = {The {First} Paper},
\tauthor = {Lavi, Yoni},
\tdoi = {10.5281/zenodo.111},
}

@misc{lavi_second_2026,
\ttitle = {The Second Paper},
\tauthor = {Lavi, Yoni},
\tdoi = {10.5281/zenodo.222},
}

@misc{lavi_skill_2025,
\ttitle = {A Skill},
\turl = {https://github.com/example},
\tauthor = {Lavi, Yoni},
}

@misc{someone_else_2026,
\ttitle = {Elsewhere},
\tauthor = {Else, Some},
\tdoi = {10.5281/zenodo.999},
}
"""


def _paper(root: Path, name: str, *, doi: str | None, cites=(), marker: str | None = None):
    directory = root / "papers" / name
    directory.mkdir(parents=True)
    stamp = f'#link("https://doi.org/{doi}")[doi:{doi}]\n' if doi else ""
    body = " ".join(f"@{key}" for key in cites)
    (directory / "proposal.typ").write_text(f"#title[{name}]\n{stamp}\n= Introduction\n{body}\n")
    if marker:
        (directory / marker).write_text(json.dumps({"status": "published"}))


@pytest.fixture
def corpus(tmp_path):
    (tmp_path / "citations.bib").write_text(BIB)
    _paper(tmp_path, "01-first", doi="10.5281/zenodo.111", marker="PUBLISHED.json")
    return tmp_path


def test_a_stamped_paper_citing_an_unpublished_corpus_paper_fails(corpus):
    _paper(corpus, "02-second", doi="10.5281/zenodo.222")
    _paper(corpus, "03-third", doi="10.5281/zenodo.333", cites=["lavi_second_2026"])
    (corpus / "citations.bib").write_text(
        BIB
        + "\n@misc{lavi_third_2026,\n\tauthor = {Lavi, Yoni},\n\tdoi = {10.5281/zenodo.333},\n}\n"
    )
    problems = check.find_violations(corpus)
    assert len(problems) == 1
    assert "papers/03-third is stamped" in problems[0] and "papers/02-second" in problems[0]


def test_a_draft_may_cite_an_unpublished_corpus_paper(corpus):
    _paper(corpus, "02-second", doi="10.5281/zenodo.222")
    _paper(corpus, "03-third", doi=None, cites=["lavi_second_2026"])
    assert check.find_violations(corpus) == []


def test_once_the_cited_paper_publishes_the_citing_paper_may_be_stamped(corpus):
    _paper(corpus, "02-second", doi="10.5281/zenodo.222", marker="RECORD.json")
    _paper(corpus, "03-third", doi="10.5281/zenodo.333", cites=["lavi_second_2026"])
    (corpus / "citations.bib").write_text(
        BIB
        + "\n@misc{lavi_third_2026,\n\tauthor = {Lavi, Yoni},\n\tdoi = {10.5281/zenodo.333},\n}\n"
    )
    assert check.find_violations(corpus) == []


def test_a_corpus_entry_that_maps_to_no_paper_fails(corpus):
    problems = check.find_violations(corpus)  # lavi_second_2026 has no paper yet
    assert len(problems) == 1 and "`lavi_second_2026`" in problems[0]


def test_a_marker_that_does_not_say_published_does_not_count(tmp_path):
    (tmp_path / "RECORD.json").write_text(json.dumps({"status": "reserved"}))
    assert not check.is_published(tmp_path)
    (tmp_path / "RECORD.json").write_text("{not json")
    assert not check.is_published(tmp_path)


def test_a_doi_in_the_body_is_not_a_stamp():
    source = '#title[x]\n= Introduction\nSee #link("https://doi.org/10.5281/zenodo.5")[it].\n'
    assert check.own_doi(source) is None


def test_only_lavi_entries_with_zenodo_dois_are_corpus_entries():
    assert check.corpus_entries(BIB) == {
        "lavi_first_2026": "10.5281/zenodo.111",
        "lavi_second_2026": "10.5281/zenodo.222",
    }


def test_the_corpus_as_it_stands_passes():
    assert check.find_violations(REPO_ROOT) == []
