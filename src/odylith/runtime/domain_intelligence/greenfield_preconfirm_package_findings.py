"""Source-typed package findings for greenfield pre-confirm gates."""

from __future__ import annotations

from collections.abc import Mapping
from collections.abc import Sequence
import re
from typing import Any

from odylith.runtime.analysis_engine.types import slugify
from odylith.runtime.artifact_quality.generated_copy_quality import generated_public_copy_findings
from odylith.runtime.artifact_quality.greenfield_rendered_artifacts import ArtifactQualityUnit
from odylith.runtime.artifact_quality.greenfield_package_quality import greenfield_rendered_package_quality_findings
from odylith.runtime.domain_intelligence.greenfield_artifact_plan import artifact_draft_exact_repair_path
from odylith.runtime.domain_intelligence.greenfield_atlas_semantic_coverage import atlas_first_path_contract_coverage_text
from odylith.runtime.domain_intelligence.greenfield_first_path_coverage import first_path_contract_has_coverage
from odylith.runtime.domain_intelligence.greenfield_preconfirm_review import GreenfieldReviewFinding
from odylith.runtime.domain_intelligence.greenfield_preconfirm_review import dedupe_review_findings
from odylith.runtime.domain_intelligence.greenfield_preconfirm_review import review_finding
from odylith.runtime.domain_intelligence.greenfield_preconfirm_semantic_drift import (
    semantic_overlap_ratio as _semantic_overlap_ratio,
)
from odylith.runtime.domain_intelligence.greenfield_preconfirm_rescue_probe import (
    rescue_probe_findings,
)
from odylith.runtime.domain_intelligence.greenfield_preconfirm_structured_rescue_proof import (
    structured_rescue_proof_findings,
)
from odylith.runtime.domain_intelligence.greenfield_text import clean_text
from odylith.runtime.domain_intelligence.greenfield_text import text_values
from odylith.runtime.domain_intelligence.greenfield_structural_copy import structural_copy_value


_RENDERED_COMPONENT_SPEC_PREFIX = "prewrite_package.rendered_component_specs::"
_COMPONENT_CONTRACT_OUTPUT_FIELD = "component_contract.produced_outputs"


def package_artifact_findings(package: Any) -> tuple[GreenfieldReviewFinding, ...]:
    """Return package findings whose route is known by the source check."""

    findings: list[GreenfieldReviewFinding] = []
    backlog_result = package.backlog_result if isinstance(getattr(package, "backlog_result", None), Mapping) else {}
    atlas_sources = (
        package.rendered_atlas_sources
        if isinstance(getattr(package, "rendered_atlas_sources", None), Mapping)
        else {}
    )
    project_brief_preview = (
        package.project_brief_preview
        if isinstance(getattr(package, "project_brief_preview", None), Mapping)
        else {}
    )
    if backlog_result:
        idea_files = backlog_result.get("idea_files") if isinstance(backlog_result.get("idea_files"), Mapping) else {}
        findings.extend(_radar_preview_semantic_findings(package, idea_files=idea_files))
    if atlas_sources:
        findings.extend(_atlas_preview_semantic_findings(package, atlas_sources))
    if project_brief_preview:
        findings.extend(_project_brief_preview_semantic_findings(package, project_brief_preview))
    if clean_text(getattr(package, "release_selector", "")):
        findings.extend(_release_package_findings(package))
    findings.extend(_package_repetition_findings(package))
    findings.extend(_mechanical_package_quality_findings(package))
    findings.extend(_plan_package_quality_findings(package))
    findings.extend(_registry_package_findings(package))
    findings.extend(_memory_projection_findings(package))
    findings.extend(rescue_probe_findings(package))
    findings.extend(structured_rescue_proof_findings(package))
    return dedupe_review_findings(findings)


