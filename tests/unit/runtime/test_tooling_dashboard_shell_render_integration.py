from __future__ import annotations

import json
from pathlib import Path

from odylith.runtime.surfaces import render_tooling_dashboard as renderer


def _legacy_payload_key(*parts: str) -> str:
    return "_".join(parts)


def _legacy_ui_phrase(*parts: str) -> str:
    return " ".join(parts)


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


def test_render_tooling_dashboard_does_not_include_status_packet_card(tmp_path: Path, monkeypatch) -> None:  # noqa: ANN001
    _seed_shell_fixture(tmp_path)
    monkeypatch.setattr(
        renderer.delivery_surface_payload_runtime,
        "load_delivery_surface_payload",
        lambda **kwargs: {
            _legacy_payload_key("memory", "snapshot"): {},
            _legacy_payload_key("evaluation", "snapshot"): {},
            _legacy_payload_key("optimization", "snapshot"): {
                "latest_packet": {
                    "workstream": "B-072",
                    _legacy_payload_key("execution", "governance", "present"): True,
                    _legacy_payload_key("execution", "governance", "outcome"): "deny",
                    _legacy_payload_key("execution", "governance", "mode"): "recover",
                    _legacy_payload_key("execution", "governance", "next", "move"): "recover.current_blocker",
                    _legacy_payload_key("execution", "governance", "blocker"): "waiting approval",
                    _legacy_payload_key("execution", "governance", "history", "rule", "hits"): [
                        "lane_drift_preflight"
                    ],
                    _legacy_payload_key("execution", "governance", "pressure", "signals"): ["wait:awaiting_callback"],
                    _legacy_payload_key("execution", "governance", "nearby", "denial", "actions"): [
                        "explore.broad_reset"
                    ],
                    _legacy_payload_key(
                        "execution",
                        "governance",
                        "runtime",
                        "invalidated",
                        "by",
                        "step",
                    ): "render_compass_dashboard",
                    _legacy_payload_key("execution", "governance", "host", "family"): "claude",
                    _legacy_payload_key("execution", "governance", "host", "supports", "native", "spawn"): False,
                    _legacy_payload_key("execution", "governance", "resume", "token"): "resume:B-072",
                }
            },
        },
    )
    monkeypatch.setattr(renderer, "_build_self_host_payload", lambda **kwargs: {})

    rc = renderer.main(["--repo-root", str(tmp_path), "--output", "odylith/index.html"])

    assert rc == 0
    html = (tmp_path / "odylith" / "index.html").read_text(encoding="utf-8")
    payload_js = (tmp_path / "odylith" / "tooling-payload.v1.js").read_text(encoding="utf-8")
    assert _legacy_ui_phrase("Latest", "Governed", "Packet") not in html
    assert "recover.current_blocker" not in html
    assert "waiting approval" not in html
    assert "explore.broad_reset" not in html
    assert "render_compass_dashboard" not in html
    assert "resume:B-072" not in html
    assert _legacy_payload_key("optimization", "snapshot") not in payload_js
