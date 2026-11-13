"""The suite-wide ban on the system git binary (tests/conftest.py) holds.

A guard that only ever passes is indistinguishable from none, so each path it
closes is shown closed: an in-process call, a call by absolute path, a child
process that finds `git` on PATH, and an inherited GIT_* variable.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys

import pytest

from poc import repo_git
from tests.conftest import SystemGitRefused
from tests.gitrepo import Pygit2Repo


def test_an_in_process_git_call_is_refused():
    with pytest.raises(SystemGitRefused):
        subprocess.run(["git", "--version"], capture_output=True)


def test_a_git_call_by_absolute_path_is_refused():
    with pytest.raises(SystemGitRefused):
        subprocess.run(["/usr/bin/git", "--version"], capture_output=True)


def test_a_shell_string_naming_git_is_refused():
    with pytest.raises(SystemGitRefused):
        subprocess.run("git status", shell=True, capture_output=True)


def test_a_child_process_finds_only_the_refusing_shim():
    done = subprocess.run(
        [
            sys.executable,
            "-c",
            "import subprocess; print(subprocess.run(['git', '--version']).returncode)",
        ],
        capture_output=True,
        text=True,
    )
    assert done.stdout.strip() == "97"
    assert "may not run the system git binary" in done.stderr
    assert "no-system-git-" in (shutil.which("git") or "")


def test_no_git_variable_reaches_the_suite():
    assert not [v for v in os.environ if v.startswith("GIT_")]


def test_code_under_test_asks_git_through_pygit2():
    assert repo_git.at is Pygit2Repo
