from __future__ import annotations

import subprocess
from pathlib import Path

from odylith.runtime.common import generated_refresh_guard


def _git(repo_root: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(repo_root), *args],
        check=True,
        capture_output=True,
        text=True,
    )


def test_compute_input_fingerprint_tracks_dirty_file_content(tmp_path: Path) -> None:
    repo_root = tmp_path
    watched = repo_root / "watched.txt"
    watched.write_text("base\n", encoding="utf-8")

    _git(repo_root, "init")
    _git(repo_root, "config", "user.name", "freedom-research")
    _git(repo_root, "config", "user.email", "freedom-research@example.com")
    _git(repo_root, "add", "watched.txt")
    _git(repo_root, "commit", "-m", "seed")

    watched.write_text("dirty-one\n", encoding="utf-8")
    first = generated_refresh_guard.compute_input_fingerprint(
        repo_root=repo_root,
        watched_paths=("watched.txt",),
    )

    watched.write_text("dirty-two\n", encoding="utf-8")
    second = generated_refresh_guard.compute_input_fingerprint(
        repo_root=repo_root,
        watched_paths=("watched.txt",),
    )

    assert first != second

