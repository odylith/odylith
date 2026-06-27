"""Shared ArtifactPlanIR projection contract for greenfield repair."""

from __future__ import annotations

from typing import Any

from odylith.runtime.common.value_coercion import normalize_token


ARTIFACT_PLAN_IR_VERSION = "odylith.greenfield.artifact_plan_ir.v1"
ARTIFACT_PLAN_DICT_ROOTS = frozenset({"project_brief", "release_plan", "program"})
ARTIFACT_PLAN_LIST_ROOTS = frozenset({"assumptions", "open_questions", "risks", "validation_strategy"})
ARTIFACT_PLAN_ROW_ROOTS = frozenset({"backlog", "components", "diagrams"})
ARTIFACT_PLAN_ROOT_ALIASES = {
    "radar": "backlog",
    "registry": "components",
    "atlas": "diagrams",
    "release": "release_plan",
}
ARTIFACT_PLAN_IMMUTABLE_FIELDS = frozenset(
    {
        "component_id",
        "created_at",
        "id",
        "provisional_release_id",
        "registry_path",
        "schema_version",
        "slug",
        "spec_path",
        "updated_at",
        "workstream_id",
    }
)

_PROJECTION_ALIASES = {
    "accepted_project": "accepted_project",
    "artifact_draft_set": "artifact_draft_set",
    "atlas": "atlas",
    "backlog": "radar",
    "compass": "compass",
    "components": "registry",
    "diagrams": "atlas",
    "next_steps": "next_steps",
    "operator_next_steps": "next_steps",
    "program": "release",
    "project_brief": "project_brief",
    "radar": "radar",
    "registry": "registry",
    "release": "release",
    "release_plan": "release",
    "rendered_atlas_sources": "atlas",
    "rendered_component_specs": "registry",
}
_IGNORED_DIRECT_PROJECTIONS = frozenset({"review_report"})


def artifact_plan_canonical_root(value: Any) -> str:
    """Return the canonical proposal root owned by ArtifactPlanIR."""

    token = normalize_token(value)
    return ARTIFACT_PLAN_ROOT_ALIASES.get(token, token)


def artifact_plan_root_kind(value: Any) -> str:
    root = artifact_plan_canonical_root(value)
    if root in ARTIFACT_PLAN_DICT_ROOTS:
        return "dict"
    if root in ARTIFACT_PLAN_LIST_ROOTS:
        return "list"
    if root in ARTIFACT_PLAN_ROW_ROOTS:
        return "row"
    return ""


def artifact_plan_is_immutable_field(value: Any) -> bool:
    return normalize_token(value) in ARTIFACT_PLAN_IMMUTABLE_FIELDS


def artifact_projection_id(value: Any) -> str:
    token = normalize_token(value)
    if not token or token in _IGNORED_DIRECT_PROJECTIONS:
        return ""
    return _PROJECTION_ALIASES.get(token, token if token in _PROJECTION_ALIASES.values() else "")


def artifact_plan_projection_for_path(value: Any) -> str:
    token = normalize_token(value)
    if not token:
        return ""
    direct = artifact_projection_id(token)
    if direct:
        return direct
    route_token = token.replace("[", "_").replace("]", "").replace(".", "_")
    for alias, projection in _PROJECTION_ALIASES.items():
        if route_token == alias or route_token.startswith(f"{alias}_") or f"_{alias}_" in route_token:
            return projection
    root = artifact_plan_canonical_root(route_token.split("_", 1)[0])
    return artifact_projection_id(root)


def artifact_plan_affected_projections(
    *,
    projection_id: Any = "",
    target_path: Any = "",
    surface: Any = "",
) -> tuple[str, ...]:
    direct = artifact_projection_id(projection_id)
    if direct and direct != "artifact_draft_set":
        return (direct,)
    path_projection = artifact_plan_projection_for_path(target_path)
    if path_projection:
        return (path_projection,)
    surface_projection = artifact_projection_id(surface)
    if surface_projection:
        return (surface_projection,)
    return ()


def artifact_draft_repair_projection(value: Any) -> str:
    projection = artifact_projection_id(value)
    return projection or artifact_plan_projection_for_path(value)


__all__ = [
    "ARTIFACT_PLAN_DICT_ROOTS",
    "ARTIFACT_PLAN_IR_VERSION",
    "ARTIFACT_PLAN_LIST_ROOTS",
    "ARTIFACT_PLAN_ROW_ROOTS",
    "artifact_draft_repair_projection",
    "artifact_plan_affected_projections",
    "artifact_plan_canonical_root",
    "artifact_plan_is_immutable_field",
    "artifact_plan_projection_for_path",
    "artifact_plan_root_kind",
    "artifact_projection_id",
]
