"""Shared ArtifactPlanIR projection contract for greenfield repair."""

from __future__ import annotations

from collections.abc import Mapping
from collections.abc import Sequence
from dataclasses import dataclass
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
ARTIFACT_PLAN_ROW_ROOT_BY_PROJECTION = {
    "atlas": "diagrams",
    "radar": "backlog",
    "registry": "components",
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
    "atlas_catalog_rows": "atlas",
    "rendered_atlas_sources": "atlas",
    "rendered_component_specs": "registry",
    "risks": "project_brief",
    "validation_strategy": "project_brief",
}
_IGNORED_DIRECT_PROJECTIONS = frozenset({"review_report"})
_PROJECTION_DEPENDENCIES = {
    "accepted_project": ("project_dashboard",),
    "project_brief": ("accepted_project", "project_dashboard", "compass", "next_steps"),
    "registry": ("project_brief", "accepted_project", "project_dashboard", "compass", "next_steps"),
    "atlas": ("accepted_project", "project_dashboard"),
    "release": ("accepted_project", "project_dashboard", "compass", "next_steps"),
    "radar": ("project_brief", "accepted_project", "project_dashboard", "compass", "next_steps"),
    "program": ("accepted_project", "project_dashboard", "compass", "next_steps", "release"),
}
_FULL_PREWRITE_PROJECTIONS = frozenset({"radar", "program"})
_ARTIFACT_PLAN_SOURCE_ENVELOPES = frozenset({"artifactplanir", "proposal"})
_PREWRITE_PACKAGE_ROUTE_ALIASES = {
    "accepted_project": "accepted_project",
    "accepted_project_preview": "accepted_project",
    "atlas": "atlas",
    "backlog_result": "radar",
    "compass": "compass",
    "compass_memory_preview": "compass",
    "next_steps": "next_steps",
    "next_steps_preview": "next_steps",
    "project_brief": "project_brief",
    "project_brief_preview": "project_brief",
    "project_dashboard": "project_dashboard",
    "project_dashboard_preview": "project_dashboard",
    "radar": "radar",
    "registry": "registry",
    "release": "release",
    "release_assignment_result": "release",
    "release_target_result": "release",
    "atlas_catalog_rows": "atlas",
    "rendered_atlas_sources": "atlas",
    "rendered_component_specs": "registry",
}
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


@dataclass(frozen=True)
class ProjectionSourceAddress:
    """Executable source fact address for an ArtifactPlanIR projection repair."""

    target_layer: str
    target_path: str
    semantic_node_id: str
    fact_id: str
    projection_id: str
    allowed_projections: tuple[str, ...]
    text_kind: str


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


def artifact_plan_row_root_for_projection(value: Any) -> str:
    projection = artifact_projection_id(value)
    return ARTIFACT_PLAN_ROW_ROOT_BY_PROJECTION.get(projection, "")


def artifact_plan_source_address_for_path(
    value: Any,
    *,
    projection_id: Any = "",
    semantic_node_id: Any = "",
    text_kind: Any = "",
) -> ProjectionSourceAddress | None:
    """Return an executable ArtifactPlanIR source address, never a projection guess."""

    source_path = artifact_plan_source_path(value)
    if not artifact_plan_exact_source_path(source_path):
        return None
    projection = artifact_projection_id(projection_id) or artifact_plan_projection_for_path(source_path)
    if not projection:
        return None
    fact_id = f"ArtifactPlanIR.{source_path}"
    semantic_node = normalize_string(semantic_node_id)
    if not semantic_node.startswith("ArtifactPlanIR."):
        semantic_node = fact_id
    return ProjectionSourceAddress(
        target_layer="artifact_plan",
        target_path=source_path,
        semantic_node_id=semantic_node,
        fact_id=fact_id,
        projection_id=projection,
        allowed_projections=(projection,),
        text_kind=normalize_token(text_kind) or artifact_plan_root_kind(_source_root(source_path)) or "semantic_fact",
    )


