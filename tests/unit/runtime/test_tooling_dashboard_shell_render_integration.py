from __future__ import annotations

import json
from pathlib import Path

from odylith.runtime.surfaces import render_tooling_dashboard as renderer


def _seed_shell_fixture(repo_root: Path) -> None:
    for surface in ("radar", "atlas", "compass", "registry", "casebook"):
        surface_root = repo_root / "odylith" / surface
        surface_root.mkdir(parents=True, exist_ok=True)
        (surface_root / f"{surface}.html").write_text(f"<!doctype html><title>{surface.title()}</title>\n", encoding="utf-8")
    runtime_source = repo_root / "odylith" / "runtime" / "source"
    runtime_source.mkdir(parents=True, exist_ok=True)
    (runtime_source / "tooling_shell.v1.json").write_text(
        json.dumps({"shell_repo_label": "Repo · Odylith", "maintainer_notes": []}, indent=2) + "\n",
        encoding="utf-8",
    )


def test_render_tooling_dashboard_includes_latest_governed_packet_card(tmp_path: Path, monkeypatch) -> None:  # noqa: ANN001
    _seed_shell_fixture(tmp_path)
    monkeypatch.setattr(
        renderer.odylith_context_engine_store,
        "load_delivery_surface_payload",
        lambda **kwargs: {
            "memory_snapshot": {},
            "evaluation_snapshot": {},
            "optimization_snapshot": {
                "latest_packet": {
                    "workstream": "B-072",
                    "execution_governance_present": True,
                    "execution_governance_outcome": "deny",
                    "execution_governance_mode": "recover",
                    "execution_governance_next_move": "recover.current_blocker",
                    "execution_governance_blocker": "waiting approval",
                    "execution_governance_history_rule_hits": ["lane_drift_preflight"],
                    "execution_governance_pressure_signals": ["wait:awaiting_callback"],
                    "execution_governance_nearby_denial_actions": ["explore.broad_reset"],
                    "execution_governance_runtime_invalidated_by_step": "render_compass_dashboard",
                    "execution_governance_host_family": "claude",
                    "execution_governance_host_supports_native_spawn": False,
                    "execution_governance_resume_token": "resume:B-072",
                }
            },
        },
    )
    monkeypatch.setattr(renderer, "_build_self_host_payload", lambda **kwargs: {})

    rc = renderer.main(["--repo-root", str(tmp_path), "--output", "odylith/index.html"])

    assert rc == 0
    html = (tmp_path / "odylith" / "index.html").read_text(encoding="utf-8")
    assert "Latest Governed Packet" in html
    assert "recover.current_blocker" in html
    assert "waiting approval" in html
    assert "explore.broad_reset" in html
    assert "render_compass_dashboard" in html
    assert "resume:B-072" in html
