"""Regression coverage for context-engine control-state persistence helpers."""

from __future__ import annotations

import json
from pathlib import Path

from odylith.install.state import write_install_state
from odylith.runtime.context_engine import odylith_control_state


def _seed_product_repo_shape(tmp_path: Path) -> None:
    """Create the minimum product-repo shape needed for posture-sensitive tests."""
    (tmp_path / "pyproject.toml").write_text("[project]\nname='odylith'\nversion='0.1.0'\n", encoding="utf-8")
    (tmp_path / "src" / "odylith").mkdir(parents=True, exist_ok=True)
    registry_root = tmp_path / "odylith" / "registry" / "source"
    registry_root.mkdir(parents=True, exist_ok=True)
    (registry_root / "component_registry.v1.json").write_text('{"version":"v1","components":[]}\n', encoding="utf-8")
    radar_root = tmp_path / "odylith" / "radar" / "source"
    radar_root.mkdir(parents=True, exist_ok=True)
    (radar_root / "INDEX.md").write_text("# Radar\n", encoding="utf-8")


def test_write_state_writes_json_and_js_companion_for_consumer_repo(tmp_path: Path) -> None:
    payload = {
        "updated_utc": "2026-04-01T21:30:00Z",
        "projection_fingerprint": "abc123",
        "updated_projections": ["workstreams"],
    }

    odylith_control_state.write_state(repo_root=tmp_path, payload=payload)

    state_json = odylith_control_state.state_path(repo_root=tmp_path)
    state_js = odylith_control_state.state_js_path(repo_root=tmp_path)
    assert json.loads(state_json.read_text(encoding="utf-8")) == payload
    assert state_js.is_file()
    assignment = state_js.read_text(encoding="utf-8").strip()
    assert assignment.startswith('window["__ODYLITH_CONTEXT_ENGINE_STATE__"] = ')
    js_payload = json.loads(assignment.split(" = ", 1)[1].removesuffix(";"))
    assert js_payload == payload


def test_write_state_skips_js_companion_for_product_repo(tmp_path: Path) -> None:
    _seed_product_repo_shape(tmp_path)
    state_js = odylith_control_state.state_js_path(repo_root=tmp_path)
    state_js.parent.mkdir(parents=True, exist_ok=True)
    state_js.write_text("stale\n", encoding="utf-8")

    odylith_control_state.write_state(
        repo_root=tmp_path,
        payload={"updated_utc": "2026-04-01T21:31:00Z"},
    )

    assert odylith_control_state.state_path(repo_root=tmp_path).is_file()
    assert not state_js.exists()


def test_write_state_keeps_js_companion_for_detached_source_local_product_repo(tmp_path: Path) -> None:
    _seed_product_repo_shape(tmp_path)
    write_install_state(
        repo_root=tmp_path,
        payload={
            "active_version": "source-local",
            "detached": True,
            "installed_versions": {
                "source-local": {
                    "runtime_root": str(tmp_path / ".odylith" / "runtime" / "versions" / "source-local"),
                    "verification": {"mode": "source-local"},
                }
            },
            "activation_history": ["source-local"],
            "last_known_good_version": "0.1.0",
        },
    )

    odylith_control_state.write_state(
        repo_root=tmp_path,
        payload={"updated_utc": "2026-04-02T20:00:00Z"},
    )

    state_js = odylith_control_state.state_js_path(repo_root=tmp_path)
    assert state_js.is_file()
