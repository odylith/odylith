#!/usr/bin/env python3
# ruff: noqa
"""Dispatch Odylith host hooks through a usable launcher, even in fresh worktrees.

Hook commands live in tracked project assets, but the repo-local Odylith launcher
under ``.odylith/bin/odylith`` lives in mutable runtime state and may be absent in
new Git worktrees. This helper prefers the repo bootstrap launcher when present
because bootstrap can recover from a stale main launcher. It falls back to the
main launcher or another worktree's launcher, repairs the current root when
possible, and then forwards the requested host command.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Callable
from typing import Iterable
from typing import Sequence

_LAUNCHER_RELATIVE = Path(".odylith") / "bin" / "odylith"
_BOOTSTRAP_RELATIVE = Path(".odylith") / "bin" / "odylith-bootstrap"
_GUIDANCE_FILES = ("AGENTS.md", "CLAUDE.md")
_ODYLITH_SCOPE_MARKER = "<!-- odylith-scope:start -->"
_HOT_CONTEXT_ENV_DEFAULTS = {
    "ODYLITH_CONTEXT_ENGINE_ALLOW_WORKSPACE_PYTHON": "1",
    "ODYLITH_CONTEXT_ENGINE_ALLOW_BACKGROUND_AUTOSPAWN": "1",
    "ODYLITH_CONTEXT_ENGINE_AUTOSPAWN_IDLE_TIMEOUT_SECONDS": "120",
}


def _resolve_repo_root(argv: Sequence[str], *, cwd: Path) -> Path:
    tokens = list(argv)
    for index, token in enumerate(tokens):
        if token != "--repo-root" or index + 1 >= len(tokens):
            continue
        candidate = Path(tokens[index + 1]).expanduser()
        return (candidate if candidate.is_absolute() else cwd / candidate).resolve()
    env_root = os.environ.get("CLAUDE_PROJECT_DIR") or os.environ.get("CODEX_PROJECT_DIR") or "."
    candidate = Path(env_root).expanduser()
    return (candidate if candidate.is_absolute() else cwd / candidate).resolve()


def _launcher_candidates(repo_root: Path) -> tuple[Path, Path]:
    return repo_root / _LAUNCHER_RELATIVE, repo_root / _BOOTSTRAP_RELATIVE


def _managed_guidance_present(repo_root: Path) -> bool:
    for name in _GUIDANCE_FILES:
        path = repo_root / name
        if not path.is_file():
            continue
        try:
            if _ODYLITH_SCOPE_MARKER in path.read_text(encoding="utf-8"):
                return True
        except (OSError, UnicodeDecodeError):
            continue
    return False


def _repo_is_uninstalled(repo_root: Path) -> bool:
    local_launcher, local_bootstrap = _launcher_candidates(repo_root)
    if local_launcher.is_file() or local_bootstrap.is_file():
        return False
    if (repo_root / ".odylith" / "install.json").is_file():
        return False
    return not _managed_guidance_present(repo_root)


def _git_worktree_roots(repo_root: Path) -> list[Path]:
    try:
        completed = subprocess.run(
            ["git", "worktree", "list", "--porcelain"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return []
    if completed.returncode != 0:
        return []
    roots: list[Path] = []
    for raw_line in str(completed.stdout or "").splitlines():
        if not raw_line.startswith("worktree "):
            continue
        token = raw_line[len("worktree ") :].strip()
        if not token:
            continue
        path = Path(token).expanduser()
        roots.append((path if path.is_absolute() else repo_root / path).resolve())
    return roots


def _candidate_roots(repo_root: Path) -> Iterable[Path]:
    seen: set[Path] = set()
    for candidate in (repo_root, *repo_root.parents, *_git_worktree_roots(repo_root)):
        resolved = candidate.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        yield resolved


def find_launcher(repo_root: Path) -> Path | None:
    for root in _candidate_roots(repo_root):
        for launcher in _launcher_candidates(root):
            if launcher.is_file():
                return launcher
    return None


def _repair_current_repo(*, repo_root: Path, launcher: Path) -> Path | None:
    local_launcher, local_bootstrap = _launcher_candidates(repo_root)
    if local_launcher.is_file():
        return local_launcher
    try:
        subprocess.run(
            [str(launcher), "doctor", "--repo-root", str(repo_root), "--repair"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            check=False,
            timeout=90,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if local_launcher.is_file():
        return local_launcher
    if local_bootstrap.is_file():
        return local_bootstrap
    return None


def _default_exec(launcher: Path, argv: Sequence[str], cwd: Path) -> int:
    os.chdir(cwd)
    os.execv(str(launcher), [str(launcher), *argv])
    return 0


def run(
    argv: Sequence[str] | None = None,
    *,
    cwd: Path | None = None,
    exec_runner: Callable[[Path, Sequence[str], Path], int] = _default_exec,
) -> int:
    command_argv = list(argv if argv is not None else sys.argv[1:])
    if not command_argv:
        print("usage: odylith-host-launcher.py <odylith args...>", file=sys.stderr)
        return 2
    resolved_cwd = (cwd or Path.cwd()).resolve()
    repo_root = _resolve_repo_root(command_argv, cwd=resolved_cwd)
    local_launcher, local_bootstrap = _launcher_candidates(repo_root)
    target = local_bootstrap if local_bootstrap.is_file() else None
    if target is None and local_launcher.is_file():
        target = local_launcher
    if target is None:
        peer = local_bootstrap if local_bootstrap.is_file() else find_launcher(repo_root)
        if peer is None:
            if _repo_is_uninstalled(repo_root):
                return 0
            print(
                f"Odylith host launcher could not find a usable launcher for {repo_root}.",
                file=sys.stderr,
            )
            return 1
        target = _repair_current_repo(repo_root=repo_root, launcher=peer) or peer
    for name, value in _HOT_CONTEXT_ENV_DEFAULTS.items():
        os.environ.setdefault(name, value)
    return exec_runner(target, command_argv, repo_root)


def main() -> int:
    return run()


if __name__ == "__main__":
    raise SystemExit(main())
