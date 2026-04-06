from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RepoRuntimePaths:
    repo_root: Path
    state_root: Path
    bin_dir: Path
    cache_dir: Path
    runtime_dir: Path
    versions_dir: Path
    current_runtime: Path
    launcher_path: Path


def repo_runtime_paths(repo_root: str | Path) -> RepoRuntimePaths:
    root = Path(repo_root).expanduser().resolve()
    state_root = root / ".odylith"
    bin_dir = state_root / "bin"
    cache_dir = state_root / "cache"
    runtime_dir = state_root / "runtime"
    versions_dir = runtime_dir / "versions"
    current_runtime = runtime_dir / "current"
    launcher_path = bin_dir / "odylith"
    return RepoRuntimePaths(
        repo_root=root,
        state_root=state_root,
        bin_dir=bin_dir,
        cache_dir=cache_dir,
        runtime_dir=runtime_dir,
        versions_dir=versions_dir,
        current_runtime=current_runtime,
        launcher_path=launcher_path,
    )
