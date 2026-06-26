"""Typed finding collectors for greenfield post-confirm review gates."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from odylith.runtime.artifact_quality.generated_copy_quality import (
    generated_public_copy_findings,
)
from odylith.runtime.artifact_quality.greenfield_quality_lenses import build_greenfield_quality_lens_report
from odylith.runtime.domain_intelligence.greenfield_component_contract import (
    component_contract_issues,
    rendered_component_spec_quality_issues,
)
from odylith.runtime.domain_intelligence.greenfield_component_contract_differentiation import (
    component_spec_preflight_issues,
)
from odylith.runtime.domain_intelligence.greenfield_component_contract_targets import (
    operator_component_spec_issues,
)
from odylith.runtime.domain_intelligence.greenfield_post_confirm_review import (
    GreenfieldReviewFinding,
)
from odylith.runtime.domain_intelligence.greenfield_post_confirm_review import (
    dedupe_review_findings,
)
from odylith.runtime.domain_intelligence.greenfield_post_confirm_review import (
    review_findings_from_messages,
)
from odylith.runtime.domain_intelligence.greenfield_post_confirm_review import (
    review_finding,
)
from odylith.runtime.domain_intelligence.greenfield_post_confirm_semantic_alignment import (
    rendered_spec_alignment_issues as _rendered_spec_alignment_issues,
)
from odylith.runtime.domain_intelligence.greenfield_post_confirm_semantic_alignment import (
    semantic_component_alignment_issues as _semantic_component_alignment_issues,
)
from odylith.runtime.domain_intelligence.greenfield_post_confirm_semantic_alignment import (
    semantic_diagram_alignment_issues as _semantic_diagram_alignment_issues,
)
from odylith.runtime.domain_intelligence.greenfield_post_confirm_semantic_alignment import (
    semantic_model_shape_issues as _semantic_model_shape_issues,
)
from odylith.runtime.domain_intelligence.greenfield_post_confirm_semantic_alignment import (
    semantic_workstream_alignment_issues as _semantic_workstream_alignment_issues,
)
from odylith.runtime.domain_intelligence.greenfield_post_confirm_semantic_drift import (
    contrastive_domain_drift_issues as _contrastive_domain_drift_issues,
)
from odylith.runtime.domain_intelligence.greenfield_post_confirm_semantic_drift import (
    semantic_repetition_issues as _semantic_repetition_issues,
)
from odylith.runtime.domain_intelligence.greenfield_quality_gate import greenfield_quality_issues
from odylith.runtime.domain_intelligence.greenfield_quality_lens_repair import quality_lens_repair_owner
from odylith.runtime.domain_intelligence.greenfield_semantic_compiler import (
    semantic_compiler_issues as _semantic_compiler_issues,
)
from odylith.runtime.domain_intelligence.greenfield_text import clean_text


def completion_review_findings(
    proposal: Mapping[str, Any],
    *,
    rendered_specs: Mapping[str, str],
    tribunal_issues: Sequence[str],
) -> tuple[GreenfieldReviewFinding, ...]:
    """Collect typed findings from proposal-level post-confirm validators."""

    findings: list[GreenfieldReviewFinding] = []
    findings.extend(_post_confirm_contract_findings(proposal, rendered_specs=rendered_specs))
    _extend_review_findings(
        findings,
        greenfield_quality_issues(proposal),
        code="proposal_quality_gate",
        surface="proposal",
        target_path="proposal",
        severity="high",
        repairability="semantic_patch",
        owner="greenfield_quality_gate",
        source="greenfield_quality_gate",
    )
    _extend_review_findings(
        findings,
        component_contract_issues(proposal),
        code="component_contract_quality",
        surface="registry",
        target_path="proposal.components",
        severity="medium",
        repairability="plan_patch",
        owner="registry_renderer",
        source="component_contract_gate",
    )
    _extend_review_findings(
        findings,
        component_spec_preflight_issues(proposal),
        code="component_contract_quality",
        surface="registry",
        target_path="proposal.components",
        severity="medium",
        repairability="plan_patch",
        owner="registry_renderer",
        source="component_spec_preflight",
    )
    if rendered_specs:
        spec_issues = rendered_component_spec_quality_issues(rendered_specs, project_title=_project_title(proposal))
        operator_spec_issues = operator_component_spec_issues(spec_issues)
        safe_spec_issues = [
            issue for issue in operator_spec_issues if _safe_mechanical_copy_issue(clean_text(issue).casefold())
        ]
        contract_spec_issues = [issue for issue in operator_spec_issues if issue not in safe_spec_issues]
        _extend_review_findings(
            findings,
            safe_spec_issues,
            code="generated_copy_quality",
            surface="registry",
            target_path="rendered_component_specs",
            projection_id="registry",
            semantic_node_id="ArtifactDraftSet.registry",
            severity="medium",
            repairability="safe_package_repair",
            owner="artifact_draft_cleaner",
            source="rendered_component_spec_quality",
        )
        _extend_review_findings(
            findings,
            contract_spec_issues,
            code="component_contract_quality",
            surface="registry",
            target_path="rendered_component_specs",
            projection_id="registry",
            severity="medium",
            repairability="plan_patch",
            owner="registry_renderer",
            source="rendered_component_spec_quality",
        )
    _extend_review_findings(
        findings,
        tribunal_issues,
        code="validation_gate_failure",
        surface="tribunal",
        target_path="proposal",
        severity="critical",
        repairability="unrepairable",
        owner="proposal_tribunal",
        source="proposal_tribunal",
    )
    return dedupe_review_findings(findings)


def package_review_findings(
    package: Any,
    *,
    package_issues: Sequence[str],
) -> tuple[GreenfieldReviewFinding, ...]:
    """Collect typed findings from the prewrite artifact package."""

    copy_findings = _generated_copy_quality_findings(package)
    copy_messages = {finding.message for finding in copy_findings}
    return dedupe_review_findings(
        [
            *(
                _package_issue_finding(issue)
                for issue in package_issues
                if clean_text(issue) and clean_text(issue) not in copy_messages
            ),
            *copy_findings,
            *_quality_lens_findings(package),
        ]
    )


def _project_title(proposal: Mapping[str, Any]) -> str:
    intent = proposal.get("intent") if isinstance(proposal.get("intent"), Mapping) else {}
    return str(intent.get("title", "")).strip()


def _package_issue_finding(message: str) -> GreenfieldReviewFinding:
    route = _package_issue_route(clean_text(message))
    return review_finding(message=message, source="package_artifact_gate", **route)


def _package_issue_route(message: str) -> dict[str, str]:
    text = clean_text(message)
    lowered = text.casefold()
    if _safe_mechanical_copy_issue(lowered):
        route = _surface_route_for_message(lowered)
        return _route(
            "generated_copy_quality",
            route["surface"],
            route["target_path"],
            route["projection_id"],
            "artifact_draft_cleaner",
            repairability="safe_package_repair",
        )
    if lowered.startswith("prewrite radar"):
        return _route("artifact_shape_drift", "radar", "prewrite_package.radar", "radar", "radar_renderer")
    if "atlas" in lowered or "mermaid" in lowered or "diagram" in lowered:
        return _route("atlas_render_quality", "atlas", "prewrite_package.atlas", "atlas", "atlas_renderer")
    if "registry" in lowered or "component authoring" in lowered or "component `" in lowered:
        return _route(
            "component_contract_quality",
            "registry",
            "prewrite_package.registry",
            "registry",
            "registry_renderer",
        )
    if lowered.startswith("project brief"):
        return _route(
            "artifact_shape_drift",
            "project_brief",
            "prewrite_package.project_brief",
            "project_brief",
            "project_brief_renderer",
        )
    if lowered.startswith("tribunal"):
        return _route(
            "validation_gate_failure",
            "tribunal",
            "prewrite_package.tribunal",
            "review_report",
            "proposal_tribunal",
            severity="critical",
            repairability="unrepairable",
        )
    if lowered.startswith("accepted-project"):
        return _route(
            "artifact_shape_drift",
            "accepted_project",
            "prewrite_package.accepted_project",
            "accepted_project",
            "accepted_project_memory",
        )
    if lowered.startswith("compass"):
        return _route(
            "artifact_shape_drift",
            "compass",
            "prewrite_package.compass",
            "compass",
            "compass_memory",
        )
    if "next-steps" in lowered or "next steps" in lowered:
        return _route(
            "artifact_shape_drift",
            "next_steps",
            "prewrite_package.next_steps",
            "next_steps",
            "operator_experience_renderer",
        )
    if "release" in lowered:
        return _route(
            "release_package_drift",
            "release",
            "prewrite_package.release",
            "release",
            "release_planner",
        )
    return _route(
        "artifact_shape_drift",
        "post_confirm_package",
        "prewrite_package",
        "artifact_draft_set",
        "artifact_plan_projector",
    )


def _route(
    code: str,
    surface: str,
    target_path: str,
    projection_id: str,
    owner: str,
    *,
    severity: str = "high",
    repairability: str = "plan_patch",
) -> dict[str, str]:
    return {
        "code": code,
        "surface": surface,
        "target_path": target_path,
        "projection_id": projection_id,
        "semantic_node_id": "ArtifactPlanIR",
        "severity": severity,
        "repairability": repairability,
        "owner": owner,
    }


def _surface_route_for_message(lowered: str) -> dict[str, str]:
    if "radar" in lowered:
        return {"surface": "radar", "target_path": "prewrite_package.radar", "projection_id": "radar"}
    if "registry" in lowered or "component spec" in lowered:
        return {"surface": "registry", "target_path": "prewrite_package.registry", "projection_id": "registry"}
    if "atlas" in lowered or "mermaid" in lowered:
        return {"surface": "atlas", "target_path": "prewrite_package.atlas", "projection_id": "atlas"}
    if "project brief" in lowered:
        return {
            "surface": "project_brief",
            "target_path": "prewrite_package.project_brief",
            "projection_id": "project_brief",
        }
    if "accepted-project" in lowered:
        return {
            "surface": "accepted_project",
            "target_path": "prewrite_package.accepted_project",
            "projection_id": "accepted_project",
        }
    if "compass" in lowered:
        return {"surface": "compass", "target_path": "prewrite_package.compass", "projection_id": "compass"}
    if "next step" in lowered:
        return {"surface": "next_steps", "target_path": "prewrite_package.next_steps", "projection_id": "next_steps"}
    return {
        "surface": "post_confirm_package",
        "target_path": "prewrite_package",
        "projection_id": "artifact_draft_set",
    }


def _safe_mechanical_copy_issue(lowered: str) -> bool:
    """Return true only for local draft-copy defects that do not change semantics."""

    return any(
        token in lowered
        for token in (
            "repeats adjacent word",
            "modal/base-form grammar drift",
            "mixed finite/base action prose",
            "clipped or dangling phrase ending",
            "clipped article phrase ending",
            "malformed ownership verb pair",
            "malformed component responsibility",
        )
    )


def _generated_copy_quality_findings(package: Any) -> tuple[GreenfieldReviewFinding, ...]:
    findings: list[GreenfieldReviewFinding] = []
    for route in _generated_copy_routes(package):
        for copy_finding in generated_public_copy_findings(route["scope"], route["value"]):
            findings.append(
                review_finding(
                    code="generated_copy_quality",
                    surface=route["surface"],
                    target_path=f"{route['target_path']}.{copy_finding.category}",
                    projection_id=route["projection_id"],
                    semantic_node_id=route["semantic_node_id"],
                    severity="medium",
                    repairability=_generated_copy_repairability(copy_finding.category),
                    owner=route["owner"],
                    source="generated_copy_quality",
                    message=copy_finding.message,
                )
            )
    return dedupe_review_findings(findings)


def _generated_copy_routes(package: Any) -> tuple[dict[str, Any], ...]:
    backlog_result = package.backlog_result if isinstance(getattr(package, "backlog_result", None), Mapping) else {}
    return (
        _copy_route(
            scope="prewrite Radar package",
            value=backlog_result.get("idea_files") if isinstance(backlog_result.get("idea_files"), Mapping) else {},
            surface="radar",
            target_path="prewrite_package.radar.idea_files",
            projection_id="radar",
            owner="radar_renderer",
        ),
        _copy_route(
            scope="Radar index `INDEX.md`",
            value=backlog_result.get("backlog_index_text") if isinstance(backlog_result, Mapping) else "",
            surface="radar",
            target_path="prewrite_package.radar.index",
            projection_id="radar",
            owner="radar_renderer",
        ),
        _copy_route(
            scope="prewrite Registry preview",
            value=tuple(
                row for row in getattr(package, "component_registry_preview", ()) if isinstance(row, Mapping)
            ),
            surface="registry",
            target_path="prewrite_package.registry.preview",
            projection_id="registry",
            owner="registry_renderer",
        ),
        _copy_route(
            scope="rendered Registry component specs",
            value=getattr(package, "rendered_component_specs", None) or {},
            surface="registry",
            target_path="prewrite_package.registry.specs",
            projection_id="registry",
            owner="registry_renderer",
        ),
        _copy_route(
            scope="rendered Atlas Mermaid sources",
            value=getattr(package, "rendered_atlas_sources", None) or {},
            surface="atlas",
            target_path="prewrite_package.atlas.sources",
            projection_id="atlas",
            owner="atlas_renderer",
        ),
        _copy_route(
            scope="project brief preview",
            value=getattr(package, "project_brief_preview", None) or {},
            surface="project_brief",
            target_path="prewrite_package.project_brief",
            projection_id="project_brief",
            owner="project_brief_renderer",
        ),
        _copy_route(
            scope="accepted-project memory preview",
            value=getattr(package, "accepted_project_preview", None) or {},
            surface="accepted_project",
            target_path="prewrite_package.accepted_project",
            projection_id="accepted_project",
            owner="accepted_project_memory",
        ),
        _copy_route(
            scope="Compass memory preview",
            value=getattr(package, "compass_memory_preview", None) or {},
            surface="compass",
            target_path="prewrite_package.compass",
            projection_id="compass",
            owner="compass_memory",
        ),
        _copy_route(
            scope="operator next-steps preview",
            value=getattr(package, "next_steps_preview", None) or {},
            surface="next_steps",
            target_path="prewrite_package.next_steps",
            projection_id="next_steps",
            owner="operator_experience_renderer",
        ),
    )


def _copy_route(
    *,
    scope: str,
    value: Any,
    surface: str,
    target_path: str,
    projection_id: str,
    owner: str,
) -> dict[str, Any]:
    return {
        "scope": scope,
        "value": value,
        "surface": surface,
        "target_path": target_path,
        "projection_id": projection_id,
        "semantic_node_id": f"ArtifactDraftSet.{projection_id}",
        "owner": owner,
    }


def _generated_copy_repairability(category: str) -> str:
    safe_categories = {
        "compact_action_inflection",
        "malformed_component_responsibility",
        "mixed_action_inflection",
    }
    return "safe_package_repair" if clean_text(category) in safe_categories else "plan_patch"


def _extend_review_findings(
    findings: list[GreenfieldReviewFinding],
    messages: Sequence[str],
    *,
    code: str,
    surface: str,
    target_path: str = "",
    projection_id: str = "",
    semantic_node_id: str = "",
    severity: str = "medium",
    repairability: str = "proposal_repair",
    owner: str = "post_confirm_engine",
    source: str = "post_confirm",
    lens: str = "",
) -> None:
    findings.extend(
        review_findings_from_messages(
            messages,
            code=code,
            surface=surface,
            target_path=target_path,
            projection_id=projection_id,
            semantic_node_id=semantic_node_id,
            severity=severity,
            repairability=repairability,
            owner=owner,
            source=source,
            lens=lens,
        )
    )


def _post_confirm_contract_findings(
    proposal: Mapping[str, Any],
    *,
    rendered_specs: Mapping[str, str],
) -> tuple[GreenfieldReviewFinding, ...]:
    if int(proposal.get("provider_calls") or 0) != 0:
        return review_findings_from_messages(
            ["post-confirm completion must be provider-free by default"],
            code="provider_call_leak",
            surface="post_confirm",
            target_path="proposal.provider_calls",
            severity="critical",
            repairability="unrepairable",
            owner="post_confirm_engine",
            source="provider_guard",
        )
    semantic = proposal.get("semantic_model")
    if not isinstance(semantic, Mapping):
        return review_findings_from_messages(
            ["post-confirm completion requires GreenfieldSemanticModel before rendering governed artifacts"],
            code="missing_semantic_model",
            surface="semantic_model",
            target_path="proposal.semantic_model",
            semantic_node_id="SemanticModelIR",
            severity="critical",
            repairability="semantic_patch",
            owner="semantic_model_compiler",
            source="semantic_model_shape",
        )
    findings: list[GreenfieldReviewFinding] = []
    _extend_semantic_findings(findings, proposal=proposal, semantic=semantic)
    if rendered_specs:
        _extend_review_findings(
            findings,
            _rendered_spec_alignment_issues(proposal, rendered_specs),
            code="component_contract_quality",
            surface="registry",
            target_path="rendered_component_specs",
            projection_id="registry",
            semantic_node_id="ArtifactPlanIR.registry",
            severity="medium",
            repairability="plan_patch",
            owner="registry_renderer",
            source="rendered_spec_alignment",
        )
    return dedupe_review_findings(findings)


def _extend_semantic_findings(
    findings: list[GreenfieldReviewFinding],
    *,
    proposal: Mapping[str, Any],
    semantic: Mapping[str, Any],
) -> None:
    _extend_review_findings(
        findings,
        _semantic_model_shape_issues(semantic),
        code="semantic_alignment",
        surface="semantic_model",
        target_path="proposal.semantic_model",
        semantic_node_id="SemanticModelIR",
        severity="high",
        repairability="semantic_patch",
        owner="semantic_model_compiler",
        source="semantic_model_shape",
    )
    _extend_review_findings(
        findings,
        _semantic_component_alignment_issues(proposal, semantic),
        code="semantic_alignment",
        surface="registry",
        target_path="proposal.components",
        semantic_node_id="SemanticModelIR.component_contracts",
        severity="high",
        repairability="semantic_patch",
        owner="semantic_model_compiler",
        source="semantic_component_alignment",
    )
    _extend_review_findings(
        findings,
        _semantic_workstream_alignment_issues(proposal, semantic),
        code="semantic_alignment",
        surface="radar",
        target_path="proposal.backlog",
        semantic_node_id="SemanticModelIR.workstream_contracts",
        severity="high",
        repairability="semantic_patch",
        owner="semantic_model_compiler",
        source="semantic_workstream_alignment",
    )
    _extend_review_findings(
        findings,
        _semantic_diagram_alignment_issues(proposal, semantic),
        code="semantic_alignment",
        surface="atlas",
        target_path="proposal.diagrams",
        semantic_node_id="SemanticModelIR.diagram_event_graph",
        severity="high",
        repairability="semantic_patch",
        owner="semantic_model_compiler",
        source="semantic_diagram_alignment",
    )
    _extend_review_findings(
        findings,
        _semantic_compiler_issues(proposal),
        code="semantic_compiler",
        surface="semantic_model",
        target_path="proposal.semantic_model",
        semantic_node_id="SemanticModelIR",
        severity="high",
        repairability="semantic_patch",
        owner="semantic_model_compiler",
        source="semantic_compiler",
    )
    _extend_review_findings(
        findings,
        _contrastive_domain_drift_issues(proposal, semantic),
        code="semantic_drift",
        surface="artifact_plan",
        target_path="proposal",
        semantic_node_id="SemanticModelIR",
        severity="high",
        repairability="semantic_patch",
        owner="semantic_model_compiler",
        source="semantic_drift",
    )
    _extend_review_findings(
        findings,
        _semantic_repetition_issues(proposal),
        code="semantic_drift",
        surface="artifact_plan",
        target_path="proposal",
        semantic_node_id="ArtifactPlanIR",
        severity="high",
        repairability="plan_patch",
        owner="artifact_plan_projector",
        source="semantic_repetition",
    )


def _quality_lens_findings(package: Any) -> tuple[GreenfieldReviewFinding, ...]:
    report = build_greenfield_quality_lens_report(package)
    lenses = report.get("lenses") if isinstance(report.get("lenses"), Mapping) else {}
    findings: list[GreenfieldReviewFinding] = []
    for lens_name, lens in lenses.items():
        if not isinstance(lens, Mapping):
            continue
        checks = lens.get("checks")
        if not isinstance(checks, list):
            continue
        for check in checks:
            if not isinstance(check, Mapping):
                continue
            if clean_text(check.get("status")).casefold() == "passed":
                continue
            check_name = clean_text(check.get("name"))
            repair_owner = quality_lens_repair_owner(check_name)
            repairability = "plan_patch" if repair_owner == "prewrite_gate" else "semantic_patch"
            findings.extend(
                review_findings_from_messages(
                    [clean_text(check.get("issue")) or f"quality lens {lens_name} failed {check_name}"],
                    code="quality_lens_gap",
                    surface=str(lens_name),
                    target_path=f"quality_lenses.{lens_name}.{check_name}" if check_name else f"quality_lenses.{lens_name}",
                    projection_id="review_report",
                    semantic_node_id="ReviewReport.quality_lenses",
                    severity="high",
                    repairability=repairability,
                    owner="quality_lens_contract",
                    source="quality_lens",
                    lens=str(lens_name),
                )
            )
    return dedupe_review_findings(findings)


__all__ = ["completion_review_findings", "package_review_findings"]
