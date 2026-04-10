from __future__ import annotations

import os
from pathlib import Path

import pytest

from odylith.runtime.surfaces import compass_refresh_runtime as runtime


class _FakeWorker:
    def __init__(self, pid: int) -> None:
        self.pid = pid


def test_parse_args_rejects_removed_refresh_profile_flag() -> None:
    with pytest.raises(SystemExit):
        runtime._parse_args(["--refresh-profile", "full"])  # noqa: SLF001


def test_enqueue_request_writes_refresh_state_and_returns_queued(
    tmp_path: Path,
    monkeypatch,  # noqa: ANN001
) -> None:
    monkeypatch.setattr(runtime, "_spawn_worker", lambda **_: _FakeWorker(4321))

    result = runtime._enqueue_request(  # noqa: SLF001
        repo_root=tmp_path,
        requested_profile="shell-safe",
        requested_runtime_mode="auto",
    )

    assert result["rc"] == 0
    assert result["status"] == "queued"
    assert result["coalesced"] is False
    state = runtime._load_state(repo_root=tmp_path)  # noqa: SLF001
    assert state["request_id"] == result["request_id"]
    assert state["requested_profile"] == "shell-safe"
    assert state["requested_runtime_mode"] == "auto"
    assert state["status"] == "queued"
    assert state["pid"] == 4321
    assert state["next_command"] == "odylith compass refresh --repo-root . --status"


def test_shell_safe_enqueue_coalesces_identical_active_request(
    tmp_path: Path,
    monkeypatch,  # noqa: ANN001
) -> None:
    active = runtime._base_state(  # noqa: SLF001
        request_id="compass-active",
        requested_profile="shell-safe",
        requested_runtime_mode="auto",
        status="running",
    )
    active["pid"] = os.getpid()
    runtime._write_state(repo_root=tmp_path, payload=active)  # noqa: SLF001
    monkeypatch.setattr(
        runtime,
        "_spawn_worker",
        lambda **_: (_ for _ in ()).throw(AssertionError("should reuse the active request")),
    )

    result = runtime.run_refresh(
        repo_root=tmp_path,
        requested_profile="shell-safe",
        requested_runtime_mode="auto",
        wait=False,
        status_only=False,
        emit_output=False,
    )

    assert result["rc"] == 0
    assert result["status"] == "running"
    assert result["coalesced"] is True
    assert result["request_id"] == "compass-active"


def test_shell_safe_enqueue_fails_fast_for_conflicting_active_request(tmp_path: Path) -> None:
    active = runtime._base_state(  # noqa: SLF001
        request_id="compass-active",
        requested_profile="shell-safe",
        requested_runtime_mode="standalone",
        status="running",
    )
    active["pid"] = os.getpid()
    runtime._write_state(repo_root=tmp_path, payload=active)  # noqa: SLF001

    result = runtime.run_refresh(
        repo_root=tmp_path,
        requested_profile="shell-safe",
        requested_runtime_mode="auto",
        wait=False,
        status_only=False,
        emit_output=False,
    )

    assert result["rc"] == 1
    assert result["status"] == "failed"
    assert result["coalesced"] is False
    assert result["request_id"] == "compass-active"


def test_status_mode_is_read_only(tmp_path: Path) -> None:
    active = runtime._base_state(  # noqa: SLF001
        request_id="compass-active",
        requested_profile="shell-safe",
        requested_runtime_mode="auto",
        status="queued",
    )
    active["pid"] = os.getpid()
    runtime._write_state(repo_root=tmp_path, payload=active)  # noqa: SLF001
    state_path = runtime.refresh_state_path(repo_root=tmp_path)
    before = state_path.read_text(encoding="utf-8")

    result = runtime.run_refresh(
        repo_root=tmp_path,
        requested_profile="shell-safe",
        requested_runtime_mode="auto",
        wait=False,
        status_only=True,
        emit_output=False,
    )

    assert result["status"] == "queued"
    assert state_path.read_text(encoding="utf-8") == before


def test_status_mode_derives_stale_worker_failure_without_mutating_state(
    tmp_path: Path,
    monkeypatch,  # noqa: ANN001
) -> None:
    active = runtime._base_state(  # noqa: SLF001
        request_id="compass-stale",
        requested_profile="shell-safe",
        requested_runtime_mode="auto",
        status="running",
    )
    active["pid"] = 4321
    runtime._write_state(repo_root=tmp_path, payload=active)  # noqa: SLF001
    state_path = runtime.refresh_state_path(repo_root=tmp_path)
    before = state_path.read_text(encoding="utf-8")
    monkeypatch.setattr(runtime, "_pid_alive", lambda pid: False)
    monkeypatch.setattr(
        runtime,
        "_record_failed_live_payload",
        lambda **_: (_ for _ in ()).throw(AssertionError("status view should stay read-only")),
    )

    result = runtime.run_refresh(
        repo_root=tmp_path,
        requested_profile="shell-safe",
        requested_runtime_mode="auto",
        wait=False,
        status_only=True,
        emit_output=False,
    )

    assert result["status"] == "failed"
    assert result["state"]["terminal_reason"] == "worker_exited"
    assert "pid 4321" in result["state"]["terminal_detail"]
    assert state_path.read_text(encoding="utf-8") == before


