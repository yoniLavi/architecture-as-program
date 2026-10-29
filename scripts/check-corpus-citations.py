#!/usr/bin/env python3
"""Fail the build if a stamped paper cites a corpus paper that is not published.

The rule came out of the September 2026 merge: Paper 2 cited the unpublished
method paper ten times while that paper cited Paper 2 for every figure, so
neither could publish first, and review found it only on the day of upload. A
published paper cites no unpublished work (`openspec/specs/paper-corpus`).

This checks the corpus half of that rule:

- A paper is **stamped** if its title block — the source before its first
  heading — links a `doi.org/10.5281/zenodo.*` identifier. That is its own DOI.
- A paper is **published** if its directory holds `PUBLISHED.json` (a frozen
  paper) or `RECORD.json` (a living one) with `"status": "published"`.
- A bib entry is a **corpus entry** if an author is Lavi and its DOI is a
  Zenodo one. Every corpus entry must map, by DOI, to a paper in `papers/`.

It fails if a stamped paper cites a corpus entry whose paper is unpublished, or
if any corpus entry maps to no paper. An unstamped paper — a draft — may cite an
unpublished one.

What it does not do. It trusts the marker: the build cannot see Zenodo, so a
marker committed before the record goes live would pass. And it checks corpus
papers only; a citation of someone else's work in preparation stays on review.

Stdlib-only, like the validator, so the pre-commit hook stays portable.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MARKERS = ("PUBLISHED.json", "RECORD.json")
ZENODO_DOI = re.compile(r"10\.5281/zenodo\.\d+")
STAMP = re.compile(r"doi\.org/(10\.5281/zenodo\.\d+)")
FIRST_HEADING = re.compile(r"^=\s", re.MULTILINE)
CITATION = re.compile(r"@([A-Za-z0-9_][A-Za-z0-9_\-]*)")
ENTRY = re.compile(r"@\w+\s*\{\s*([^,\s]+)\s*,(.*?)\n\}", re.DOTALL)
FIELD = re.compile(r"(\w+)\s*=\s*\{(.*?)\}\s*,?\s*$", re.MULTILINE)


def own_doi(source: str) -> str | None:
    """The DOI a paper is stamped with: a Zenodo link before its first heading."""
    heading = FIRST_HEADING.search(source)
    title_block = source[: heading.start()] if heading else source
    stamp = STAMP.search(title_block)
    return stamp.group(1) if stamp else None


def is_published(paper_dir: Path) -> bool:
    for name in MARKERS:
        marker = paper_dir / name
        if marker.exists():
            try:
                return json.loads(marker.read_text()).get("status") == "published"
            except json.JSONDecodeError:
                return False
    return False


def corpus_entries(bib: str) -> dict[str, str]:
    """Bib key → DOI, for every entry by Lavi with a Zenodo DOI."""
    entries = {}
    for key, body in ENTRY.findall(bib):
        fields = {name.lower(): value for name, value in FIELD.findall(body)}
        doi = ZENODO_DOI.search(fields.get("doi", ""))
        if doi and "Lavi" in fields.get("author", ""):
            entries[key] = doi.group(0)
    return entries


def papers(root: Path) -> dict[str, dict]:
    """Paper directory name → its source, own DOI and publication state."""
    found = {}
    for source_path in sorted((root / "papers").glob("*/proposal.typ")):
        source = source_path.read_text()
        found[source_path.parent.name] = {
            "source": source,
            "doi": own_doi(source),
            "published": is_published(source_path.parent),
        }
    return found


def find_violations(root: Path = REPO_ROOT) -> list[str]:
    corpus = corpus_entries((root / "citations.bib").read_text())
    by_paper = papers(root)
    paper_by_doi = {p["doi"]: name for name, p in by_paper.items() if p["doi"]}

    problems = [
        f"citations.bib: `{key}` looks like a corpus paper (Lavi, {doi}) but no paper "
        f"under papers/ is stamped with that DOI"
        for key, doi in corpus.items()
        if doi not in paper_by_doi
    ]
    for name, paper in by_paper.items():
        if not paper["doi"]:
            continue  # a draft may cite an unpublished paper
        for key in sorted(set(CITATION.findall(paper["source"])) & corpus.keys()):
            cited = paper_by_doi.get(corpus[key])
            if cited and cited != name and not by_paper[cited]["published"]:
                problems.append(
                    f"papers/{name} is stamped ({paper['doi']}) and cites `{key}`, but "
                    f"papers/{cited} has no publication marker ({' or '.join(MARKERS)} "
                    f'with "status": "published"). A published paper cites no '
                    f"unpublished work: publish papers/{cited} first, or unstamp papers/{name}."
                )
    return problems


def main() -> int:
    problems = find_violations()
    if problems:
        print("check-corpus-citations: failed", file=sys.stderr)
        for problem in problems:
            print(f"  {problem}", file=sys.stderr)
        return 1
    stamped = sum(1 for p in papers(REPO_ROOT).values() if p["doi"])
    print(f"check-corpus-citations: {stamped} stamped papers cite no unpublished corpus paper.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
