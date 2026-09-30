#!/usr/bin/env python3
"""Guard the frozen founding-vision paper against silent edits.

Paper 1 (papers/01-vision/) is the founding vision: its *content* is the
repository's state before the executable demonstrator (poc/) existed, dated June
2026. Its value is that it is a stable, dated, historical record; that only holds
if its sources are not quietly rewritten. This check compares each frozen file
against its content at the freeze commit and fails if any has drifted.

The freeze reference moved with the paper's single sanctioned publication
revision. The paper was originally frozen at 7acf585~1 (b28593a, the last
pre-poc commit; named 59898cc~1 before a history rewrite gave every commit from
then on a new identifier with an identical tree). In July 2026 it received the
revision's preparation step (typos, phrasing, and publication front matter,
with no substantive claim changed) and was re-frozen; on 21 July 2026 the
revision concluded at the actual publication event — the Zenodo DOI and licence
stamped onto the title block, plus a Figure 1 legibility fix — and the paper was
re-frozen at the published commit named below. The frozen paths and the freeze
ref are the same on both sides of the comparison. See papers/01-vision/ERRATA.md
and the paper-corpus spec for the rule that permits one such revision and its
concluding step.

Corrections to a frozen paper are otherwise recorded in its ERRATA.md, never by
editing the frozen text — so any diff here is a mistake, and the build should
fail.

If the freeze commit is unavailable in a *shallow* checkout, the check prints a
warning and passes, rather than failing a build that simply cannot see the
reference. In a full clone it fails instead, and it also fails if the freeze
commit is not an ancestor of HEAD: after the history rewrite the old identifier
survived only as a dangling object in the author's clone and was absent from
every fresh clone, so the guard skipped itself everywhere else and nothing said
so. The pre-commit hook and CI (`fetch-depth: 0`) run against full clones.

Freezing the *sources* is not enough once a paper is published. Its PDF,
Markdown, HTML and figures were regenerated on every build through shared inputs
this check never saw (the Lua filter, the CSL, the shared bibliography, the
typst and pandoc versions). So a published paper carries a PUBLISHED.json
marker, and the build serves the files under its published/ directory instead of
regenerating them. The second check here holds those files to the marker: each
must exist and match its SHA-256, no unlisted file may sit beside them, and the
PDF must still have the MD5 the publication record states for it. That check
needs no git history, so it runs in a shallow checkout too.
"""

import hashlib
import json
import subprocess
import sys
from pathlib import Path

# The freeze point: the published commit of Paper 1 — the concluding step of its
# one-time publication revision (Zenodo DOI + licence stamp, Figure 1 legibility
# fix). Previously 9ae2380 (the preprint preparation step); originally
# "7acf585~1", the last commit before poc/ existed. Before the history rewrite
# these were c4ae487, 0137aea and 59898cc~1 (same trees, now unreachable).
FREEZE_REF = "5a551e00c8c8e9be8220287dc6d63373573a8367"

# Frozen files in the corpus. At the published-preprint freeze commit the paper
# already lives under papers/01-vision/, so a file's current path and its path at
# the freeze commit are identical; FROZEN_FILES maps current -> frozen for the
# comparison below, here an identity map over the frozen set.
_FROZEN_PATHS = [
    "papers/01-vision/proposal.typ",
    "papers/01-vision/graphs/customer-support.json",
    "papers/01-vision/graphs/support-platform.json",
    "papers/01-vision/graphs/schema.json",
    "papers/01-vision/diagrams/typed-wiring.typ",
]
FROZEN_FILES = {path: path for path in _FROZEN_PATHS}


def git_show(ref_path: str) -> bytes | None:
    """Return the bytes of ref_path at the freeze commit, or None if unavailable."""
    result = subprocess.run(
        ["git", "show", f"{FREEZE_REF}:{ref_path}"],
        capture_output=True,
    )
    return result.stdout if result.returncode == 0 else None


# Frozen papers that have been published, and so are served from their stored
# artifacts rather than rebuilt.
PUBLISHED_PAPERS = ["papers/01-vision"]