def test_shell_safe_wait_mode_runs_in_foreground_when_no_request_is_active(
    tmp_path: Path,
    monkeypatch,  # noqa: ANN001
) -> None:
    captured: dict[str, object] = {}

    def _fake_run_foreground_request(**kwargs):  # noqa: ANN003
        captured["foreground"] = kwargs
        return {
            "rc": 0,
            "status": "passed",
            "request_id": "compass-new",
            "state": {
                "request_id": "compass-new",
                "requested_profile": "shell-safe",
                "requested_runtime_mode": "auto",
                "resolved_runtime_mode": "standalone",
                "started_utc": "2026-04-09T16:00:00.000Z",
                "completed_utc": "2026-04-09T16:00:00.500Z",
            },
            "coalesced": False,
            "message": "passed",
        }

    monkeypatch.setattr(runtime, "_run_foreground_request", _fake_run_foreground_request)
    monkeypatch.setattr(
        runtime,
        "_enqueue_request",
        lambda **_: (_ for _ in ()).throw(AssertionError("shell-safe wait should not enqueue a worker")),
    )
    monkeypatch.setattr(
        runtime,
        "_wait_for_terminal",
        lambda **_: (_ for _ in ()).throw(AssertionError("shell-safe wait should not poll a new worker")),
    )

    result = runtime.run_refresh(
        repo_root=tmp_path,
        requested_profile="shell-safe",
        requested_runtime_mode="auto",
        wait=True,
        status_only=False,
        emit_output=False,
    )

    assert result["rc"] == 0
    assert result["status"] == "passed"
    assert captured["foreground"] == {
        "repo_root": tmp_path.resolve(),
        "requested_profile": "shell-safe",
        "requested_runtime_mode": "auto",
    }


def test_wait_mode_fails_fast_for_conflicting_active_request(tmp_path: Path) -> None:
    active = runtime._base_state(  # noqa: SLF001
        request_id="compass-active",
        requested_profile="shell-safe",
        requested_runtime_mode="standalone",
        status="running",
    )
    active["pid"] = os.getpid()
    runtime._write_state(repo_root=tmp_path, payload=active)  # noqa: SLF001

    result = runtime.run_refresh(
        repo_root=tmp_path,
        requested_profile="shell-safe",
        requested_runtime_mode="auto",
        wait=True,
        status_only=False,
        emit_output=False,
    )

    assert result["rc"] == 1
    assert result["status"] == "failed"
    assert "different settings" in str(result["message"])


def test_foreground_timeout_records_failure_without_retry(
    tmp_path: Path,
    monkeypatch,  # noqa: ANN001
) -> None:
    captured: dict[str, object] = {"render_calls": 0}

    def _fake_render_request(**kwargs):  # noqa: ANN003
        captured["render_calls"] = int(captured["render_calls"]) + 1
        raise runtime.CompassRefreshTimeout("timed out")

    def _fake_record_failed_live_payload(**kwargs):  # noqa: ANN003
        captured["failed_payload"] = kwargs

    monkeypatch.setattr(runtime, "_render_request", _fake_render_request)
    monkeypatch.setattr(runtime, "_record_failed_live_payload", _fake_record_failed_live_payload)
    monkeypatch.setattr(runtime, "_resolve_runtime_mode", lambda **_: "standalone")

    result = runtime._run_foreground_request(  # noqa: SLF001
        repo_root=tmp_path,
        requested_profile="shell-safe",
        requested_runtime_mode="auto",
    )

    assert captured["render_calls"] == 1
    assert result["rc"] == 124
    assert result["status"] == "failed"
    state = result["state"]
    assert state["terminal_reason"] == "timeout"
    assert state["status"] == "failed"
    assert state["next_command"] == "odylith compass refresh --repo-root . --wait"
    assert captured["failed_payload"] == {
        "repo_root": tmp_path.resolve(),
        "requested_profile": "shell-safe",
        "runtime_mode": "standalone",
        "reason": "timeout",
    }


