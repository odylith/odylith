from __future__ import annotations

from pathlib import Path

import pytest

from odylith.runtime.evaluation import odylith_benchmark_live_execution as live_execution


def test_codex_auth_snapshot_survives_source_file_rewrite(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    source = tmp_path / "auth.json"
    source.write_text('{"token":"initial"}\n', encoding="utf-8")
    monkeypatch.setattr(live_execution, "_CODEX_AUTH_SNAPSHOT_DIR", None)
    monkeypatch.setattr(live_execution, "_CODEX_AUTH_SNAPSHOT_PATH", None)
    monkeypatch.setattr(live_execution, "_CODEX_AUTH_SNAPSHOT_CANDIDATES", ())
    monkeypatch.setattr(
        live_execution,
        "_codex_auth_source",
        lambda *, environ: source if source.is_file() else None,
    )

    first = live_execution._codex_auth_snapshot_source(environ={})  # noqa: SLF001
    source.unlink()
    second = live_execution._codex_auth_snapshot_source(environ={})  # noqa: SLF001

    assert first is not None
    assert second == first
    assert second.read_text(encoding="utf-8") == '{"token":"initial"}\n'
    live_execution._cleanup_codex_auth_snapshot()  # noqa: SLF001


def test_codex_auth_snapshot_reports_missing_when_no_source_exists(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(live_execution, "_CODEX_AUTH_SNAPSHOT_DIR", None)
    monkeypatch.setattr(live_execution, "_CODEX_AUTH_SNAPSHOT_PATH", None)
    monkeypatch.setattr(live_execution, "_CODEX_AUTH_SNAPSHOT_CANDIDATES", ())
    monkeypatch.setattr(live_execution, "_codex_auth_source", lambda *, environ: None)

    assert live_execution._codex_auth_snapshot_source(environ={}) is None  # noqa: SLF001