def published_problems(paper_dir: Path) -> list[str]:
    """Hold a published paper's stored artifacts to its PUBLISHED.json marker."""
    marker_path = paper_dir / "PUBLISHED.json"
    if not marker_path.exists():
        return [f"{marker_path}: missing — a published paper must carry its marker"]
    marker = json.loads(marker_path.read_text(encoding="utf-8"))
    artifacts: dict[str, str] = marker.get("artifacts", {})
    store = paper_dir / "published"
    problems: list[str] = []
    if not artifacts:
        problems.append(f"{marker_path}: lists no artifacts, so nothing would be guarded")
    for rel, expected in sorted(artifacts.items()):
        path = store / rel
        if not path.is_file():
            problems.append(f"{path}: missing")
        elif hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            problems.append(f"{path}: differs from the SHA-256 recorded in {marker_path.name}")
    if store.is_dir():
        present = {p.relative_to(store).as_posix() for p in store.rglob("*") if p.is_file()}
        for rel in sorted(present - set(artifacts)):
            problems.append(f"{store / rel}: present but not listed in {marker_path.name}")
    record = marker.get("record_file", {})
    record_path = store / record.get("path", "")
    if not record.get("path") or not record.get("md5"):
        problems.append(f"{marker_path}: record_file must name the published file and its MD5")
    elif (
        record_path.is_file() and hashlib.md5(record_path.read_bytes()).hexdigest() != record["md5"]
    ):
        problems.append(
            f"{record_path}: no longer the publication record's file "
            f"(MD5 differs from {record['md5']})"
        )
    return problems


def main() -> int:
    root = Path(__file__).resolve().parent.parent

    published = [p for paper in PUBLISHED_PAPERS for p in published_problems(root / paper)]
    if published:
        print("ERROR: a published paper's served artifacts have drifted:", file=sys.stderr)
        for p in published:
            print(f"  {p}", file=sys.stderr)
        print(
            "\nA published paper is served exactly as published. Its artifacts change only\n"
            "by a deliberate, author-approved act recorded in its ERRATA.md, with the\n"
            "checksums in PUBLISHED.json updated in the same commit.",
            file=sys.stderr,
        )
        return 1

    # Probe once. A shallow checkout may simply not see the freeze commit, so it
    # skips; a full clone must both hold it and reach it from HEAD, or the guard
    # would be checking against a commit no fresh clone has.
    probe = subprocess.run(
        ["git", "cat-file", "-e", f"{FREEZE_REF}:papers/01-vision/proposal.typ"],
        cwd=root,
        capture_output=True,
    )
    reachable = (
        probe.returncode == 0
        and subprocess.run(
            ["git", "merge-base", "--is-ancestor", FREEZE_REF, "HEAD"],
            cwd=root,
            capture_output=True,
        ).returncode
        == 0
    )
    if not reachable:
        shallow = subprocess.run(
            ["git", "rev-parse", "--is-shallow-repository"],
            cwd=root,
            capture_output=True,
            text=True,
        )
        if shallow.returncode != 0 or shallow.stdout.strip() == "true":
            print(
                f"check-freeze: freeze commit {FREEZE_REF} unavailable "
                "(shallow checkout?); skipping frozen-paper guard.",
                file=sys.stderr,
            )
            return 0
        print(
            f"ERROR: freeze commit {FREEZE_REF} is not reachable from HEAD in a full\n"
            "clone, so a fresh clone could not run this guard. If history was\n"
            "rewritten, re-point FREEZE_REF (and PUBLISHED.json's source_commit) at\n"
            "the commit with the same tree.",
            file=sys.stderr,
        )
        return 1

    drifted = []
    for current, frozen in FROZEN_FILES.items():
        current_path = root / current
        if not current_path.exists():
            drifted.append(f"{current}: missing (expected a copy of {frozen}@{FREEZE_REF})")
            continue
        expected = git_show(frozen)
        if expected is None:
            drifted.append(f"{current}: cannot read {frozen}@{FREEZE_REF}")
            continue
        if current_path.read_bytes() != expected:
            drifted.append(f"{current}: differs from {frozen}@{FREEZE_REF}")

    if drifted:
        print("ERROR: frozen paper has drifted from the freeze commit:", file=sys.stderr)
        for d in drifted:
            print(f"  {d}", file=sys.stderr)
        print(
            "\nA frozen paper is errata-only. Record corrections in "
            "papers/01-vision/ERRATA.md; do not edit the frozen sources.",
            file=sys.stderr,
        )
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
