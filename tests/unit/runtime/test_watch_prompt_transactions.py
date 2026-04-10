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