def _project_brief_preview_semantic_findings(
    package: Any,
    project_brief_preview: Mapping[str, Any],
) -> tuple[GreenfieldReviewFinding, ...]:
    if not _confirmed_greenfield_package(package):
        return ()
    semantic = _semantic_model(package)
    first_path = semantic.get("first_path_contract") if isinstance(semantic.get("first_path_contract"), Mapping) else {}
    proof_boundary = (
        semantic.get("domain_ontology", {}).get("proof_boundary")
        if isinstance(semantic.get("domain_ontology"), Mapping)
        else ""
    )
    preview_text = clean_text(" ".join(value for item in text_values(project_brief_preview) for value in text_values(item)))
    findings: list[GreenfieldReviewFinding] = []
    first_path_capability = clean_text(first_path.get("capability"))
    first_path_raw_path = clean_text(first_path.get("raw_path"))
    if (
        first_path_capability
        and _semantic_overlap_ratio(first_path_capability, preview_text) < 0.16
        and (not first_path_raw_path or _semantic_overlap_ratio(first_path_raw_path, preview_text) < 0.16)
    ):
        findings.append(
            _semantic_package_finding(
                message="project brief preview missing semantic coverage for FirstPathContract",
                surface="project_brief",
                projection_id="project_brief",
                semantic_node_id="SemanticModelIR.first_path_contract",
                target_path="semantic_model.first_path_contract",
            )
        )
    if clean_text(proof_boundary) and _semantic_overlap_ratio(clean_text(proof_boundary), preview_text) < 0.12:
        findings.append(
            _semantic_package_finding(
                message="project brief preview missing semantic coverage for proof boundary",
                surface="project_brief",
                projection_id="project_brief",
                semantic_node_id="SemanticModelIR.domain_ontology.proof_boundary",
                target_path="semantic_model.domain_ontology.proof_boundary",
            )
        )
    return tuple(findings)


def _radar_preview_semantic_findings(
    package: Any,
    *,
    idea_files: Mapping[Any, Any],
) -> tuple[GreenfieldReviewFinding, ...]:
    if not _confirmed_greenfield_package(package):
        return ()
    text = clean_text(" ".join(str(value or "") for value in idea_files.values()))
    if not text:
        return ()
    semantic = _semantic_model(package)
    first_path = semantic.get("first_path_contract") if isinstance(semantic.get("first_path_contract"), Mapping) else {}
    ontology = semantic.get("domain_ontology") if isinstance(semantic.get("domain_ontology"), Mapping) else {}
    findings: list[GreenfieldReviewFinding] = []
    if not first_path_contract_has_coverage(
        first_path,
        text,
        overlap_ratio=_semantic_overlap_ratio,
        threshold=0.18,
    ):
        findings.append(
            _semantic_package_finding(
                message="prewrite Radar package missing semantic coverage for first path",
                surface="radar",
                projection_id="radar",
                semantic_node_id="SemanticModelIR.first_path_contract",
                target_path="semantic_model.first_path_contract",
            )
        )
    proof_boundary = clean_text(ontology.get("proof_boundary"))
    if proof_boundary and _semantic_overlap_ratio(proof_boundary, text) < 0.18:
        findings.append(
            _semantic_package_finding(
                message="prewrite Radar package missing semantic coverage for proof boundary",
                surface="radar",
                projection_id="radar",
                semantic_node_id="SemanticModelIR.domain_ontology.proof_boundary",
                target_path="semantic_model.domain_ontology.proof_boundary",
            )
        )
    return tuple(findings)


