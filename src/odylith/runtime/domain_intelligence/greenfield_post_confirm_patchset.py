"""Formal semantic and artifact-plan patch requests for greenfield repair."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import asdict, dataclass
from typing import Any

from odylith.runtime.common.value_coercion import dedupe_by_key
from odylith.runtime.common.value_coercion import normalize_string
from odylith.runtime.common.value_coercion import normalize_token
from odylith.runtime.domain_intelligence.greenfield_post_confirm_review import GreenfieldReviewFinding


POST_CONFIRM_PATCHSET_VERSION = "odylith.greenfield.post_confirm.patchset_request.v1"


@dataclass(frozen=True)
class GreenfieldPatchOperation:
    """One bounded semantic or artifact-plan repair target."""

    operation_id: str
    target_layer: str
    target_path: str
    semantic_node_id: str
    issue_code: str
    source_finding: str
    affected_projections: tuple[str, ...]
    requested_action: str
    rejected_interpretation: str = ""
    confidence: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class GreenfieldPatchSet:
    """Repair-plan contract passed to host reasoning or deterministic patch owners."""

    version: str
    status: str
    operations: tuple[GreenfieldPatchOperation, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "status": self.status,
            "operation_count": len(self.operations),
            "operations": [operation.to_dict() for operation in self.operations],
        }


def patchset_request_from_findings(findings: Sequence[GreenfieldReviewFinding]) -> GreenfieldPatchSet:
    """Build stable repair targets without mutating rendered artifacts."""

    operations = [
        operation
        for operation in (_operation_from_finding(finding, index=index) for index, finding in enumerate(findings, 1))
        if operation is not None
    ]
    deduped = tuple(
        dedupe_by_key(
            operations,
            key=lambda operation: (
                operation.target_layer,
                operation.target_path,
                operation.semantic_node_id,
                operation.issue_code,
                operation.source_finding,
                operation.affected_projections,
            ),
        )
    )
    return GreenfieldPatchSet(
        version=POST_CONFIRM_PATCHSET_VERSION,
        status="repairable" if deduped else "no_repairable_operations",
        operations=deduped,
    )


def _operation_from_finding(
    finding: GreenfieldReviewFinding,
    *,
    index: int,
) -> GreenfieldPatchOperation | None:
    if finding.repairability == "unrepairable":
        return None
    target_layer = _target_layer(finding)
    if not target_layer:
        return None
    return GreenfieldPatchOperation(
        operation_id=f"GF-PATCH-{index:03d}",
        target_layer=target_layer,
        target_path=normalize_string(finding.target_path or finding.semantic_node_id) or target_layer,
        semantic_node_id=normalize_string(finding.semantic_node_id),
        issue_code=finding.code,
        source_finding=finding.source,
        affected_projections=_affected_projections(finding),
        requested_action=_requested_action(finding, target_layer=target_layer),
        rejected_interpretation=_rejected_interpretation(finding, target_layer=target_layer),
        confidence=0.2 if target_layer in {"semantic_model", "artifact_plan"} else 0.0,
    )


def _target_layer(finding: GreenfieldReviewFinding) -> str:
    repairability = normalize_token(finding.repairability)
    if repairability in {"semantic_patch", "proposal_repair"}:
        return "semantic_model"
    if repairability == "plan_patch":
        return "artifact_plan"
    if repairability == "safe_package_repair":
        return "artifact_draft_set"
    return ""


def _affected_projections(finding: GreenfieldReviewFinding) -> tuple[str, ...]:
    projection = normalize_token(finding.projection_id)
    if projection and projection not in {"review_report", "artifact_draft_set"}:
        return (projection,)
    path_projection = _projection_from_target_path(finding.target_path)
    if path_projection:
        return (path_projection,)
    surface = normalize_token(finding.surface)
    by_surface = {
        "architect": ("atlas", "registry"),
        "atlas": ("atlas",),
        "domain_expert": ("project_brief", "radar", "atlas"),
        "engineer": ("registry", "next_steps"),
        "operator_next_steps": ("next_steps",),
        "post_confirm_package": ("radar", "registry", "atlas", "project_brief", "next_steps"),
        "product_manager": ("project_brief", "radar", "release"),
        "project_brief": ("project_brief",),
        "radar": ("radar",),
        "registry": ("registry",),
        "release": ("release",),
    }
    return by_surface.get(surface, ("project_brief",))


def _projection_from_target_path(value: str) -> str:
    token = normalize_token(value)
    known = (
        "accepted_project",
        "atlas",
        "backlog",
        "compass",
        "next_steps",
        "project_brief",
        "radar",
        "registry",
        "release",
        "rendered_atlas_sources",
        "rendered_component_specs",
    )
    for item in known:
        if token == item or token.startswith(f"{item}_") or f"_{item}_" in token:
            if item == "backlog":
                return "radar"
            if item == "rendered_atlas_sources":
                return "atlas"
            if item == "rendered_component_specs":
                return "registry"
            return item
    return ""


def _requested_action(finding: GreenfieldReviewFinding, *, target_layer: str) -> str:
    if target_layer == "semantic_model":
        return "Return a semantic patch that corrects the accepted intent interpretation and preserves rejected interpretations."
    if target_layer == "artifact_plan":
        return "Return an artifact-plan patch that changes only sanctioned projection fields before rerender."
    return "Apply only explicitly safe mechanical cleanup, then rerun the same typed review gates."


def _rejected_interpretation(finding: GreenfieldReviewFinding, *, target_layer: str) -> str:
    if target_layer not in {"semantic_model", "artifact_plan"}:
        return ""
    return normalize_string(finding.message)


__all__ = [
    "GreenfieldPatchOperation",
    "GreenfieldPatchSet",
    "POST_CONFIRM_PATCHSET_VERSION",
    "patchset_request_from_findings",
]
