from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_ROOT = REPO_ROOT / "scripts"


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _module():
    return _load_module(SCRIPTS_ROOT / "release_worktree.py", "release_worktree")


def _run(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(args),
        cwd=cwd,
        check=True,
        text=True,
        capture_output=True,
    )


def _init_git_repo(tmp_path: Path) -> tuple[Path, Path]:
    remote = tmp_path / "origin.git"
    repo = tmp_path / "repo"
    _run("git", "init", "--bare", str(remote), cwd=tmp_path)
    _run("git", "init", str(repo), cwd=tmp_path)
    _run("git", "config", "user.name", "Odylith Tests", cwd=repo)
    _run("git", "config", "user.email", "odylith-tests@example.invalid", cwd=repo)
    (repo / "README.md").write_text("# Odylith Test Repo\n", encoding="utf-8")
    _run("git", "add", "README.md", cwd=repo)
    _run("git", "commit", "-m", "init", cwd=repo)
    _run("git", "branch", "-M", "main", cwd=repo)
    _run("git", "remote", "add", "origin", str(remote), cwd=repo)
    _run("git", "push", "-u", "origin", "main", cwd=repo)
    return repo, remote


def test_prepare_checkout_uses_current_repo_when_already_clean_main(tmp_path: Path) -> None:
    module = _module()
    repo, _remote = _init_git_repo(tmp_path)

    mode, path = module.prepare_checkout(repo_root=repo, remote="origin", ref="main")

    assert mode == "current"
    assert path == repo.resolve()


def test_prepare_checkout_creates_isolated_worktree_when_current_checkout_is_dirty_or_off_main(tmp_path: Path) -> None:
    module = _module()
    repo, _remote = _init_git_repo(tmp_path)
    _run("git", "checkout", "-b", "2026/freedom/test", cwd=repo)
    (repo / "README.md").write_text("# Dirty\n", encoding="utf-8")

    mode, path = module.prepare_checkout(repo_root=repo, remote="origin", ref="main")
    try:
        assert mode == "isolated"
        assert path != repo.resolve()
        assert path.is_dir()
        assert module.worktree_is_clean(repo_root=path) is True
        assert module.head_sha(repo_root=path) == module.remote_ref_sha(repo_root=repo, remote="origin", ref="main")
    finally:
        module.cleanup_checkout(repo_root=repo, path=path)
        assert not path.exists()


def test_prepare_checkout_fails_when_head_does_not_match_remote_ref(tmp_path: Path) -> None:
    module = _module()
    repo, _remote = _init_git_repo(tmp_path)
    (repo / "CHANGELOG.md").write_text("next\n", encoding="utf-8")
    _run("git", "add", "CHANGELOG.md", cwd=repo)
    _run("git", "commit", "-m", "next", cwd=repo)

    try:
        module.prepare_checkout(repo_root=repo, remote="origin", ref="main")
    except ValueError as exc:
        assert "HEAD to match origin/main" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected prepare_checkout to fail when HEAD diverges from origin/main")