def _atlas_preview_semantic_findings(
    package: Any,
    atlas_sources: Mapping[str, str],
) -> tuple[GreenfieldReviewFinding, ...]:
    if not _confirmed_greenfield_package(package):
        return ()
    text = clean_text(" ".join(str(value or "") for value in atlas_sources.values()))
    if not text:
        return ()
    semantic = _semantic_model(package)
    graph = semantic.get("diagram_event_graph") if isinstance(semantic.get("diagram_event_graph"), Mapping) else {}
    findings: list[GreenfieldReviewFinding] = []
    first_path_text = atlas_first_path_contract_coverage_text(semantic)
    if first_path_text and _semantic_overlap_ratio(first_path_text, text) < 0.16:
        findings.append(
            _semantic_package_finding(
                message="prewrite Atlas package missing semantic coverage for FirstPathContract",
                surface="atlas",
                projection_id="atlas",
                semantic_node_id="SemanticModelIR.first_path_contract",
                target_path="semantic_model.first_path_contract",
            )
        )
    if "proof checkpoint" not in text.casefold():
        findings.append(
            review_finding(
                code="atlas_render_quality",
                surface="atlas",
                target_path="prewrite_package.atlas",
                projection_id="atlas",
                semantic_node_id="ArtifactPlanIR.atlas",
                severity="high",
                repairability="plan_patch",
                owner="atlas_renderer",
                source="package_artifact_gate",
                message="prewrite Atlas package missing proof checkpoint diagram label",
            )
        )
    checkpoint = _atlas_checkpoint_search_text(clean_text(graph.get("proof_checkpoint")))
    if checkpoint and _semantic_overlap_ratio(checkpoint, text) < 0.12:
        findings.append(
            _semantic_package_finding(
                message="prewrite Atlas package missing semantic coverage for DiagramEventGraph proof checkpoint",
                surface="atlas",
                projection_id="atlas",
                semantic_node_id="SemanticModelIR.diagram_event_graph.proof_checkpoint",
                target_path="semantic_model.diagram_event_graph.proof_checkpoint",
            )
        )
    return tuple(findings)


def _release_package_findings(package: Any) -> tuple[GreenfieldReviewFinding, ...]:
    findings: list[GreenfieldReviewFinding] = []
    backlog_result = package.backlog_result if isinstance(getattr(package, "backlog_result", None), Mapping) else {}
    if clean_text(getattr(package, "release_selector", "")) and backlog_result and not package.release_workstream_ids:
        findings.append(_release_package_finding("prewrite release package must resolve first-release workstream ids"))
    if not clean_text(getattr(package, "release_selector", "")):
        return tuple(findings)
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
    else:
        if clean_text(release_assignment.get("dry_run")).casefold() not in {"true", "1"}:
            findings.append(_release_package_finding("prewrite release assignment preview must run in dry-run mode"))
        assigned_ids = {
            clean_text(item).upper()
            for item in release_assignment.get("workstream_ids", [])
            if clean_text(item)
        }
        expected_ids = {clean_text(item).upper() for item in package.release_workstream_ids if clean_text(item)}
        if expected_ids and not expected_ids.issubset(assigned_ids):
            findings.append(
                _release_package_finding("prewrite release assignment preview did not cover first-release workstream ids")
            )
        target_release = release_target.get("release") if isinstance(release_target.get("release"), Mapping) else {}
        assignment_release = release_assignment.get("release") if isinstance(release_assignment.get("release"), Mapping) else {}
        if clean_text(target_release.get("release_id")) and clean_text(assignment_release.get("release_id")):
            if clean_text(target_release.get("release_id")) != clean_text(assignment_release.get("release_id")):
                findings.append(
                    _release_package_finding("prewrite release target preview drifted from release assignment preview")
                )
    return tuple(findings)


