"""Typed finding collectors for greenfield post-confirm review gates."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

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
        _extend_review_findings(
            findings,
            operator_component_spec_issues(spec_issues),
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

    return dedupe_review_findings(
        [
            *(_package_issue_finding(issue) for issue in package_issues if clean_text(issue)),
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
