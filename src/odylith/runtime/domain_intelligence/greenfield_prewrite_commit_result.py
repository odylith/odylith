"""Pre-confirm success result sealed beside the greenfield repository write set."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_prewrite_surface_stage import (
    GreenfieldStagedSurfaceBuild,
)


def build_greenfield_commit_result_preview(
    *,
    source_root: Path,
    target_root: Path,
    validation_gate: Mapping[str, Any],
    backlog_result: Mapping[str, Any],
    components: Sequence[Mapping[str, Any]],
    diagrams: Sequence[str],
    backlog_topology: Sequence[str],
    staged_surfaces: GreenfieldStagedSurfaceBuild,
    next_steps: Mapping[str, Any],
    prewrite_safety: Mapping[str, Any],
    release_bootstrap: Mapping[str, Any] | None,
    release_target: Mapping[str, Any] | None,
    brand_asset_count: int,
) -> dict[str, Any]:
    """Build the operator result without requiring commit-time artifact parsing."""

    preview = dict(staged_surfaces.surface_refresh_preview)
    dashboard_refresh = {
        "status": "passed",
        "surfaces": list(preview.get("surfaces") or ()),
        "view": str(preview.get("view", "")).strip(),
        "pre_confirm_surface_refresh": preview,
        "rendered_surface_custody": dict(staged_surfaces.rendered_surface_custody),
        "managed_brand_assets": {
            "status": "passed",
            "seeded_count": int(brand_asset_count),
        },
    }
    result = {
        "mode": "applied",
        "validation_gate": dict(validation_gate),
        "backlog": list(backlog_result.get("created", ())),
        "components": [dict(row) for row in components],
        "diagrams": [str(value) for value in diagrams],
        "backlog_topology": [str(value) for value in backlog_topology],
        "atlas_scaffold_logs": list(staged_surfaces.atlas_scaffold_logs),
        "memory": dict(staged_surfaces.memory_record),
        "dashboard_refresh": dashboard_refresh,
        "next_steps": dict(next_steps),
        "prewrite_safety": dict(prewrite_safety),
        "release_bootstrap": dict(release_bootstrap or {"created": False, "release": {}}),
        "release_target": dict(release_target or {"selector": "", "release_id": "none", "events": []}),
        "completion_priority_quality_debt": [],
    }
    return result


def require_greenfield_commit_result_preview(value: object) -> dict[str, Any]:
    """Validate only the sealed reporting envelope needed after commit."""

    if not isinstance(value, Mapping):
        raise ValueError("ProductCreateTransaction is missing a compiled commit result preview")
    payload = dict(value)
    if str(payload.get("mode", "")).strip() != "applied":
        raise ValueError("ProductCreateTransaction commit result preview has an invalid mode")
    for key in ("backlog", "components", "diagrams"):
        if not isinstance(payload.get(key), list):
            raise ValueError(
                f"ProductCreateTransaction commit result preview is missing compiled {key} reporting data"
            )
    dashboard = payload.get("dashboard_refresh")
    if not isinstance(dashboard, Mapping) or str(dashboard.get("status", "")).strip() != "passed":
        raise ValueError("ProductCreateTransaction commit result preview is missing surface refresh proof")
    if payload.get("completion_priority_quality_debt") not in ([], ()):
        raise ValueError("ProductCreateTransaction commit result preview contains unresolved quality debt")
    return payload


__all__ = ["build_greenfield_commit_result_preview", "require_greenfield_commit_result_preview"]
