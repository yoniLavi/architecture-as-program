"""The repository queries `poc/` asks of git, behind one seam.

Several harnesses refuse to run on a tree that differs from `HEAD`, record the commit
they ran at, or check that an approval or a prediction is committed. They ask five
questions, and only these: what `HEAD` is, which commit last changed a path, whether a
path is tracked, how a path differs from `HEAD`, and which paths under some prefixes
differ from it.

`at(root)` answers them with the `git` binary, as the harnesses always have. The test
suite never runs that binary (the author's rule, 13 November 2026): `tests/conftest.py`
replaces `at` with a pygit2 implementation (`tests/gitrepo.py`), so tests exercise the
callers' logic against real repositories through libgit2. The binary-backed class is
therefore not run by the suite; it is kept to plain invocations of documented git
commands for that reason.

Stdlib only, like the rest of what the harnesses import before a model is called.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


class GitError(RuntimeError):
    """A git query failed (not a repository, no `HEAD`, git missing)."""


class Repo(Protocol):
    def head(self) -> str: ...

    def last_commit(self, rel: str) -> str:
        """The commit that last changed `rel`, or '' if none did."""
        ...

    def tracked(self, rel: str) -> bool: ...

    def diff_head(self, rel: str) -> str:
        """The patch from `HEAD` to the working tree for `rel`; '' if they agree."""
        ...

    def status(self, include: tuple[str, ...], exclude: tuple[str, ...] = ()) -> list[str]:
        """Paths under `include` (and not under `exclude`) that differ from `HEAD`:
        modified, staged, deleted or untracked, every untracked file listed."""
        ...


@dataclass(frozen=True)
class CLIRepo:
    root: Path

    def _git(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        done = subprocess.run(
            ["git", *args], cwd=self.root, capture_output=True, text=True, check=False
        )
        if check and done.returncode != 0:
            raise GitError(f"git {' '.join(args)}: {done.stderr.strip()}")
        return done

    def head(self) -> str:
        return self._git("rev-parse", "HEAD").stdout.strip()

    def last_commit(self, rel: str) -> str:
        return self._git("log", "-1", "--format=%H", "--", rel).stdout.strip()

    def tracked(self, rel: str) -> bool:
        return self._git("ls-files", "--error-unmatch", rel, check=False).returncode == 0

    def diff_head(self, rel: str) -> str:
        return self._git("diff", "HEAD", "--", rel).stdout

    def status(self, include: tuple[str, ...], exclude: tuple[str, ...] = ()) -> list[str]:
        spec = [*include, *(f":(exclude){e}" for e in exclude)]
        out = self._git("status", "--porcelain", "--untracked-files=all", "--", *spec).stdout
        return [line[3:] for line in out.splitlines() if line.strip()]


def at(root: Path) -> Repo:
    """The repository at `root`. Replaced under test; see the module docstring."""
    return CLIRepo(Path(root))
