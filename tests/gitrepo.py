"""Git for tests, through pygit2 (libgit2), never the `git` binary.

`Pygit2Repo` answers the queries of `poc.repo_git.Repo`; `tests/conftest.py` installs
it in place of `poc.repo_git.at` for the whole suite. `scratch_repo` and `commit_all`
build throwaway repositories. Their semantics follow git's for the cases the suite
uses (linear history, plain paths and directory prefixes as pathspecs), not git's in
full.
"""

from __future__ import annotations

from pathlib import Path

import pygit2

from poc.repo_git import GitError

_SIG = pygit2.Signature("test", "test@example.com")


def _under(path: str, prefixes: tuple[str, ...]) -> bool:
    for p in prefixes:
        p = p.rstrip("/")
        if path == p or path.startswith(p + "/"):
            return True
    return False


class Pygit2Repo:
    def __init__(self, root: Path):
        self.root = Path(root)
        try:
            self.repo = pygit2.Repository(str(self.root))
        except pygit2.GitError as e:
            raise GitError(f"not a repository: {self.root}: {e}") from e

    def head(self) -> str:
        if self.repo.head_is_unborn:
            raise GitError("HEAD has no commit")
        return str(self.repo.head.target)

    def _blob_at(self, commit, rel: str):
        try:
            return commit.tree[rel].id
        except KeyError:
            return None

    def last_commit(self, rel: str) -> str:
        if self.repo.head_is_unborn:
            return ""
        for commit in self.repo.walk(self.repo.head.target, pygit2.enums.SortMode.TIME):
            mine = self._blob_at(commit, rel)
            parents = [self._blob_at(p, rel) for p in commit.parents]
            if not parents:
                if mine is not None:
                    return str(commit.id)
            elif all(p != mine for p in parents):
                return str(commit.id)
        return ""

    def tracked(self, rel: str) -> bool:
        self.repo.index.read()
        return rel in self.repo.index

    def diff_head(self, rel: str) -> str:
        tree = self.repo.revparse_single("HEAD").peel(pygit2.Tree)
        diff = tree.diff_to_workdir()  # HEAD's tree against the working tree, as `git diff HEAD`
        text = []
        for patch in diff:
            if patch is None:
                continue
            if rel in (patch.delta.old_file.path, patch.delta.new_file.path):
                text.append(patch.text or "")
        return "".join(text)

    def status(self, include: tuple[str, ...], exclude: tuple[str, ...] = ()) -> list[str]:
        changed = self.repo.status(untracked_files="all")
        return sorted(
            path
            for path, flags in changed.items()
            if flags != pygit2.enums.FileStatus.CURRENT
            and not flags & pygit2.enums.FileStatus.IGNORED
            and _under(path, include)
            and not _under(path, exclude)
        )


def scratch_repo(root: Path) -> pygit2.Repository:
    root.mkdir(parents=True, exist_ok=True)
    return pygit2.init_repository(str(root))


def commit_all(root: Path, message: str = "x") -> str:
    """Stage everything (as `git add -A`) and commit it."""
    repo = pygit2.Repository(str(root))
    repo.index.add_all()
    repo.index.write()
    tree = repo.index.write_tree()
    parents = [] if repo.head_is_unborn else [repo.head.target]
    return str(repo.create_commit("HEAD", _SIG, _SIG, message, tree, parents))
