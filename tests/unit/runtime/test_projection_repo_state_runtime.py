from __future__ import annotations

from pathlib import Path

from odylith.runtime.context_engine import projection_repo_state_runtime


def test_git_head_oid_reads_head_from_git_dir(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    git_dir = repo_root / ".git"
    ref_path = git_dir / "refs" / "heads" / "main"
    repo_root.mkdir()
    ref_path.parent.mkdir(parents=True, exist_ok=True)
    (git_dir / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
    ref_path.write_text("abc123def456\n", encoding="utf-8")

    try:
        assert projection_repo_state_runtime._git_head_oid(repo_root=repo_root) == "abc123def456"  # noqa: SLF001
    finally:
        projection_repo_state_runtime._git_dir.cache_clear()  # noqa: SLF001


def test_git_head_oid_reads_packed_ref_from_gitdir_file(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    git_dir = tmp_path / "git-data"
    repo_root.mkdir()
    git_dir.mkdir()
    (repo_root / ".git").write_text(f"gitdir: {git_dir}\n", encoding="utf-8")
    (git_dir / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
    (git_dir / "packed-refs").write_text(
        "# pack-refs with: peeled fully-peeled sorted\n"
        "fedcba9876543210 refs/heads/main\n",
        encoding="utf-8",
    )

    try:
        assert projection_repo_state_runtime._git_head_oid(repo_root=repo_root) == "fedcba9876543210"  # noqa: SLF001
    finally:
        projection_repo_state_runtime._git_dir.cache_clear()  # noqa: SLF001
