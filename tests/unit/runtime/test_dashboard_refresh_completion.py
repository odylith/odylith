"""Require real terminal surface coverage before dashboard completion may activate a baseline."""

from pathlib import Path

import pytest

from odylith.runtime.governance import sync_workstream_artifacts as sync


@pytest.fixture
def surface_workers(monkeypatch):
    events: list[str] = []
    results: dict[str, dict[str, object]] = {}

    def run_worker(**kwargs):
        surface = kwargs["surface"]
        events.append(surface)
        result = results.get(surface, {"surface": surface, "status": "passed", "rc": 0})
        return "", result

    monkeypatch.setattr(sync, "_run_surface_worker", run_worker)
    return events, results


@pytest.mark.parametrize("callback_rc", [0, 3])
def test_completion_runs_once_after_every_parallel_and_serial_worker(
    tmp_path: Path, monkeypatch, surface_workers, callback_rc: int,
) -> None:
    events, _results = surface_workers
    monkeypatch.setenv(sync._SYNC_SKIP_GENERATED_REFRESH_GUARD_ENV, "prior")

    def complete() -> int:
        assert set(events[:2]) == {"radar", "compass"}
        assert events[2:] == ["atlas", "tooling_shell"]
        assert sync.os.environ[sync._SYNC_SKIP_GENERATED_REFRESH_GUARD_ENV] == "prior"
        events.append("completed")
        return callback_rc

    rc = sync.refresh_dashboard_surfaces(
        repo_root=tmp_path, surfaces=("radar", "compass", "atlas", "tooling_shell"),
        runtime_mode="standalone", atlas_sync=True, force=True, on_completed=complete,
    )

    assert rc == callback_rc
    assert events.count("completed") == 1


@pytest.mark.parametrize("status", ["queued", "failed"])
@pytest.mark.parametrize("requires_completion", [False, True])
def test_nonterminal_or_failed_surface_never_completes(
    tmp_path: Path, surface_workers, status: str, requires_completion: bool,
) -> None:
    events, results = surface_workers
    results["compass"] = {"surface": "compass", "status": status, "rc": 0 if status == "queued" else 1}

    def complete() -> int:
        events.append("completed")
        return 0

    rc = sync.refresh_dashboard_surfaces(
        repo_root=tmp_path, surfaces=("radar", "compass", "tooling_shell"),
        runtime_mode="standalone", on_completed=complete if requires_completion else None,
    )

    assert set(events) == {"radar", "compass", "tooling_shell"}
    if status == "queued" and not requires_completion:
        assert rc == 0
    else:
        assert rc != 0


def test_dry_run_does_not_run_workers_or_completion(tmp_path: Path, surface_workers) -> None:
    events, _results = surface_workers
    rc = sync.refresh_dashboard_surfaces(
        repo_root=tmp_path, surfaces=("radar", "tooling_shell"), runtime_mode="standalone",
        dry_run=True, on_completed=lambda: events.append("completed") or 0,
    )
    assert rc == 0
    assert events == []


def test_completion_exception_propagates_after_finished_workers(tmp_path: Path, surface_workers) -> None:
    events, _results = surface_workers

    def complete() -> int:
        assert events == ["tooling_shell"]
        events.append("completed")
        raise RuntimeError("baseline activation refused")

    with pytest.raises(RuntimeError, match="baseline activation refused"):
        sync.refresh_dashboard_surfaces(
            repo_root=tmp_path, surfaces=("tooling_shell",), runtime_mode="standalone",
            on_completed=complete,
        )
    assert events == ["tooling_shell", "completed"]


def test_worker_exception_never_runs_completion(tmp_path: Path, monkeypatch) -> None:
    events: list[str] = []

    def fail_worker(**kwargs):
        raise RuntimeError("surface worker interrupted")

    monkeypatch.setattr(sync, "_run_surface_worker", fail_worker)
    with pytest.raises(RuntimeError, match="surface worker interrupted"):
        sync.refresh_dashboard_surfaces(
            repo_root=tmp_path, surfaces=("radar", "compass"), runtime_mode="standalone",
            on_completed=lambda: events.append("completed") or 0,
        )
    assert events == []


@pytest.mark.parametrize("results", [
    [],
    [{"surface": "radar", "status": "passed"}],
    [{"surface": "radar", "status": "passed"}, {"surface": "radar", "status": "passed"}],
    [{"surface": "radar", "status": "passed"}, {"surface": "atlas", "status": "passed"}],
    [{"surface": "radar", "status": "passed"}, {"surface": "compass"}],
    [{"surface": "radar", "status": "passed"}, {"surface": "compass", "status": "running"}],
    [{"surface": "radar", "status": "passed"}, {"status": "passed"}],
    [{"surface": "radar", "status": "passed"}, {"surface": "compass", "status": "passed"},
     {"surface": "atlas", "status": "passed"}],
], ids=["empty", "missing", "duplicate", "foreign", "missing-status", "unknown-status", "missing-name", "extra"])
def test_completion_requires_exact_terminal_surface_coverage(
    tmp_path: Path, monkeypatch, results: list[dict[str, object]],
) -> None:
    completions: list[bool] = []
    monkeypatch.setattr(sync, "_refresh_surfaces_parallel", lambda **kwargs: results)

    rc = sync.refresh_dashboard_surfaces(
        repo_root=tmp_path, surfaces=("radar", "compass"), runtime_mode="standalone",
        on_completed=lambda: completions.append(True) or 0,
    )

    assert completions == []
    assert rc != 0


def test_empty_selection_is_rejected_before_workers_or_completion(tmp_path: Path, surface_workers) -> None:
    events, _results = surface_workers
    with pytest.raises(ValueError, match="at least one surface"):
        sync.refresh_dashboard_surfaces(
            repo_root=tmp_path, surfaces=(), runtime_mode="standalone",
            on_completed=lambda: events.append("completed") or 0,
        )
    assert events == []
