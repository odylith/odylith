"""Regression coverage for generated rebuild skip-guard behavior."""

from __future__ import annotations

import subprocess
from pathlib import Path

from odylith.runtime.common import generated_refresh_guard
from odylith.runtime.surfaces import generated_surface_refresh_guards


def _git(repo_root: Path, *args: str) -> None:
    """Run git commands against the temporary test repository."""
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


def test_surface_refresh_guard_bypasses_tree_scan_when_sync_already_forced_rebuild(
    tmp_path: Path,
    monkeypatch,
) -> None:
    output_path = tmp_path / "odylith" / "radar" / "radar.html"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    def _guard_should_not_run(**_kwargs):  # noqa: ANN001
        raise AssertionError("sync-forced render should bypass generated refresh-guard scanning")

    monkeypatch.setenv("ODYLITH_SYNC_SKIP_GENERATED_REFRESH_GUARD", "1")
    monkeypatch.setattr(
        generated_surface_refresh_guards.generated_refresh_guard,
        "should_skip_rebuild",
        _guard_should_not_run,
    )

    skip, fingerprint, metadata, _bundle_paths, _output_paths = (
        generated_surface_refresh_guards.should_skip_surface_rebuild(
            repo_root=tmp_path,
            output_path=output_path,
            asset_prefix="backlog",
            key="backlog-dashboard-render",
            watched_paths=("odylith/radar/source",),
        )
    )

    assert skip is False
    assert fingerprint == ""
    assert metadata == {}
