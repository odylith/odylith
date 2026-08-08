"""Formal semantic and artifact-plan patch requests for greenfield repair."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import asdict, dataclass
from typing import Any

from odylith.runtime.common.value_coercion import dedupe_by_key
from odylith.runtime.common.value_coercion import normalize_string
from odylith.runtime.common.value_coercion import normalize_token
from odylith.runtime.domain_intelligence.greenfield_artifact_plan import artifact_plan_affected_projections
from odylith.runtime.domain_intelligence.greenfield_artifact_plan import artifact_plan_source_address_for_path
from odylith.runtime.domain_intelligence.greenfield_artifact_plan import ProjectionSourceAddress
from odylith.runtime.domain_intelligence.greenfield_projection_repair_targets import ProjectionRepairTarget
from odylith.runtime.domain_intelligence.greenfield_projection_repair_targets import (
    projection_repair_target_for_finding,
)
from odylith.runtime.domain_intelligence.greenfield_preconfirm_rescue_probe import (
    rescue_probe_patch_values,
)
from odylith.runtime.domain_intelligence.greenfield_preconfirm_review import GreenfieldReviewFinding
from odylith.runtime.domain_intelligence.greenfield_semantic_patch_targets import semantic_patch_operation_kind


PRECONFIRM_PATCHSET_VERSION = "odylith.greenfield.preconfirm.patchset_request.v1"


@dataclass(frozen=True)
class GreenfieldPatchOperation:
    """One bounded semantic or artifact-plan repair target."""

    operation_id: str
    target_layer: str
    target_path: str
    semantic_node_id: str
    issue_code: str
    source_finding: str
    operation_kind: str
    repair_owner: str
    projection_kind: str
    affected_projections: tuple[str, ...]
    requested_action: str
    replacement_fact: Any = ""
    decision_ledger_entry: Any = ""
    proof_obligation_delta: Any = ""
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
        version=PRECONFIRM_PATCHSET_VERSION,
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
    repair_target = projection_repair_target_for_finding(finding.to_dict())
    source_address = None if repair_target else _source_address(finding)
    target_layer = repair_target.target_layer if repair_target else _target_layer(finding, source_address=source_address)
    if not target_layer:
        return None
    probe_values = rescue_probe_patch_values(finding)
    operation_kind = (
        normalize_token(probe_values.get("operation_kind"))
        or (repair_target.operation_kind if repair_target else "")
        or _operation_kind(finding, target_layer=target_layer)
    )
    if target_layer == "semantic_model" and not operation_kind:
        return None
    return GreenfieldPatchOperation(
        operation_id=f"GF-PATCH-{index:03d}",
        target_layer=target_layer,
        target_path=_target_path(
            finding,
            repair_target=repair_target,
            source_address=source_address,
            target_layer=target_layer,
        ),
        semantic_node_id=_semantic_node_id(finding, repair_target=repair_target, source_address=source_address),
        issue_code=finding.code,
        source_finding=finding.source,
        operation_kind=operation_kind,
        repair_owner=finding.owner,
        projection_kind=_projection_kind(finding, repair_target=repair_target, source_address=source_address),
        affected_projections=_affected_projections(finding, repair_target=repair_target, source_address=source_address),
        requested_action=_requested_action(finding, target_layer=target_layer),
        replacement_fact=probe_values.get("replacement_fact", ""),
        decision_ledger_entry=probe_values.get("decision_ledger_entry", ""),
        proof_obligation_delta=probe_values.get("proof_obligation_delta", ""),
        rejected_interpretation=_rejected_interpretation(finding, target_layer=target_layer),
        confidence=float(probe_values.get("confidence", 0.2 if target_layer in {"semantic_model", "artifact_plan"} else 0.0)),
    )


def _target_path(
    finding: GreenfieldReviewFinding,
    *,
    repair_target: ProjectionRepairTarget | None,
    source_address: ProjectionSourceAddress | None,
    target_layer: str,
) -> str:
    if repair_target:
        return repair_target.target_path
    if source_address:
        return source_address.target_path
    return normalize_string(finding.target_path or finding.semantic_node_id) or target_layer


def _semantic_node_id(
    finding: GreenfieldReviewFinding,
    *,
    repair_target: ProjectionRepairTarget | None,
    source_address: ProjectionSourceAddress | None,
) -> str:
    if repair_target:
        return repair_target.semantic_node_id
    if source_address:
        return source_address.semantic_node_id
    return normalize_string(finding.semantic_node_id)


def _target_layer(
    finding: GreenfieldReviewFinding,
    *,
    source_address: ProjectionSourceAddress | None,
) -> str:
    repairability = normalize_token(finding.repairability)
    if repairability == "semantic_patch" and source_address is not None:
        return "artifact_plan"
    if repairability == "semantic_patch":
        return "semantic_model"
    if repairability == "plan_patch" and source_address is not None:
        return "artifact_plan"
    return ""


def _source_address(finding: GreenfieldReviewFinding) -> ProjectionSourceAddress | None:
    return artifact_plan_source_address_for_path(
        finding.target_path,
        projection_id=finding.projection_id,
        semantic_node_id=finding.semantic_node_id,
    )


def _affected_projections(
    finding: GreenfieldReviewFinding,
    *,
    repair_target: ProjectionRepairTarget | None = None,
    source_address: ProjectionSourceAddress | None = None,
) -> tuple[str, ...]:
    if repair_target:
        return repair_target.affected_projections
    if source_address:
        return source_address.allowed_projections
    return artifact_plan_affected_projections(
        projection_id=finding.projection_id,
        target_path=finding.target_path,
        surface=finding.surface,
    )


def _projection_kind(
    finding: GreenfieldReviewFinding,
    *,
    repair_target: ProjectionRepairTarget | None = None,
    source_address: ProjectionSourceAddress | None = None,
) -> str:
    if repair_target and repair_target.projection_kind:
        return repair_target.projection_kind
    if source_address:
        return source_address.projection_id
    projections = _affected_projections(finding)
    return projections[0] if len(projections) == 1 else "multi_projection" if projections else ""


def _operation_kind(finding: GreenfieldReviewFinding, *, target_layer: str) -> str:
    if target_layer == "artifact_plan":
        return "artifact_plan_projection"
    if target_layer != "semantic_model":
        return ""
    return semantic_patch_operation_kind(
        target_path=finding.target_path,
        semantic_node_id=finding.semantic_node_id,
    )


def _requested_action(finding: GreenfieldReviewFinding, *, target_layer: str) -> str:
    if target_layer == "semantic_model":
        return (
            "Return a semantic patch that corrects the accepted intent interpretation "
            "and preserves rejected interpretations."
        )
    if target_layer == "artifact_plan":
        return "Return an artifact-plan patch that changes only sanctioned projection fields before rerender."
    return ""


def _rejected_interpretation(finding: GreenfieldReviewFinding, *, target_layer: str) -> str:
    if target_layer not in {"semantic_model", "artifact_plan"}:
        return ""
    return normalize_string(finding.message)


__all__ = [
    "GreenfieldPatchOperation",
    "GreenfieldPatchSet",
    "PRECONFIRM_PATCHSET_VERSION",
    "patchset_request_from_findings",
]
