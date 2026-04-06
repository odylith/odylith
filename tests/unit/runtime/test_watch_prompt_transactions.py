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
