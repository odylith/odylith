from __future__ import annotations

import json

import pytest

from odylith.runtime.evaluation import odylith_benchmark_runner as runner


def test_prune_stale_shared_benchmark_progress_clears_dead_pid_even_when_temp_artifacts_exist(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    unrelated_temp_dir = tmp_path / ".odylith" / "runtime" / "odylith-benchmark-temp" / "odylith-benchmark-host-old"
    unrelated_temp_dir.mkdir(parents=True)
    monkeypatch.setattr(runner, "_benchmark_owned_codex_process_ids", lambda: [])
    monkeypatch.setattr(runner, "_benchmark_temp_worktrees", lambda repo_root: [])
    monkeypatch.setattr(runner, "_benchmark_temp_directories", lambda repo_root: [unrelated_temp_dir])
    monkeypatch.setattr(runner, "_process_exists", lambda pid: False)

    progress_path = runner.progress_report_path(repo_root=tmp_path)
    progress_path.parent.mkdir(parents=True, exist_ok=True)
    progress_path.write_text(
        json.dumps(
            {
                "report_id": "report-dead-shared",
                "benchmark_profile": runner.BENCHMARK_PROFILE_QUICK,
                "comparison_contract": runner.LIVE_COMPARISON_CONTRACT,
                "repo_root": str(tmp_path.resolve()),
                "started_utc": "2026-04-15T00:00:00Z",
                "updated_utc": "2026-04-15T00:01:00Z",
                "status": "running",
                "write_report": False,
                "owning_pid": 54321,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    cleanup = runner._prune_stale_benchmark_progress(repo_root=tmp_path, clear_shared_progress=False)  # noqa: SLF001

    assert cleanup["active_runtime_present"] is True
    assert cleanup["stale_shared_progress_cleared"] is True
    assert not progress_path.exists()


def test_cleanup_stale_benchmark_state_removes_host_temp_directories(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    host_temp_dir = tmp_path / ".odylith" / "runtime" / "odylith-benchmark-temp" / "odylith-benchmark-host-old"
    host_temp_dir.mkdir(parents=True)
    (host_temp_dir / "result.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(runner, "_benchmark_owned_codex_process_ids", lambda: [])
    monkeypatch.setattr(runner, "_benchmark_temp_worktrees", lambda repo_root: [])
    monkeypatch.setattr(runner, "_process_exists", lambda pid: False)

    cleanup = runner._cleanup_stale_benchmark_state(repo_root=tmp_path, clear_progress=True)  # noqa: SLF001

    assert cleanup["temp_directory_cleanup"]["removed_temp_directory_count"] == 1
    assert not host_temp_dir.exists()
