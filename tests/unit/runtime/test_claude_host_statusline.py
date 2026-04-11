from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import pytest

from odylith.runtime.surfaces import claude_host_shared, claude_host_statusline


def _write_runtime_snapshot(repo_root: Path, payload: dict) -> Path:
    runtime_dir = repo_root / "odylith" / "compass" / "runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    path = runtime_dir / "current.v1.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


@pytest.fixture(autouse=True)
def _clear_host_env(monkeypatch):
    for var in ("ODYLITH_HOST_FAMILY", "CLAUDE_PROJECT_DIR", "CODEX_HOME", "CODEX_HOST_RUNTIME"):
        monkeypatch.delenv(var, raising=False)


def test_statusline_renders_active_workstream_and_freshness(tmp_path, monkeypatch):
    stamp = dt.datetime.now(tz=dt.timezone.utc).replace(microsecond=0)
    _write_runtime_snapshot(
        tmp_path,
        {
            "generated_utc": stamp.isoformat().replace("+00:00", "Z"),
            "execution_focus": {"global": {"headline": "B-085 bake", "workstreams": ["B-085", "B-084"]}},
        },
    )
    monkeypatch.setenv("ODYLITH_HOST_FAMILY", "claude")
    rendered = claude_host_statusline.render_claude_host_statusline(tmp_path)
    assert rendered.startswith("Odylith · B-085 · brief ")
    assert "· host claude" in rendered


def test_statusline_degrades_to_no_snapshot_when_runtime_missing(tmp_path):
    rendered = claude_host_statusline.render_claude_host_statusline(tmp_path)
    assert "no active workstream" in rendered
    assert "brief no snapshot" in rendered
    assert "host unknown" in rendered


def test_statusline_degrades_on_malformed_runtime(tmp_path):
    runtime_dir = tmp_path / "odylith" / "compass" / "runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    (runtime_dir / "current.v1.json").write_text("{not json", encoding="utf-8")
    rendered = claude_host_statusline.render_claude_host_statusline(tmp_path)
    assert "brief no snapshot" in rendered
    assert "no active workstream" in rendered


def test_statusline_never_raises_even_on_unresolvable_root():
    rendered = claude_host_statusline.render_claude_host_statusline("\x00invalid\x00")
    assert rendered == claude_host_statusline.SAFE_FALLBACK_STATUSLINE or "Odylith" in rendered


def test_statusline_host_family_prefers_explicit_env(monkeypatch, tmp_path):
    _write_runtime_snapshot(
        tmp_path,
        {
            "generated_utc": dt.datetime.now(tz=dt.timezone.utc).isoformat().replace("+00:00", "Z"),
            "execution_focus": {"global": {"headline": "h", "workstreams": ["B-001"]}},
        },
    )
    monkeypatch.setenv("ODYLITH_HOST_FAMILY", "codex")
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", "/tmp/fake")
    rendered = claude_host_statusline.render_claude_host_statusline(tmp_path)
    assert "host codex" in rendered


def test_statusline_host_family_falls_back_to_claude_when_only_env_marker_present(monkeypatch, tmp_path):
    _write_runtime_snapshot(
        tmp_path,
        {
            "generated_utc": dt.datetime.now(tz=dt.timezone.utc).isoformat().replace("+00:00", "Z"),
            "execution_focus": {"global": {"headline": "h", "workstreams": ["B-001"]}},
        },
    )
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", "/tmp/fake")
    rendered = claude_host_statusline.render_claude_host_statusline(tmp_path)
    assert "host claude" in rendered


def test_freshness_label_buckets():
    now = dt.datetime(2026, 4, 11, 12, 0, tzinfo=dt.timezone.utc)
    assert claude_host_shared.freshness_label({"generated_utc": "2026-04-11T11:59:30Z"}, now=now) == "fresh"
    assert claude_host_shared.freshness_label({"generated_utc": "2026-04-11T11:30:00Z"}, now=now) == "30m"
    assert claude_host_shared.freshness_label({"generated_utc": "2026-04-11T09:00:00Z"}, now=now) == "3h"
    assert claude_host_shared.freshness_label({"generated_utc": "2026-04-09T12:00:00Z"}, now=now) == "2d"
    assert claude_host_shared.freshness_label({"generated_utc": ""}, now=now) == "no snapshot"
    assert claude_host_shared.freshness_label(None, now=now) == "no snapshot"


def test_main_writes_string_to_stdout(tmp_path, capsys):
    _write_runtime_snapshot(
        tmp_path,
        {
            "generated_utc": dt.datetime.now(tz=dt.timezone.utc).isoformat().replace("+00:00", "Z"),
            "execution_focus": {"global": {"headline": "h", "workstreams": ["B-085"]}},
        },
    )
    exit_code = claude_host_statusline.main(["--repo-root", str(tmp_path)])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert captured.out.startswith("Odylith · B-085 · brief ")