def test_foreground_render_failure_records_terminal_detail(
    tmp_path: Path,
    monkeypatch,  # noqa: ANN001
) -> None:
    def _fake_render_request(**kwargs):  # noqa: ANN003
        raise RuntimeError("B-025 48h window is still unresolved")

    monkeypatch.setattr(runtime, "_render_request", _fake_render_request)
    monkeypatch.setattr(runtime, "_record_failed_live_payload", lambda **_: None)
    monkeypatch.setattr(runtime, "_resolve_runtime_mode", lambda **_: "standalone")

    result = runtime._run_foreground_request(  # noqa: SLF001
        repo_root=tmp_path,
        requested_profile="shell-safe",
        requested_runtime_mode="auto",
    )

    assert result["rc"] == 1
    assert result["status"] == "failed"
    assert result["state"]["terminal_reason"] == "render_failed"
    assert result["state"]["terminal_detail"] == "RuntimeError: B-025 48h window is still unresolved"


def test_shell_safe_daemon_unavailable_fails_before_queue_spawn(
    tmp_path: Path,
    monkeypatch,  # noqa: ANN001
) -> None:
    monkeypatch.setattr(
        runtime,
        "_resolve_runtime_mode",
        lambda **_: (_ for _ in ()).throw(runtime.CompassRefreshError("daemon unavailable")),
    )
    monkeypatch.setattr(
        runtime,
        "_spawn_worker",
        lambda **_: (_ for _ in ()).throw(AssertionError("worker should not spawn when mode resolution fails")),
    )

    result = runtime.run_refresh(
        repo_root=tmp_path,
        requested_profile="shell-safe",
        requested_runtime_mode="daemon",
        wait=False,
        status_only=False,
        emit_output=False,
    )

    assert result["rc"] == 1
    assert result["status"] == "failed"
    state = result["state"]
    assert state["terminal_reason"] == "mode_resolution_failed"
    assert state["status"] == "failed"


def test_shell_safe_daemon_unavailable_fails_cleanly_without_raise(
    tmp_path: Path,
    monkeypatch,  # noqa: ANN001
) -> None:
    monkeypatch.setattr(
        runtime,
        "_resolve_runtime_mode",
        lambda **_: (_ for _ in ()).throw(runtime.CompassRefreshError("daemon unavailable")),
    )

    result = runtime.run_refresh(
        repo_root=tmp_path,
        requested_profile="shell-safe",
        requested_runtime_mode="daemon",
        wait=False,
        status_only=False,
        emit_output=False,
    )

    assert result["rc"] == 1
    assert result["status"] == "failed"
    assert result["state"]["terminal_reason"] == "mode_resolution_failed"


def test_wait_mode_repairs_stale_worker_and_returns_terminal_state(
    tmp_path: Path,
    monkeypatch,  # noqa: ANN001
) -> None:
    active = runtime._base_state(  # noqa: SLF001
        request_id="compass-stale",
        requested_profile="shell-safe",
        requested_runtime_mode="standalone",
        status="running",
    )
    active["pid"] = 4321
    runtime._write_state(repo_root=tmp_path, payload=active)  # noqa: SLF001
    monkeypatch.setattr(runtime, "_pid_alive", lambda pid: False)
    monkeypatch.setattr(runtime, "_record_failed_live_payload", lambda **_: None)

    result = runtime._wait_for_terminal(repo_root=tmp_path, request_id="compass-stale")  # noqa: SLF001

    assert result["rc"] == 1
    assert result["status"] == "failed"
    assert result["state"]["terminal_reason"] == "worker_exited"
    assert "pid 4321" in result["state"]["terminal_detail"]


def test_progress_callback_persists_stage_detail(
    tmp_path: Path,
) -> None:
    active = runtime._base_state(  # noqa: SLF001
        request_id="compass-progress",
        requested_profile="shell-safe",
        requested_runtime_mode="auto",
        status="running",
    )
    runtime._write_state(repo_root=tmp_path, payload=active)  # noqa: SLF001

    callback = runtime._progress_callback_for_request(repo_root=tmp_path, request_id="compass-progress")  # noqa: SLF001
    callback("activity_events_collected", {"message": "collected 7 commits, 9 local changes, and 42 timeline events"})

    state = runtime._load_state(repo_root=tmp_path)  # noqa: SLF001
    assert state["current_stage"] == "activity_events_collected"
    assert state["current_stage_detail"] == "collected 7 commits, 9 local changes, and 42 timeline events"
    assert state["stage_timings"]["activity_events_collected"]["detail"] == state["current_stage_detail"]


def test_pid_alive_treats_permission_denied_as_live(
    monkeypatch,  # noqa: ANN001
) -> None:
    def _fake_kill(pid: int, signal: int) -> None:  # noqa: ARG001
        raise PermissionError("operation not permitted")

    monkeypatch.setattr(runtime.os, "kill", _fake_kill)

    assert runtime._pid_alive(4321)  # noqa: SLF001
