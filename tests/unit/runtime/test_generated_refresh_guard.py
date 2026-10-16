"""Regression coverage for generated rebuild skip-guard behavior."""

from __future__ import annotations

import subprocess
from pathlib import Path

from odylith.runtime.common import generated_refresh_guard
from odylith.runtime.governance import surface_refresh_fingerprint_dag
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


def test_compute_input_fingerprint_tracks_same_size_content_change(tmp_path: Path) -> None:
    watched = tmp_path / "odylith" / "registry" / "source" / "component_registry.v1.json"
    watched.parent.mkdir(parents=True, exist_ok=True)
    watched.write_text('{"components":["a"]}\n', encoding="utf-8")
    initial_size = watched.stat().st_size

    first = generated_refresh_guard.compute_input_fingerprint(
        repo_root=tmp_path,
        watched_paths=("odylith/registry/source/component_registry.v1.json",),
    )

    watched.write_text('{"components":["b"]}\n', encoding="utf-8")
    second = generated_refresh_guard.compute_input_fingerprint(
        repo_root=tmp_path,
        watched_paths=("odylith/registry/source/component_registry.v1.json",),
    )

    assert watched.stat().st_size == initial_size
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


def test_casebook_surface_fingerprint_tracks_renderer_inputs(tmp_path: Path) -> None:
    renderer_path = tmp_path / "src" / "odylith" / "runtime" / "surfaces" / "render_casebook_dashboard.py"
    renderer_path.parent.mkdir(parents=True, exist_ok=True)
    renderer_path.write_text("first renderer contract\n", encoding="utf-8")

    first = surface_refresh_fingerprint_dag.surface_input_fingerprint(
        repo_root=tmp_path,
        surface="casebook",
        atlas_sync=False,
    )

    renderer_path.write_text("second renderer contract with changed behavior\n", encoding="utf-8")
    second = surface_refresh_fingerprint_dag.surface_input_fingerprint(
        repo_root=tmp_path,
        surface="casebook",
        atlas_sync=False,
    )

    assert first != second