def _mechanical_package_quality_findings(package: Any) -> tuple[GreenfieldReviewFinding, ...]:
    findings: list[GreenfieldReviewFinding] = []
    for unit in _artifact_draft_public_copy_units(package):
        for copy_finding in generated_public_copy_findings(unit.surface, unit):
            if not _mechanical_package_quality_issue(copy_finding.message):
                continue
            findings.append(
                review_finding(
                    code="generated_copy_quality",
                    surface=unit.projection_id,
                    target_path=unit.source_path,
                    projection_id=unit.projection_id,
                    semantic_node_id=unit.semantic_node_id or f"ArtifactPlanIR.{unit.projection_id}",
                    severity="medium",
                    repairability="plan_patch",
                    owner=_plan_package_quality_owner(unit.projection_id),
                    source="package_quality",
                    message=copy_finding.message,
                )
            )
    for quality_finding in greenfield_rendered_package_quality_findings(package):
        message = quality_finding.message
        if quality_finding.code == "package_repetition":
            continue
        if not _mechanical_package_quality_issue(message):
            continue
        projection = quality_finding.projection_id
        if projection == "artifact_draft_set":
            continue
        if not artifact_draft_exact_repair_path(quality_finding.target_path):
            continue
        target_path = quality_finding.target_path
        if projection == "registry":
            target_path = _registry_component_contract_target_path(package, quality_finding.target_path)
        findings.append(
            review_finding(
                code="generated_copy_quality",
                surface=projection,
                target_path=target_path,
                projection_id=projection,
                semantic_node_id=f"ArtifactPlanIR.{target_path}"
                if target_path.startswith("components[")
                else f"ArtifactPlanIR.{projection}",
                severity="medium",
                repairability="plan_patch",
                owner=_plan_package_quality_owner(projection),
                source="package_quality",
                message=message,
            )
        )
    return tuple(findings)


def _package_repetition_findings(package: Any) -> tuple[GreenfieldReviewFinding, ...]:
    findings: list[GreenfieldReviewFinding] = []
    for quality_finding in greenfield_rendered_package_quality_findings(package):
        if quality_finding.code != "package_repetition":
            continue
        findings.append(
            review_finding(
                code=quality_finding.code,
                surface=quality_finding.surface or quality_finding.projection_id or "preconfirm_package",
                target_path=quality_finding.target_path,
                projection_id=quality_finding.projection_id,
                semantic_node_id=quality_finding.semantic_node_id,
                severity=quality_finding.severity or "medium",
                repairability=quality_finding.repairability or "unrepairable",
                owner=quality_finding.owner or "typed_package_artifact_gate",
                source=quality_finding.source or "package_repetition_quality",
                message=quality_finding.message,
            )
        )
    return tuple(findings)


def _artifact_draft_public_copy_units(package: Any) -> tuple[ArtifactQualityUnit, ...]:
    units: list[ArtifactQualityUnit] = []
    _append_public_copy_units(
        units,
        getattr(package, "project_brief_preview", None),
        root_path="prewrite_package.project_brief_preview",
        projection_id="project_brief",
        surface="project brief preview",
    )
    _append_public_copy_units(
        units,
        getattr(package, "next_steps_preview", None),
        root_path="prewrite_package.next_steps_preview",
        projection_id="next_steps",
        surface="operator next-steps preview",
    )
    _append_public_copy_units(
        units,
        getattr(package, "accepted_project_preview", None),
        root_path="prewrite_package.accepted_project_preview",
        projection_id="accepted_project",
        surface="accepted-project memory preview",
    )
    _append_public_copy_units(
        units,
        getattr(package, "compass_memory_preview", None),
        root_path="prewrite_package.compass_memory_preview",
        projection_id="compass",
        surface="Compass memory preview",
    )
    _append_public_copy_units(
        units,
        getattr(package, "project_dashboard_preview", None),
        root_path="prewrite_package.project_dashboard_preview",
        projection_id="project_dashboard",
        surface="project dashboard preview",
    )
    return tuple(dict.fromkeys(units))


