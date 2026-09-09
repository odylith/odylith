"""Hook alignment consumes recorded posture, never live projection evaluation."""

import json
from pathlib import Path

import pytest

from odylith.runtime.context_engine import odylith_runtime_surface_summary as summary
from odylith.runtime.intervention_engine import alignment_context
from odylith.runtime.surfaces import host_intervention_support


@pytest.fixture(autouse=True)
def forbid_live_rebuild(monkeypatch):
    def forbidden(**kwargs):
        pytest.fail("host alignment attempted a live engine rebuild")

    monkeypatch.setattr(summary, "load_runtime_surface_summary", forbidden)
    monkeypatch.setattr(summary.memory_snapshot_runtime, "load_runtime_evaluation_snapshot", forbidden)
    monkeypatch.setattr(summary.memory_snapshot_runtime, "load_runtime_memory_snapshot", forbidden)
    monkeypatch.setattr(summary.runtime_learning_runtime, "load_runtime_optimization_snapshot", forbidden)
    monkeypatch.delenv("ODYLITH_MODE", raising=False)
    monkeypatch.delenv("ODYLITH_ENABLED", raising=False)


def test_alignment_reads_recorded_evidence_without_promoting_freshness(tmp_path: Path):
    source = tmp_path / "odylith/compass/runtime/current.v1.json"
    source.parent.mkdir(parents=True)
    source.write_text(json.dumps({
        "generated_utc": "2099-01-01T00:00:00Z",
        "odylith_runtime": {
            "status": "active",
            "enabled": True,
            "memory_status": "partial",
            "memory_backend_label": "Compiler Snapshot",
            "latest_execution_engine_present": True,
            "latest_execution_engine_mode": "bounded",
            "unrelated_dashboard_field": "not hook context",
        },
    }))
    before = source.read_bytes()

    actual = alignment_context._runtime_surface_compact(tmp_path)

    assert actual == {
        "status": "recorded",
        "recorded_status": "active",
        "source": "odylith/compass/runtime/current.v1.json",
        "freshness": "unverified",
        "enabled": True,
        "memory_status": "partial",
        "memory_backend_label": "Compiler Snapshot",
        "latest_execution_engine_present": True,
        "latest_execution_engine_mode": "bounded",
    }
    assert source.read_bytes() == before
    assert not (tmp_path / ".odylith").exists()
    receipt = host_intervention_support._format_substrate_alignment(
        {"context_packet": {"runtime_surface_summary": actual}}, prefix="Test context",
    )
    assert "memory=Compiler Snapshot [recorded; freshness unverified]" in receipt


@pytest.mark.parametrize("content", [None, b"{", b"[]", b"{}", b'{"odylith_runtime": []}', b"\xff"])
def test_absent_or_invalid_recorded_evidence_never_rebuilds(tmp_path: Path, content):
    source = tmp_path / "odylith/compass/runtime/current.v1.json"
    if content is not None:
        source.parent.mkdir(parents=True)
        source.write_bytes(content)

    actual = alignment_context._runtime_surface_compact(tmp_path)

    assert actual["status"] == "unavailable"
    assert "enabled" not in actual
    assert not (tmp_path / ".odylith").exists()


@pytest.mark.parametrize("switch_source", ["environment", "file"])
def test_current_disabled_switch_wins_over_recorded_enabled_state(tmp_path: Path, monkeypatch, switch_source):
    if switch_source == "environment":
        monkeypatch.setenv("ODYLITH_MODE", "off")
    else:
        switch = summary.odylith_ablation.switch_path(repo_root=tmp_path)
        switch.parent.mkdir(parents=True)
        switch.write_text('{"enabled": false}')

    def forbidden_read(path):
        pytest.fail("disabled alignment read stale recorded evidence")

    monkeypatch.setattr(summary.odylith_context_cache, "read_json_object", forbidden_read)
    assert alignment_context._runtime_surface_compact(tmp_path) == {
        "status": "disabled", "enabled": False, "memory_status": "disabled",
    }
