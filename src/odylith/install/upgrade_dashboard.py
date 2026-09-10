"""Target-runtime dashboard rendering inside an admitted upgrade's writer lease."""

from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys

from odylith.runtime.domain_intelligence.greenfield_repository_lock import (
    GreenfieldRepositoryBusyError,
    GreenfieldRepositoryLockError,
    inherited_greenfield_repository_lock,
)


RENDER_WORKER_COMMAND = "_upgrade-dashboard-render"
UPGRADE_DASHBOARD_SURFACES = ("tooling_shell", "radar", "compass")


def run_dashboard_renderer(*, repo_root: Path, repository_lock_fd: int) -> subprocess.CompletedProcess[str]:
    """Keep launcher-owned target selection; wait before the parent may publish."""
    return subprocess.run(
        [
            str((repo_root / ".odylith/bin/odylith").resolve()),
            RENDER_WORKER_COMMAND, "--repo-root", str(repo_root),
            "--lock-fd", str(repository_lock_fd),
        ],
        cwd=str(repo_root), check=False, capture_output=True, text=True,
        pass_fds=(repository_lock_fd,),
    )


def worker_main(argv: list[str]) -> int:
    """Fixed internal operation, never a generic admission bypass or publisher."""
    parser = argparse.ArgumentParser(prog=RENDER_WORKER_COMMAND, allow_abbrev=False)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--lock-fd", type=int, required=True)
    args = parser.parse_args(argv)
    try:
        with inherited_greenfield_repository_lock(args.repo_root, args.lock_fd) as descriptor:
            from odylith.runtime.governance import sync_workstream_artifacts

            return sync_workstream_artifacts.refresh_dashboard_surfaces(
                repo_root=args.repo_root.resolve(), surfaces=UPGRADE_DASHBOARD_SURFACES,
                runtime_mode="auto", atlas_sync=False, force=True,
                repository_lock_fd=descriptor, on_completed=lambda: 0,
            )
    except (GreenfieldRepositoryBusyError, GreenfieldRepositoryLockError, OSError) as exc:
        print(f"Odylith upgrade dashboard render refused: {exc}", file=sys.stderr)
        return 75 if isinstance(exc, GreenfieldRepositoryBusyError) else 1
