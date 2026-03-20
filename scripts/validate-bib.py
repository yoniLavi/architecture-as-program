#!/usr/bin/env python3
"""Validate citations.bib entries against Semantic Scholar API.

For each entry with a DOI, queries Semantic Scholar and compares
title, year, and author count. Reports discrepancies.
"""

import json
import re
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path


def parse_bib(bib_path: Path) -> list[dict]:
    """Extract entries from a .bib file (lightweight parser)."""
    content = bib_path.read_text()
    entries = []
    # Match each @type{key, ... } block
    for match in re.finditer(
        r"@(\w+)\{([\w-]+),\s*(.*?)\n\}", content, re.DOTALL
    ):
        entry_type, key, body = match.groups()
        entry = {"type": entry_type, "key": key}
        for field_match in re.finditer(
            r"(\w+)\s*=\s*\{(.*?)\}(?:,|\s*$)", body, re.DOTALL
        ):
            field_name, field_value = field_match.groups()
            # Clean up whitespace
            entry[field_name] = " ".join(field_value.split())
        # Year might also be just a number without braces
        if "year" not in entry:
            year_match = re.search(r"year\s*=\s*(\d{4})", body)
            if year_match:
                entry["year"] = year_match.group(1)
        entries.append(entry)
    return entries


def query_s2(doi: str) -> dict | None:
    """Query Semantic Scholar for a paper by DOI."""
    url = f"https://api.semanticscholar.org/graph/v1/paper/DOI:{doi}?fields=title,authors,year,venue,publicationVenue"
    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        if e.code == 429:
            print(f"  Rate limited, waiting 5s...", file=sys.stderr)
            time.sleep(5)
            return query_s2(doi)
        raise
    except urllib.error.URLError:
        return None


def query_s2_by_title(title: str) -> dict | None:
    """Query Semantic Scholar by title search as fallback."""
    # Clean bib title formatting
    clean = re.sub(r"\{([^}]*)\}", r"\1", title)
    url = f"https://api.semanticscholar.org/graph/v1/paper/search?query={urllib.request.quote(clean)}&limit=1&fields=title,authors,year,venue,externalIds,publicationVenue"
    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            if data.get("data"):
                return data["data"][0]
            return None
    except (urllib.error.HTTPError, urllib.error.URLError):
        return None


def clean_bib_title(title: str) -> str:
    """Remove BibTeX braces from title."""
    return re.sub(r"\{([^}]*)\}", r"\1", title)


def count_bib_authors(author_str: str) -> int:
    """Count authors in a BibTeX author field."""
    if "others" in author_str:
        return len(author_str.split(" and "))  # includes "others"
    return len(author_str.split(" and "))


def normalize(s: str) -> str:
    """Normalize string for comparison."""
    return re.sub(r"[^a-z0-9 ]", "", s.lower()).strip()


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    bib_path = root / "citations.bib"
    entries = parse_bib(bib_path)

    issues = []
    checked = 0
    skipped = 0

    for entry in entries:
        key = entry["key"]
        doi = entry.get("doi", "")
        title = entry.get("title", "")
        year = entry.get("year", "")
        authors = entry.get("author", "")

        # Try DOI first, then title search
        s2 = None
        lookup_method = None
        if doi:
            s2 = query_s2(doi)
            lookup_method = f"DOI:{doi}"
            time.sleep(0.35)  # Rate limit: ~3 req/sec

        if not s2 and title:
            s2 = query_s2_by_title(title)
            lookup_method = "title search"
            time.sleep(0.35)

        if not s2:
            skipped += 1
            print(f"  SKIP  {key} (not found via {lookup_method or 'no DOI/title'})")
            continue

        checked += 1
        entry_issues = []

        # Compare title
        bib_title = normalize(clean_bib_title(title))
        s2_title = normalize(s2.get("title", ""))
        if bib_title and s2_title and bib_title != s2_title:
            # Check if one contains the other (subtitle differences)
            if not (bib_title in s2_title or s2_title in bib_title):
                entry_issues.append(
                    f"  TITLE  bib: {clean_bib_title(title)}\n"
                    f"         s2:  {s2.get('title', '')}"
                )

        # Compare year
        s2_year = str(s2.get("year", ""))
        if year and s2_year and year != s2_year:
            entry_issues.append(f"  YEAR   bib: {year}  s2: {s2_year}")

        # Compare author count
        s2_authors = s2.get("authors", [])
        bib_count = count_bib_authors(authors) if authors else 0
        s2_count = len(s2_authors)
        if bib_count and s2_count and abs(bib_count - s2_count) > 0:
            bib_names = authors.replace(" and ", ", ")
            s2_names = ", ".join(a["name"] for a in s2_authors)
            entry_issues.append(
                f"  AUTHORS bib({bib_count}): {bib_names}\n"
                f"          s2({s2_count}):  {s2_names}"
            )

        if entry_issues:
            issues.append((key, entry_issues))
            print(f"  ISSUE {key}")
        else:
            print(f"  OK    {key}")

    print(f"\n{'=' * 60}")
    print(f"Checked {checked} entries, skipped {skipped}, found {len(issues)} with issues\n")

    if issues:
        for key, entry_issues in issues:
            print(f"@{key}:")
            for issue in entry_issues:
                print(issue)
            print()

    return 1 if issues else 0


if __name__ == "__main__":
    sys.exit(main())