def artifact_plan_source_path(value: Any) -> str:
    path = normalize_string(value)
    if not path:
        return ""
    for prefix in ("proposal.", "ArtifactPlanIR."):
        if path.startswith(prefix):
            path = path[len(prefix) :]
            break
    root = artifact_plan_canonical_root(_source_root(path))
    if not root:
        return ""
    tail = _source_tail(path)
    return f"{root}{tail}"


def artifact_plan_exact_source_path(value: Any) -> bool:
    path = normalize_string(value)
    if not path:
        return False
    parts = _source_path_parts(path)
    if not parts:
        return False
    root = artifact_plan_canonical_root(parts[0])
    kind = artifact_plan_root_kind(root)
    if kind == "dict":
        return len(parts) >= 2
    if kind == "list":
        return len(parts) == 1 or (len(parts) >= 2 and parts[1].isdecimal())
    if kind == "row":
        return len(parts) >= 3 and parts[1].isdecimal()
    return False


def artifact_plan_is_immutable_field(value: Any) -> bool:
    return normalize_token(value) in ARTIFACT_PLAN_IMMUTABLE_FIELDS


def artifact_projection_id(value: Any) -> str:
    token = normalize_token(value)
    if not token or token in _IGNORED_DIRECT_PROJECTIONS:
        return ""
    return _PROJECTION_ALIASES.get(token, token if token in _PROJECTION_ALIASES.values() else "")


def artifact_plan_projection_for_path(value: Any) -> str:
    path = normalize_string(value)
    if not path:
        return ""
    direct = artifact_projection_id(path)
    if direct:
        return direct
    parts = _artifact_plan_route_parts(path)
    if not parts:
        return ""
    head = parts[0]
    if head == "prewrite_package":
        return _prewrite_package_route_projection(parts[1:])
    if head in _ARTIFACT_PLAN_SOURCE_ENVELOPES:
        return _artifact_plan_source_root_projection(parts[1:])
    return _artifact_plan_source_root_projection(parts)


def _artifact_plan_source_root_projection(parts: Sequence[str]) -> str:
    if not parts:
        return ""
    root = artifact_plan_canonical_root(parts[0])
    return artifact_projection_id(root)


def _prewrite_package_route_projection(parts: Sequence[str]) -> str:
    if not parts:
        return ""
    return _PREWRITE_PACKAGE_ROUTE_ALIASES.get(parts[0], "")


def _artifact_plan_route_parts(value: str) -> tuple[str, ...]:
    rows: list[str] = []
    current: list[str] = []
    for char in value:
        if char.isalnum() or char in {"_", "-"}:
            current.append(char)
            continue
        if current:
            rows.append(normalize_token("".join(current)))
            current = []
    if current:
        rows.append(normalize_token("".join(current)))
    return tuple(row for row in rows if row)


def _source_root(path: str) -> str:
    return normalize_token(path.split("[", 1)[0].split(".", 1)[0])


def _source_tail(path: str) -> str:
    text = normalize_string(path)
    boundaries = [index for index in (text.find("["), text.find(".")) if index >= 0]
    if not boundaries:
        return ""
    return text[min(boundaries) :]


def _source_path_parts(path: str) -> tuple[str, ...]:
    text = normalize_string(path)
    parts: list[str] = []
    current: list[str] = []
    for char in text:
        if char.isalnum() or char in {"_", "-"}:
            current.append(char)
            continue
        if current:
            parts.append(normalize_token("".join(current)))
            current = []
    if current:
        parts.append(normalize_token("".join(current)))
    return tuple(part for part in parts if part)


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
    "ARTIFACT_PLAN_ROW_ROOT_BY_PROJECTION",
    "ProjectionSourceAddress",
    "artifact_draft_exact_repair_path",
    "artifact_draft_repair_projection",
    "artifact_plan_affected_projections",
    "artifact_plan_canonical_root",
    "artifact_plan_exact_source_path",
    "artifact_plan_expand_projection_scope",
    "artifact_plan_is_immutable_field",
    "artifact_plan_operation_affected_projections",
    "artifact_plan_projection_for_path",
    "artifact_plan_row_root_for_projection",
    "artifact_plan_root_kind",
    "artifact_plan_scope_requires_full_prewrite",
    "artifact_plan_source_address_for_path",
    "artifact_plan_source_path",
    "artifact_projection_id",
]
