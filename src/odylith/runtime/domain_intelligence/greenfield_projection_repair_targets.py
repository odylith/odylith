"""Resolve generated preview findings to source-owned repair facts."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from odylith.runtime.common.value_coercion import normalize_string
from odylith.runtime.domain_intelligence.greenfield_artifact_plan import artifact_plan_expand_projection_scope
from odylith.runtime.domain_intelligence.greenfield_artifact_plan import artifact_plan_projection_for_path
from odylith.runtime.domain_intelligence.greenfield_artifact_plan import artifact_plan_source_address_for_path
from odylith.runtime.domain_intelligence.greenfield_artifact_plan import artifact_projection_id


@dataclass(frozen=True)
class ProjectionRepairTarget:
    """A preview-quality finding mapped back to an executable source fact."""

    target_layer: str
    target_path: str
    semantic_node_id: str
    operation_kind: str
    affected_projections: tuple[str, ...]
    projection_kind: str


_ACCEPTED_PROJECT_PROPOSAL_PREFIX = "prewrite_package.accepted_project_preview.proposal."
_PROJECT_DASHBOARD_CONTRACT_PREFIX = "prewrite_package.project_dashboard_preview.product_story.release_contract["
_PROJECT_DASHBOARD_CONTRACT_SUFFIX = "].body"
_FIRST_PATH_PREVIEW_PATHS = frozenset(
    {
        "prewrite_package.next_steps_preview.implementation_prompt",
        "prewrite_package.accepted_project_preview.source_launch.implementation_prompt",
    }
)
_PROOF_BOUNDARY_PREVIEW_PATHS = frozenset(
    {
        "prewrite_package.compass_memory_preview.proof",
    }
)
_DASHBOARD_ARTIFACT_CARD_TARGETS = {
    0: ("project_brief.purpose", "ArtifactPlanIR.project_brief.purpose"),
    2: ("project_brief.operating_principle", "ArtifactPlanIR.project_brief.operating_principle"),
    3: ("project_brief.project_outcome", "ArtifactPlanIR.project_brief.project_outcome"),
}


def projection_repair_target_for_finding(
    finding: Mapping[str, Any],
) -> ProjectionRepairTarget | None:
    """Return the sanctioned repair target for a rendered preview finding."""

    target_path = normalize_string(finding.get("target_path"))
    projection_id = artifact_projection_id(finding.get("projection_id")) or artifact_projection_id(finding.get("surface"))
    if not target_path:
        return None
    if target_path.startswith(_ACCEPTED_PROJECT_PROPOSAL_PREFIX):
        return _accepted_project_proposal_target(target_path, projection_id=projection_id)
    dashboard_card_index = _project_dashboard_contract_index(target_path)
    if dashboard_card_index is not None:
        return _project_dashboard_card_target(dashboard_card_index, projection_id=projection_id or "project_dashboard")
    if target_path in _FIRST_PATH_PREVIEW_PATHS:
        return _semantic_first_path_target(projection_id=projection_id)
    if target_path in _PROOF_BOUNDARY_PREVIEW_PATHS:
        return _semantic_proof_boundary_target(projection_id=projection_id)
    if target_path.startswith("prewrite_package.project_brief_preview."):
        return _artifact_plan_dict_preview_target(
            target_path,
            prefix="prewrite_package.project_brief_preview.",
            root="project_brief",
            projection_id=projection_id or "project_brief",
        )
    return None


def projection_repair_target_value(
    proposal: Mapping[str, Any],
    target_path: str,
) -> Any:
    """Read the current source fact for structured repair evidence."""

    path = normalize_string(target_path)
    if not path:
        return ""
    return _read_path(proposal, path)


def _accepted_project_proposal_target(target_path: str, *, projection_id: str) -> ProjectionRepairTarget | None:
    source_path = target_path[len(_ACCEPTED_PROJECT_PROPOSAL_PREFIX) :]
    if not _artifact_plan_source_path(source_path):
        return None
    source_projection = artifact_plan_projection_for_path(source_path)
    affected = tuple(
        dict.fromkeys(
            projection
            for projection in (
                source_projection,
                "accepted_project",
                "project_dashboard" if source_projection in {"atlas", "project_brief", "release"} else "",
                projection_id,
            )
            if projection
        )
    )
    return ProjectionRepairTarget(
        target_layer="artifact_plan",
        target_path=source_path,
        semantic_node_id=f"ArtifactPlanIR.{source_path}",
        operation_kind="artifact_plan_projection",
        affected_projections=affected,
        projection_kind=source_projection or projection_id or "accepted_project",
    )


def _artifact_plan_dict_preview_target(
    target_path: str,
    *,
    prefix: str,
    root: str,
    projection_id: str,
) -> ProjectionRepairTarget | None:
    relative = target_path[len(prefix) :]
    if not relative or "[" in relative:
        return None
    source_path = f"{root}.{relative}"
    if not _artifact_plan_source_path(source_path):
        return None
    return ProjectionRepairTarget(
        target_layer="artifact_plan",
        target_path=source_path,
        semantic_node_id=f"ArtifactPlanIR.{source_path}",
        operation_kind="artifact_plan_projection",
        affected_projections=tuple(dict.fromkeys((projection_id, artifact_plan_projection_for_path(source_path)))),
        projection_kind=projection_id,
    )


def _project_dashboard_contract_index(target_path: str) -> int | None:
    if not target_path.startswith(_PROJECT_DASHBOARD_CONTRACT_PREFIX) or not target_path.endswith(
        _PROJECT_DASHBOARD_CONTRACT_SUFFIX
    ):
        return None
    raw_index = target_path[
        len(_PROJECT_DASHBOARD_CONTRACT_PREFIX) : len(target_path) - len(_PROJECT_DASHBOARD_CONTRACT_SUFFIX)
    ]
    if not raw_index.isdecimal():
        return None
    return int(raw_index)


def _project_dashboard_card_target(index: int, *, projection_id: str) -> ProjectionRepairTarget | None:
    if index == 1:
        return _semantic_first_path_target(projection_id=projection_id)
    if index == 4:
        return _semantic_proof_boundary_target(projection_id=projection_id)
    artifact_target = _DASHBOARD_ARTIFACT_CARD_TARGETS.get(index)
    if artifact_target is None:
        return None
    target_path, semantic_node_id = artifact_target
    affected = artifact_plan_expand_projection_scope((artifact_plan_projection_for_path(target_path), projection_id))
    return ProjectionRepairTarget(
        target_layer="artifact_plan",
        target_path=target_path,
        semantic_node_id=semantic_node_id,
        operation_kind="artifact_plan_projection",
        affected_projections=affected,
        projection_kind=artifact_plan_projection_for_path(target_path) or projection_id,
    )


def _semantic_first_path_target(*, projection_id: str) -> ProjectionRepairTarget:
    return ProjectionRepairTarget(
        target_layer="semantic_model",
        target_path="semantic_model.first_path_contract",
        semantic_node_id="SemanticModelIR.first_path_contract",
        operation_kind="semantic_first_path",
        affected_projections=tuple(dict.fromkeys(projection for projection in (projection_id, "project_dashboard") if projection)),
        projection_kind=projection_id or "project_dashboard",
    )


def _semantic_proof_boundary_target(*, projection_id: str) -> ProjectionRepairTarget:
    return ProjectionRepairTarget(
        target_layer="semantic_model",
        target_path="semantic_model.domain_ontology.proof_boundary",
        semantic_node_id="SemanticModelIR.domain_ontology.proof_boundary",
        operation_kind="semantic_proof_boundary",
        affected_projections=tuple(dict.fromkeys(projection for projection in (projection_id, "compass") if projection)),
        projection_kind=projection_id or "compass",
    )


def _artifact_plan_source_path(path: str) -> bool:
    return artifact_plan_source_address_for_path(path) is not None


def _read_path(value: Any, path: str) -> Any:
    current = value
    for part in _path_parts(path):
        if isinstance(part, int):
            if not isinstance(current, Sequence) or isinstance(current, (str, bytes, bytearray)):
                return ""
            if part < 0 or part >= len(current):
                return ""
            current = current[part]
            continue
        if not isinstance(current, Mapping):
            return ""
        current = current.get(part)
    return current


def _path_parts(path: str) -> tuple[str | int, ...]:
    parts: list[str | int] = []
    for segment in path.split("."):
        if not segment:
            continue
        while segment:
            bracket = segment.find("[")
            if bracket < 0:
                parts.append(segment)
                break
            if bracket > 0:
                parts.append(segment[:bracket])
            close = segment.find("]", bracket + 1)
            if close < 0:
                break
            index = segment[bracket + 1 : close]
            if index.isdecimal():
                parts.append(int(index))
            segment = segment[close + 1 :]
    return tuple(parts)


__all__ = [
    "ProjectionRepairTarget",
    "projection_repair_target_for_finding",
    "projection_repair_target_value",
]
