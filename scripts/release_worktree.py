"""Prepare an isolated clean checkout for the canonical local release lane."""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path


def _run_git(*, repo_root: Path, args: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=str(repo_root),
        check=check,
        capture_output=True,
        text=True,
    )


def _git_stdout(*, repo_root: Path, args: list[str]) -> str:
    completed = _run_git(repo_root=repo_root, args=args)
    return completed.stdout.strip()


def current_branch(*, repo_root: Path) -> str:
    return _git_stdout(repo_root=repo_root, args=["branch", "--show-current"])


def head_sha(*, repo_root: Path) -> str:
    return _git_stdout(repo_root=repo_root, args=["rev-parse", "HEAD"])


def fetch_remote_ref(*, repo_root: Path, remote: str, ref: str) -> None:
    _run_git(repo_root=repo_root, args=["fetch", remote, ref, "--quiet"])


def remote_ref_sha(*, repo_root: Path, remote: str, ref: str) -> str:
    return _git_stdout(repo_root=repo_root, args=["rev-parse", f"{remote}/{ref}"])


def worktree_is_clean(*, repo_root: Path) -> bool:
    tracked = _run_git(repo_root=repo_root, args=["diff", "--quiet", "--ignore-submodules", "HEAD", "--"], check=False)
    staged = _run_git(repo_root=repo_root, args=["diff", "--quiet", "--ignore-submodules", "--cached", "--"], check=False)
    return tracked.returncode == 0 and staged.returncode == 0


def prepare_checkout(*, repo_root: Path, remote: str, ref: str) -> tuple[str, Path]:
    fetch_remote_ref(repo_root=repo_root, remote=remote, ref=ref)
    current_head = head_sha(repo_root=repo_root)
    expected_head = remote_ref_sha(repo_root=repo_root, remote=remote, ref=ref)
    if current_head != expected_head:
        raise ValueError(
            f"release lane requires HEAD to match {remote}/{ref} "
            f"(HEAD={current_head} {remote}/{ref}={expected_head})"
        )

    branch = current_branch(repo_root=repo_root)
    if worktree_is_clean(repo_root=repo_root) and branch in {"", ref}:
        return "current", repo_root.resolve()

    temp_root = Path(tempfile.mkdtemp(prefix="odylith-release-worktree-")).resolve()
    try:
        _run_git(repo_root=repo_root, args=["worktree", "add", "--detach", str(temp_root), f"{remote}/{ref}"])
    except Exception:
        temp_root.rmdir()
        raise
    return "isolated", temp_root


def cleanup_checkout(*, repo_root: Path, path: Path) -> None:
    _run_git(repo_root=repo_root, args=["worktree", "remove", "--force", str(path)])


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Prepare or clean up a canonical Odylith release checkout.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    prepare = subparsers.add_parser("prepare", help="Prepare a clean checkout for canonical release proof.")
    prepare.add_argument("--repo-root", required=True)
    prepare.add_argument("--remote", default="origin")
    prepare.add_argument("--ref", default="main")

    cleanup = subparsers.add_parser("cleanup", help="Remove an isolated release checkout.")
    cleanup.add_argument("--repo-root", required=True)
    cleanup.add_argument("--path", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "prepare":
            mode, path = prepare_checkout(
                repo_root=Path(args.repo_root).expanduser().resolve(),
                remote=str(args.remote).strip(),
                ref=str(args.ref).strip(),
            )
            print(f"{mode}\t{path}")
            return 0
        if args.command == "cleanup":
            cleanup_checkout(
                repo_root=Path(args.repo_root).expanduser().resolve(),
                path=Path(args.path).expanduser().resolve(),
            )
            return 0
        raise ValueError(f"unsupported command: {args.command}")
    except (ValueError, subprocess.CalledProcessError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