def _append_public_copy_units(
    units: list[ArtifactQualityUnit],
    value: Any,
    *,
    root_path: str,
    projection_id: str,
    surface: str,
    role: str = "",
) -> None:
    if value is None:
        return
    if isinstance(value, Mapping):
        for key, nested in value.items():
            text_key = str(key)
            _append_public_copy_units(
                units,
                nested,
                root_path=f"{root_path}.{text_key}",
                projection_id=projection_id,
                surface=surface,
                role=text_key,
            )
        return
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for index, nested in enumerate(value):
            _append_public_copy_units(
                units,
                nested,
                root_path=f"{root_path}[{index}]",
                projection_id=projection_id,
                surface=surface,
                role=role,
            )
        return
    text = clean_text(value)
    if not text or structural_copy_value(key=role, value=text):
        return
    units.append(
        ArtifactQualityUnit(
            projection_id=projection_id,
            surface=surface,
            source_path=root_path,
            surface_role=role or "body",
            text_kind=_artifact_draft_text_kind(role),
            text=text,
            semantic_node_id=f"ArtifactDraftSet.{projection_id}",
        )
    )


def _artifact_draft_text_kind(role: str) -> str:
    normalized = clean_text(role).casefold()
    if normalized in {"command", "commands", "verification_commands"}:
        return "command"
    if normalized in {"mermaid", "mermaid_source"}:
        return "mermaid_source"
    if normalized in {"id", "key", "position", "schema_version", "status", "version"}:
        return "metadata"
    return "free_prose"


def _plan_package_quality_findings(package: Any) -> tuple[GreenfieldReviewFinding, ...]:
    findings: list[GreenfieldReviewFinding] = []
    for quality_finding in greenfield_rendered_package_quality_findings(package):
        message = quality_finding.message
        if quality_finding.code == "package_repetition":
            continue
        if _mechanical_package_quality_issue(message):
            continue
        if quality_finding.projection_id == "registry":
            continue
        projection = quality_finding.projection_id
        if projection == "artifact_draft_set":
            continue
        findings.append(
            review_finding(
                code=_plan_package_quality_code(message),
                surface=projection,
                target_path=quality_finding.target_path,
                projection_id=projection,
                semantic_node_id=f"ArtifactPlanIR.{projection}",
                severity="medium",
                repairability="plan_patch",
                owner=_plan_package_quality_owner(projection),
                source="package_quality",
                message=message,
            )
        )
    return tuple(findings)


