"""Graph-native accepted-project adapter for the Project dashboard."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any


_DASHBOARD_KEY = "project_dashboard"
_DASHBOARD_VERSION = "odylith.greenfield.semantic-project-dashboard.v1"


def proposal_from_sources(*, repo_root: Path, shell_payload: Mapping[str, Any]) -> dict[str, Any]:
    """Return only a precompiled graph-native Project dashboard payload."""

    for value in (
        shell_payload.get(_DASHBOARD_KEY),
        shell_payload.get("accepted_project"),
        shell_payload.get("greenfield_proposal"),
        shell_payload.get("proposal"),
    ):
        dashboard = _dashboard_payload(value)
        if dashboard:
            return {_DASHBOARD_KEY: dashboard}
    for path in (
        Path(repo_root) / "odylith/runtime/source/accepted-project.v1.json",
        Path(repo_root) / "odylith/runtime/source/greenfield-project.v1.json",
    ):
        dashboard = _dashboard_payload(_read_mapping(path))
        if dashboard:
            return {_DASHBOARD_KEY: dashboard}
    return {}


def build_greenfield_payload(*, proposal: Mapping[str, Any], repo_root: Path) -> dict[str, Any]:
    """Return the exact dashboard compiled before confirmation."""

    del repo_root
    dashboard = _dashboard_payload(proposal)
    if not dashboard:
        raise ValueError("accepted greenfield project lacks a graph-native dashboard projection")
    return dashboard


def _dashboard_payload(value: object) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    if str(value.get("schema_version") or "").strip() == _DASHBOARD_VERSION:
        return dict(value)
    nested = value.get(_DASHBOARD_KEY)
    if isinstance(nested, Mapping) and str(nested.get("schema_version") or "").strip() == _DASHBOARD_VERSION:
        return dict(nested)
    for key in ("accepted_project", "greenfield_proposal", "proposal"):
        nested = value.get(key)
        if isinstance(nested, Mapping):
            dashboard = _dashboard_payload(nested)
            if dashboard:
                return dashboard
    return {}


def _read_mapping(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return dict(value) if isinstance(value, Mapping) else {}


__all__ = ["build_greenfield_payload", "proposal_from_sources"]
