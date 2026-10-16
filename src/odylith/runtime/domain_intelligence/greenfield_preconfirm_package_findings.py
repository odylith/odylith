"""Exact package-shape findings for authored Greenfield pre-confirm gates."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from odylith.runtime.common.value_coercion import normalize_string as clean_text
from odylith.runtime.domain_intelligence.greenfield_preconfirm_review import (
    GreenfieldReviewFinding,
    dedupe_review_findings,
    review_finding,
)


def package_artifact_findings(
    package: Any,
    *,
    model_authored: bool = False,
) -> tuple[GreenfieldReviewFinding, ...]:
    """Return structural findings without prose reinterpretation or repair."""

    if not model_authored:
        raise ValueError("Greenfield package findings require a sealed authored projection")
    findings: list[GreenfieldReviewFinding] = []
    if clean_text(getattr(package, "release_selector", "")):
        findings.extend(_release_package_findings(package))
    findings.extend(_memory_projection_findings(package))
    return dedupe_review_findings(findings)


def _release_package_findings(package: Any) -> tuple[GreenfieldReviewFinding, ...]:
    findings: list[GreenfieldReviewFinding] = []
    backlog_result = package.backlog_result if isinstance(getattr(package, "backlog_result", None), Mapping) else {}
    if backlog_result and not package.release_workstream_ids:
        findings.append(_release_package_finding("prewrite release package must resolve first-release workstream ids"))
    release_target = (
        package.release_target_result
        if isinstance(getattr(package, "release_target_result", None), Mapping)
        else {}
    )
    release_assignment = (
        package.release_assignment_result
        if isinstance(getattr(package, "release_assignment_result", None), Mapping)
        else {}
    )
    if not isinstance(release_target.get("release"), Mapping):
        findings.append(_release_package_finding("prewrite release package missing release target preview"))
    elif clean_text(release_target.get("dry_run")).casefold() not in {"true", "1"}:
        findings.append(_release_package_finding("prewrite release target preview must run in dry-run mode"))
    if not release_assignment:
        findings.append(_release_package_finding("prewrite release package missing release assignment preview"))
        return tuple(findings)
    if clean_text(release_assignment.get("dry_run")).casefold() not in {"true", "1"}:
        findings.append(_release_package_finding("prewrite release assignment preview must run in dry-run mode"))
    assigned_ids = {
        clean_text(item).upper()
        for item in release_assignment.get("workstream_ids", [])
        if clean_text(item)
    }
    expected_ids = {
        clean_text(item).upper()
        for item in package.release_workstream_ids
        if clean_text(item)
    }
    if expected_ids and not expected_ids.issubset(assigned_ids):
        findings.append(
            _release_package_finding(
                "prewrite release assignment preview did not cover first-release workstream ids"
            )
        )
    target_release = release_target.get("release") if isinstance(release_target.get("release"), Mapping) else {}
    assignment_release = (
        release_assignment.get("release")
        if isinstance(release_assignment.get("release"), Mapping)
        else {}
    )
    if (
        clean_text(target_release.get("release_id"))
        and clean_text(assignment_release.get("release_id"))
        and clean_text(target_release.get("release_id"))
        != clean_text(assignment_release.get("release_id"))
    ):
        findings.append(
            _release_package_finding(
                "prewrite release target preview drifted from release assignment preview"
            )
        )
    return tuple(findings)


def _memory_projection_findings(package: Any) -> tuple[GreenfieldReviewFinding, ...]:
    findings: list[GreenfieldReviewFinding] = []
    accepted_preview = (
        getattr(package, "accepted_project_preview", None)
        if isinstance(getattr(package, "accepted_project_preview", None), Mapping)
        else {}
    )
    compass_preview = (
        getattr(package, "compass_memory_preview", None)
        if isinstance(getattr(package, "compass_memory_preview", None), Mapping)
        else {}
    )
    component_preview = tuple(
        row for row in getattr(package, "component_registry_preview", ()) if isinstance(row, Mapping)
    )
    if accepted_preview:
        created = accepted_preview.get("created") if isinstance(accepted_preview.get("created"), Mapping) else {}
        components = created.get("components") if isinstance(created.get("components"), list) else []
        if len(components) != len(component_preview):
            findings.append(
                _artifact_plan_finding(
                    message="accepted-project memory preview component count drifted from Registry prewrite output",
                    surface="accepted_project",
                    target_path="prewrite_package.accepted_project",
                    projection_id="accepted_project",
                    owner="accepted_project_memory",
                )
            )
    if compass_preview:
        components = compass_preview.get("components") if isinstance(compass_preview.get("components"), list) else []
        if len(components) != len(component_preview):
            findings.append(
                _artifact_plan_finding(
                    message="Compass memory event preview components drifted from Registry prewrite output",
                    surface="compass",
                    target_path="prewrite_package.compass",
                    projection_id="compass",
                    owner="compass_memory",
                )
            )
    return tuple(findings)


def _release_package_finding(message: str) -> GreenfieldReviewFinding:
    return review_finding(
        code="release_package_drift",
        surface="release",
        target_path="prewrite_package.release",
        projection_id="release",
        semantic_node_id="ArtifactPlanIR.release",
        severity="high",
        repairability="unrepairable",
        owner="release_planner",
        source="package_artifact_gate",
        message=message,
    )


def _artifact_plan_finding(
    *,
    message: str,
    surface: str,
    target_path: str,
    projection_id: str,
    owner: str,
) -> GreenfieldReviewFinding:
    return review_finding(
        code="artifact_shape_drift",
        surface=surface,
        target_path=target_path,
        projection_id=projection_id,
        semantic_node_id="ArtifactPlanIR",
        severity="high",
        repairability="unrepairable",
        owner=owner,
        source="package_artifact_gate",
        message=message,
    )
