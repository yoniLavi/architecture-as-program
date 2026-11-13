"""Suite-wide guards.

No test may run the system ``git`` binary, directly or through the code it tests
(the author's rule, 13 November 2026). A test that needs a repository builds or
reads one with pygit2 (``tests/gitrepo.py``). Code under test asks git through
``poc.repo_git``, which this file points at pygit2 for every test; the one script
that shells out to git, ``scripts/check-freeze.py``, is given stand-ins by its own
test.

Why: a test that runs ``git`` inherits whatever ``GIT_*`` variables its runner
has. Under ``git commit -a`` the pre-commit hook runs the suite with
``GIT_INDEX_FILE`` pointing at the commit's temporary index, and a fixture's
``git add -A`` in a scratch repository wrote its ``README`` into that index,
with a blob only the scratch repository held: the commit then failed with
"invalid object ... Error building trees".

The guard is installed in ``pytest_configure``, before collection, because a
``skipif`` condition runs at import time, and an earlier version installed as a
fixture let one through. Two guards, so neither path is left open:

- a ``git`` shim at the front of ``PATH`` that fails loudly, which also catches
  child processes (harnesses and scripts run as subprocesses);
- an in-process check on ``subprocess.Popen``, which catches an absolute path
  to the binary and names the offending call.

``GIT_*`` variables are removed for the session too, so nothing this suite runs
can address the repository a hook is committing to.
"""

from __future__ import annotations

import os
import stat
import subprocess
import tempfile
from pathlib import Path

import pytest

REFUSAL = "tests may not run the system git binary; use pygit2 (tests/gitrepo.py) or poc.repo_git"

_SHIM = f"""#!/bin/sh
echo "{REFUSAL}: git $*" >&2
exit 97
"""


class SystemGitRefused(AssertionError):
    pass


def _is_git(args) -> bool:
    if isinstance(args, (str, bytes, os.PathLike)):
        first = os.fsdecode(args).strip().split(maxsplit=1)
        return bool(first) and Path(first[0]).name == "git"
    try:
        first = next(iter(args))
    except (TypeError, StopIteration):
        return False
    return Path(os.fsdecode(first)).name == "git"


_saved: dict = {}


def pytest_configure(config):
    shim_dir = Path(tempfile.mkdtemp(prefix="no-system-git-"))
    shim = shim_dir / "git"
    shim.write_text(_SHIM)
    shim.chmod(shim.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    _saved["env"] = dict(os.environ)
    for var in [v for v in os.environ if v.startswith("GIT_")]:
        del os.environ[var]
    os.environ["PATH"] = f"{shim_dir}{os.pathsep}{os.environ.get('PATH', '')}"

    real_init = subprocess.Popen.__init__
    _saved["popen_init"] = real_init

    def guarded_init(self, args, *a, **kw):
        if _is_git(args):
            raise SystemGitRefused(f"{REFUSAL}: {args!r}")
        real_init(self, args, *a, **kw)

    subprocess.Popen.__init__ = guarded_init


def pytest_unconfigure(config):
    if "popen_init" in _saved:
        subprocess.Popen.__init__ = _saved.pop("popen_init")
    if "env" in _saved:
        os.environ.clear()
        os.environ.update(_saved.pop("env"))


@pytest.fixture(autouse=True)
def _repo_git_through_pygit2(monkeypatch):
    """Every git question code under test asks goes to libgit2, not the binary."""
    from poc import repo_git
    from tests.gitrepo import Pygit2Repo

    monkeypatch.setattr(repo_git, "at", Pygit2Repo)
