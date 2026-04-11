from __future__ import annotations

from pathlib import Path

import pytest

from odylith.runtime.surfaces import watch_prompt_transactions as watcher


def test_runtime_fingerprint_falls_back_to_manual_fingerprint_on_auto_mode(
    tmp_path: Path,
    monkeypatch,  # noqa: ANN001
) -> None:
    monkeypatch.setattr(
        watcher.odylith_context_engine_store,
        "projection_input_fingerprint",
        lambda *, repo_root: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    monkeypatch.setattr(watcher, "_fingerprint", lambda repo_root: "fallback-fingerprint")

    assert watcher._runtime_fingerprint(tmp_path, runtime_mode="auto") == "fallback-fingerprint"


def test_runtime_fingerprint_fails_closed_in_daemon_mode(
    tmp_path: Path,
    monkeypatch,  # noqa: ANN001
) -> None:
    monkeypatch.setattr(
        watcher.odylith_context_engine,
        "_daemon_request",
        lambda **kwargs: (_ for _ in ()).throw(RuntimeError("daemon state unavailable")),
    )  # noqa: SLF001

    with pytest.raises(RuntimeError, match="daemon state unavailable"):
        watcher._runtime_fingerprint(tmp_path, runtime_mode="daemon")


def test_runtime_fingerprint_reads_daemon_state(
    tmp_path: Path,
    monkeypatch,  # noqa: ANN001
) -> None:
    monkeypatch.setattr(watcher.odylith_context_engine, "_daemon_request", lambda **kwargs: {"projection_fingerprint": "runtime-fingerprint"})  # noqa: SLF001

    assert watcher._runtime_fingerprint(tmp_path, runtime_mode="daemon") == "runtime-fingerprint"


def test_runtime_fingerprint_prefers_live_daemon_in_auto_mode(
    tmp_path: Path,
    monkeypatch,  # noqa: ANN001
) -> None:
    monkeypatch.setattr(watcher.odylith_context_engine, "_daemon_socket_available", lambda *, repo_root: True)  # noqa: SLF001
    monkeypatch.setattr(
        watcher.odylith_context_engine,
        "_daemon_request",
        lambda **kwargs: {"projection_fingerprint": "daemon-fingerprint"},
    )  # noqa: SLF001

    assert watcher._runtime_fingerprint(tmp_path, runtime_mode="auto") == "daemon-fingerprint"


def test_wait_for_runtime_change_uses_daemon_wait_when_available(
    tmp_path: Path,
    monkeypatch,  # noqa: ANN001
) -> None:
    captured: dict[str, object] = {}

    monkeypatch.setattr(watcher.odylith_context_engine, "_daemon_socket_available", lambda *, repo_root: True)  # noqa: SLF001

    def _fake_daemon_request(**kwargs):  # noqa: ANN003
        captured.update(kwargs)
        return {"changed": True, "projection_fingerprint": "next-fingerprint"}

    monkeypatch.setattr(watcher.odylith_context_engine, "_daemon_request", _fake_daemon_request)  # noqa: SLF001

    changed, fingerprint = watcher._wait_for_runtime_change(  # noqa: SLF001
        tmp_path,
        runtime_mode="auto",
        since_fingerprint="previous-fingerprint",
        interval_seconds=1,
        local_watcher=None,
    )

    assert (changed, fingerprint) == (True, "next-fingerprint")
    assert captured == {
        "repo_root": tmp_path,
        "command": "wait-projection-change",
        "payload": {
            "since_fingerprint": "previous-fingerprint",
            "timeout_seconds": watcher._DAEMON_WAIT_TIMEOUT_SECONDS,  # noqa: SLF001
        },
        "required": False,
        "timeout_seconds": watcher._DAEMON_WAIT_TIMEOUT_SECONDS + 5.0,  # noqa: SLF001
    }


def test_wait_for_runtime_change_uses_local_watcher_without_daemon(
    tmp_path: Path,
    monkeypatch,  # noqa: ANN001
) -> None:
    class _LocalWatcher:
        def __init__(self) -> None:
            self.calls: list[tuple[Path, int]] = []

        def wait_for_change(self, *, stop_file: Path, poll_seconds: int) -> bool:
            self.calls.append((stop_file, poll_seconds))
            return True

    monkeypatch.setattr(watcher.odylith_context_engine, "_daemon_socket_available", lambda *, repo_root: False)  # noqa: SLF001
    local_watcher = _LocalWatcher()

    changed, fingerprint = watcher._wait_for_runtime_change(  # noqa: SLF001
        tmp_path,
        runtime_mode="auto",
        since_fingerprint="previous-fingerprint",
        interval_seconds=1,
        local_watcher=local_watcher,
    )

    assert (changed, fingerprint) == (True, "")
    assert local_watcher.calls == [
        (
            (tmp_path / watcher._LOCAL_WATCHER_STOP_FILE).resolve(),  # noqa: SLF001
            watcher._LOCAL_WATCHER_POLL_SECONDS,  # noqa: SLF001
        )
    ]


def test_wait_for_runtime_change_falls_back_to_coarse_sleep_without_daemon_or_watcher(
    tmp_path: Path,
    monkeypatch,  # noqa: ANN001
) -> None:
    slept: list[int] = []

    monkeypatch.setattr(watcher.odylith_context_engine, "_daemon_socket_available", lambda *, repo_root: False)  # noqa: SLF001
    monkeypatch.setattr(watcher.time, "sleep", lambda seconds: slept.append(seconds))

    changed, fingerprint = watcher._wait_for_runtime_change(  # noqa: SLF001
        tmp_path,
        runtime_mode="auto",
        since_fingerprint="previous-fingerprint",
        interval_seconds=1,
        local_watcher=None,
    )

    assert (changed, fingerprint) == (False, "")
    assert slept == [5]


def test_build_local_runtime_watcher_bootstraps_git_fsmonitor_when_recommended(
    tmp_path: Path,
    monkeypatch,  # noqa: ANN001
) -> None:
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        watcher.odylith_context_engine_store,
        "watcher_backend_report",
        lambda *, repo_root: {
            "preferred_backend": "poll",
            "bootstrap_recommended": True,
        },
    )
    monkeypatch.setattr(
        watcher.odylith_context_engine,
        "_build_runtime_watcher",
        lambda *, repo_root, backend: captured.setdefault("backend", backend) or object(),
    )  # noqa: SLF001

    watcher._build_local_runtime_watcher(tmp_path)  # noqa: SLF001

    assert captured == {"backend": "git-fsmonitor"}