def _registry_package_findings(package: Any) -> tuple[GreenfieldReviewFinding, ...]:
    findings: list[GreenfieldReviewFinding] = []
    component_preview = tuple(
        row
        for row in getattr(package, "component_registry_preview", ())
        if isinstance(row, Mapping)
    )
    rendered_specs = (
        getattr(package, "rendered_component_specs", None)
        if isinstance(getattr(package, "rendered_component_specs", None), Mapping)
        else {}
    )
    if rendered_specs and not component_preview:
        findings.append(_registry_plan_finding("prewrite Registry package must include component authoring previews"))
    for quality_finding in greenfield_rendered_package_quality_findings(package):
        if quality_finding.code == "package_repetition":
            continue
        if quality_finding.projection_id == "registry" and not _mechanical_package_quality_issue(quality_finding.message):
            findings.append(
                _registry_plan_finding(
                    quality_finding.message,
                    target_path=_registry_component_contract_target_path(package, quality_finding.target_path),
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
        row
        for row in getattr(package, "component_registry_preview", ())
        if isinstance(row, Mapping)
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


def _semantic_package_finding(
    *,
    message: str,
    surface: str,
    projection_id: str,
    semantic_node_id: str,
    target_path: str,
) -> GreenfieldReviewFinding:
    return review_finding(
        code="semantic_alignment",
        surface=surface,
        target_path=target_path,
        projection_id=projection_id,
        semantic_node_id=semantic_node_id,
        severity="high",
        repairability="semantic_patch",
        owner="semantic_model_compiler",
        source="package_artifact_gate",
        message=message,
    )


def _release_package_finding(message: str) -> GreenfieldReviewFinding:
    return review_finding(
        code="release_package_drift",
        surface="release",
        target_path="prewrite_package.release",
        projection_id="release",
        semantic_node_id="ArtifactPlanIR.release",
        severity="high",
        repairability="plan_patch",
        owner="release_planner",
        source="package_artifact_gate",
        message=message,
    )


def _registry_component_contract_target_path(package: Any, target_path: str) -> str:
    spec_name = _rendered_component_spec_name(target_path)
    if not spec_name:
        return "prewrite_package.registry"
    proposal = getattr(package, "proposal", {}) if isinstance(getattr(package, "proposal", {}), Mapping) else {}
    rows = [row for row in proposal.get("components", []) if isinstance(row, Mapping)]
    needle = slugify(spec_name)
    matches = [
        index
        for index, row in enumerate(rows)
        if needle and any(slugify(str(value or "")) == needle for value in _component_row_aliases(row))
    ]
    if len(matches) != 1:
        return "prewrite_package.registry"
    return f"components[{matches[0]}].{_COMPONENT_CONTRACT_OUTPUT_FIELD}"


def _rendered_component_spec_name(target_path: str) -> str:
    path = clean_text(target_path)
    if not path.startswith(_RENDERED_COMPONENT_SPEC_PREFIX):
        return ""
    return clean_text(path[len(_RENDERED_COMPONENT_SPEC_PREFIX) :])


def _component_row_aliases(row: Mapping[str, Any]) -> tuple[Any, ...]:
    return (row.get("component_id"), row.get("id"), row.get("label"), row.get("name"))


def _registry_plan_finding(message: str, *, target_path: str = "prewrite_package.registry") -> GreenfieldReviewFinding:
    source_path = clean_text(target_path) or "prewrite_package.registry"
    return review_finding(
        code="component_contract_quality",
        surface="registry",
        target_path=source_path,
        projection_id="registry",
        semantic_node_id=f"ArtifactPlanIR.{source_path}" if source_path.startswith("components[") else "ArtifactPlanIR.registry",
        severity="medium",
        repairability="plan_patch",
        owner="registry_renderer",
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
        repairability="plan_patch",
        owner=owner,
        source="package_artifact_gate",
        message=message,
    )


def _mechanical_package_quality_issue(message: str) -> bool:
    text = clean_text(message).casefold()
    return any(
        marker in text
        for marker in (
            "repeats adjacent word",
            "leaked adjacent duplicate word prose",
            "clipped or dangling phrase ending",
            "clipped article phrase ending",
            "leaked clipped or dangling public copy",
        )
    )


def _plan_package_quality_code(message: str) -> str:
    text = clean_text(message).casefold()
    if "scope boundary truncates" in text:
        return "artifact_shape_drift"
    return "generated_copy_quality"


def _plan_package_quality_owner(projection: str) -> str:
    return {
        "atlas": "atlas_renderer",
        "next_steps": "operator_experience_renderer",
        "project_brief": "project_brief_renderer",
        "radar": "radar_renderer",
        "release": "release_planner",
    }.get(projection, "artifact_plan_projector")


def _confirmed_greenfield_package(package: Any) -> bool:
    return clean_text(_intent(package).get("reasoning_mode")) == "odylith_confirmed_governed_proposal"


def _intent(package: Any) -> Mapping[str, Any]:
    proposal = getattr(package, "proposal", {}) if isinstance(getattr(package, "proposal", {}), Mapping) else {}
    return proposal.get("intent") if isinstance(proposal.get("intent"), Mapping) else {}


def _semantic_model(package: Any) -> Mapping[str, Any]:
    proposal = getattr(package, "proposal", {}) if isinstance(getattr(package, "proposal", {}), Mapping) else {}
    return proposal.get("semantic_model") if isinstance(proposal.get("semantic_model"), Mapping) else {}


def _atlas_checkpoint_search_text(value: str) -> str:
    text = clean_text(value)
    text = re.sub(r"^accepted\s+first\s+path\s+proof\s*:\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^proven\s+when\s+", "", text, flags=re.IGNORECASE)
    return text


__all__ = ["package_artifact_findings"]
