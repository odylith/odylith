"""Shared ArtifactPlanIR projection contract for greenfield repair."""

from __future__ import annotations

from collections.abc import Mapping
from collections.abc import Sequence
from typing import Any

from odylith.runtime.common.value_coercion import normalize_string_list
from odylith.runtime.common.value_coercion import normalize_string
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
    "assumptions": "project_brief",
    "artifact_draft_set": "artifact_draft_set",
    "atlas": "atlas",
    "backlog": "radar",
    "compass": "compass",
    "components": "registry",
    "diagrams": "atlas",
    "next_steps": "next_steps",
    "operator_next_steps": "next_steps",
    "open_questions": "project_brief",
    "program": "program",
    "project_dashboard": "project_dashboard",
    "project_dashboard_preview": "project_dashboard",
    "project_brief": "project_brief",
    "radar": "radar",
    "registry": "registry",
    "release": "release",
    "release_plan": "release",
    "rendered_atlas_sources": "atlas",
    "rendered_component_specs": "registry",
    "risks": "project_brief",
    "validation_strategy": "project_brief",
}
_ARTIFACT_PLAN_ENVELOPE_PREFIXES = ("proposal_", "prewrite_package_", "artifactplanir_")
_IGNORED_DIRECT_PROJECTIONS = frozenset({"review_report"})
_PROJECTION_DEPENDENCIES = {
    "project_brief": ("accepted_project", "compass", "next_steps"),
    "registry": ("project_brief", "accepted_project", "compass", "next_steps"),
    "atlas": ("accepted_project",),
    "release": ("accepted_project", "compass", "next_steps"),
    "radar": ("project_brief", "accepted_project", "compass", "next_steps"),
    "program": ("accepted_project", "compass", "next_steps", "release"),
}
_FULL_PREWRITE_PROJECTIONS = frozenset({"radar", "program"})
_ARTIFACT_DRAFT_EXACT_TARGETS = frozenset(
    {
        "prewrite_package.backlog_result.backlog_index_text",
    }
)
_ARTIFACT_DRAFT_EXACT_PREFIXES = (
    "prewrite_package.rendered_component_specs::",
    "prewrite_package.rendered_atlas_sources::",
    "prewrite_package.backlog_result.idea_files::",
    "prewrite_package.accepted_project_preview.",
    "prewrite_package.compass_memory_preview.",
    "prewrite_package.project_brief_preview.",
    "prewrite_package.next_steps_preview.",
)
_PROJECT_DASHBOARD_PREVIEW_PREFIX = "prewrite_package.project_dashboard_preview."


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
    for candidate in _artifact_plan_route_candidates(route_token):
        for alias, projection in _PROJECTION_ALIASES.items():
            if candidate == alias or candidate.startswith(f"{alias}_") or f"_{alias}_" in candidate:
                return projection
        root = artifact_plan_canonical_root(candidate.split("_", 1)[0])
        projection = artifact_projection_id(root)
        if projection:
            return projection
    return ""


def _artifact_plan_route_candidates(route_token: str) -> tuple[str, ...]:
    candidates = [route_token]
    for prefix in _ARTIFACT_PLAN_ENVELOPE_PREFIXES:
        if route_token.startswith(prefix):
            candidates.append(route_token[len(prefix) :])
    return tuple(dict.fromkeys(candidate for candidate in candidates if candidate))


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


def artifact_plan_operation_affected_projections(operation: Mapping[str, Any]) -> tuple[str, ...]:
    """Return the sanctioned projection scope carried by one PatchSet operation."""

    affected = operation.get("affected_projections")
    rows = (
        normalize_string_list(affected, limit=16)
        if isinstance(affected, Sequence) and not isinstance(affected, (str, bytes, bytearray))
        else ()
    )
    projections = tuple(projection for projection in (artifact_projection_id(row) for row in rows) if projection)
    if projections:
        return tuple(dict.fromkeys(projections))
    return artifact_plan_affected_projections(
        projection_id=operation.get("projection_kind"),
        target_path=operation.get("target_path"),
        surface=operation.get("surface"),
    )


def artifact_plan_expand_projection_scope(projections: Sequence[Any]) -> tuple[str, ...]:
    """Expand primary projection IDs through package preview dependencies."""

    scope: list[str] = []
    for raw_projection in projections:
        projection = artifact_projection_id(raw_projection)
        if not projection:
            continue
        scope.append(projection)
        scope.extend(_PROJECTION_DEPENDENCIES.get(projection, ()))
    return tuple(dict.fromkeys(scope))


def artifact_plan_scope_requires_full_prewrite(projections: Sequence[Any]) -> bool:
    """Return true when a scope needs staged Radar/program recomputation."""

    expanded = artifact_plan_expand_projection_scope(projections)
    return any(projection in _FULL_PREWRITE_PROJECTIONS for projection in expanded)


def artifact_draft_repair_projection(value: Any) -> str:
    projection = artifact_projection_id(value)
    return projection or artifact_plan_projection_for_path(value)


def artifact_draft_exact_repair_path(value: Any) -> bool:
    """Return true only for artifact-draft paths that identify one repair leaf."""

    target = normalize_string(value)
    if not target:
        return False
    if target in _ARTIFACT_DRAFT_EXACT_TARGETS:
        return True
    for prefix in _ARTIFACT_DRAFT_EXACT_PREFIXES:
        if target.startswith(prefix):
            return bool(target[len(prefix) :])
    if target.startswith(_PROJECT_DASHBOARD_PREVIEW_PREFIX):
        relative = target[len(_PROJECT_DASHBOARD_PREVIEW_PREFIX) :]
        return bool(relative) and not relative.endswith("]")
    return False


__all__ = [
    "ARTIFACT_PLAN_DICT_ROOTS",
    "ARTIFACT_PLAN_IR_VERSION",
    "ARTIFACT_PLAN_LIST_ROOTS",
    "ARTIFACT_PLAN_ROW_ROOTS",
    "artifact_draft_exact_repair_path",
    "artifact_draft_repair_projection",
    "artifact_plan_affected_projections",
    "artifact_plan_canonical_root",
    "artifact_plan_expand_projection_scope",
    "artifact_plan_is_immutable_field",
    "artifact_plan_operation_affected_projections",
    "artifact_plan_projection_for_path",
    "artifact_plan_root_kind",
    "artifact_plan_scope_requires_full_prewrite",
    "artifact_projection_id",
]