def test_refresh_outputs_runtime_uses_compass_refresh_engine_then_backlog_runtime(
    tmp_path: Path,
    monkeypatch,  # noqa: ANN001
) -> None:
    captured: dict[str, object] = {}

    def _fake_run_refresh(**kwargs):  # noqa: ANN003
        captured["refresh"] = kwargs
        return {"rc": 0, "status": "passed"}

    class _BacklogModule:
        @staticmethod
        def main(argv: list[str]) -> int:
            captured["backlog_argv"] = argv
            return 0

    monkeypatch.setattr(watcher.compass_refresh_runtime, "run_refresh", _fake_run_refresh)
    monkeypatch.setattr(watcher.importlib, "import_module", lambda name: _BacklogModule())

    rc = watcher._refresh_outputs_runtime(tmp_path, runtime_mode="auto")  # noqa: SLF001

    assert rc == 0
    assert captured["refresh"] == {
        "repo_root": tmp_path,
        "requested_profile": "shell-safe",
        "requested_runtime_mode": "auto",
        "wait": True,
        "status_only": False,
        "emit_output": True,
    }
    assert captured["backlog_argv"] == [
        "--repo-root",
        str(tmp_path),
        "--runtime-mode",
        "auto",
    ]


def test_refresh_outputs_runtime_stops_when_compass_refresh_fails(
    tmp_path: Path,
    monkeypatch,  # noqa: ANN001
    capsys,  # noqa: ANN001
) -> None:
    monkeypatch.setattr(
        watcher.compass_refresh_runtime,
        "run_refresh",
        lambda **_: {"rc": 124, "status": "failed"},
    )
    monkeypatch.setattr(
        watcher.importlib,
        "import_module",
        lambda name: (_ for _ in ()).throw(AssertionError("backlog render should not run after Compass failure")),
    )

    rc = watcher._refresh_outputs_runtime(tmp_path, runtime_mode="auto")  # noqa: SLF001

    assert rc == 124
    assert "prompt transaction watcher FAILED while refreshing Compass" in capsys.readouterr().out
