"""Typed findings for the authored Greenfield pre-confirm review gate."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_confirmed_proposal import (
    sealed_authored_projection,
)
from odylith.runtime.domain_intelligence.greenfield_preconfirm_review import (
    GreenfieldReviewFinding,
    dedupe_review_findings,
    review_finding,
    review_findings_from_messages,
)
from odylith.runtime.domain_intelligence.greenfield_preconfirm_semantic_alignment import (
    rendered_spec_alignment_issues as _rendered_spec_alignment_issues,
)
from odylith.runtime.domain_intelligence.greenfield_preconfirm_semantic_alignment import (
    semantic_component_alignment_issues as _semantic_component_alignment_issues,
)
from odylith.runtime.domain_intelligence.greenfield_preconfirm_semantic_alignment import (
    semantic_diagram_alignment_issues as _semantic_diagram_alignment_issues,
)
from odylith.runtime.domain_intelligence.greenfield_preconfirm_semantic_alignment import (
    semantic_model_shape_issues as _semantic_model_shape_issues,
)
from odylith.runtime.domain_intelligence.greenfield_preconfirm_semantic_alignment import (
    semantic_workstream_alignment_issues as _semantic_workstream_alignment_issues,
)
from odylith.runtime.domain_intelligence.greenfield_text import clean_text


def completion_review_findings(
    proposal: Mapping[str, Any],
    *,
    rendered_specs: Mapping[str, str],
    tribunal_issues: Sequence[str],
    model_authored: bool = False,
) -> tuple[GreenfieldReviewFinding, ...]:
    """Collect proposal-level findings without introducing a second semantic authority."""

    del model_authored
    if not sealed_authored_projection(proposal):
        return review_findings_from_messages(
            ["pre-confirm completion requires a sealed authored projection"],
            code="missing_authored_projection",
            surface="proposal",
            target_path="proposal.projection_origin",
            severity="critical",
            repairability="unrepairable",
            owner="authored_projection_gate",
            source="authored_projection_gate",
        )
    findings = list(_preconfirm_contract_findings(proposal, rendered_specs=rendered_specs))
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
    package_findings: Sequence[GreenfieldReviewFinding] = (),
    model_authored: bool = False,
) -> tuple[GreenfieldReviewFinding, ...]:
    """Collect package findings from exact compiled-artifact checks only."""

    del model_authored
    proposal = package.proposal if isinstance(getattr(package, "proposal", None), Mapping) else {}
    if not sealed_authored_projection(proposal):
        return review_findings_from_messages(
            ["prewrite package requires a sealed authored projection"],
            code="missing_authored_projection",
            surface="preconfirm_package",
            target_path="prewrite_package.proposal.projection_origin",
            severity="critical",
            repairability="unrepairable",
            owner="authored_projection_gate",
            source="authored_projection_gate",
        )
    typed_findings = tuple(
        finding for finding in package_findings if isinstance(finding, GreenfieldReviewFinding)
    )
    typed_messages = {finding.message for finding in typed_findings}
    return dedupe_review_findings(
        [
            *(
                _package_issue_finding(issue)
                for issue in package_issues
                if clean_text(issue) and clean_text(issue) not in typed_messages
            ),
            *typed_findings,
        ]
    )


def _package_issue_finding(message: str) -> GreenfieldReviewFinding:
    text = clean_text(message)
    if text.startswith("compiled surface refresh proof did not pass"):
        return review_finding(
            code="surface_refresh_proof",
            surface="preconfirm_package",
            target_path="prewrite_package.surface_refresh_preview",
            projection_id="registry",
            semantic_node_id="ArtifactDraftSet.registry",
            severity="critical",
            repairability="projection_rerender",
            owner="greenfield_surface_refresh_proof",
            source="surface_refresh_proof",
            message=message,
        )
    return review_finding(
        code="compiled_package_artifact_gate",
        surface="preconfirm_package",
        target_path="prewrite_package",
        projection_id="review_report",
        semantic_node_id="",
        severity="critical",
        repairability="unrepairable",
        owner="typed_package_artifact_gate",
        source="compiled_package_artifact_gate",
        message=message,
    )


def _preconfirm_contract_findings(
    proposal: Mapping[str, Any],
    *,
    rendered_specs: Mapping[str, str],
) -> tuple[GreenfieldReviewFinding, ...]:
    if int(proposal.get("provider_calls") or 0) != 0:
        return review_findings_from_messages(
            ["pre-confirm completion must be provider-free"],
            code="provider_call_leak",
            surface="preconfirm",
            target_path="proposal.provider_calls",
            severity="critical",
            repairability="unrepairable",
            owner="preconfirm_engine",
            source="provider_guard",
        )
    semantic = proposal.get("semantic_model")
    if not isinstance(semantic, Mapping):
        return review_findings_from_messages(
            ["pre-confirm completion requires GreenfieldSemanticModel before rendering governed artifacts"],
            code="missing_semantic_model",
            surface="semantic_model",
            target_path="proposal.semantic_model",
            semantic_node_id="SemanticModelIR",
            severity="critical",
            repairability="unrepairable",
            owner="authored_projection_gate",
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
            target_path="prewrite_package.rendered_component_specs",
            projection_id="registry",
            semantic_node_id="ArtifactPlanIR.registry",
            severity="high",
            repairability="projection_rerender",
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
    checks = (
        (
            _semantic_model_shape_issues(semantic, include_lexical_alignment=False),
            "semantic_model",
            "proposal.semantic_model",
            "SemanticModelIR",
            "semantic_model_shape",
        ),
        (
            _semantic_component_alignment_issues(proposal, semantic),
            "registry",
            "proposal.components",
            "ArtifactPlanIR.registry",
            "semantic_component_alignment",
        ),
        (
            _semantic_workstream_alignment_issues(proposal, semantic),
            "radar",
            "proposal.backlog",
            "ArtifactPlanIR.radar",
            "semantic_workstream_alignment",
        ),
        (
            _semantic_diagram_alignment_issues(proposal, semantic),
            "atlas",
            "proposal.diagrams",
            "ArtifactPlanIR.atlas",
            "semantic_diagram_alignment",
        ),
    )
    for messages, surface, target_path, semantic_node_id, source in checks:
        _extend_review_findings(
            findings,
            messages,
            code="semantic_alignment",
            surface=surface,
            target_path=target_path,
            semantic_node_id=semantic_node_id,
            severity="high",
            repairability="unrepairable",
            owner="authored_projection_gate",
            source=source,
        )


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
    repairability: str = "unrepairable",
    owner: str = "preconfirm_engine",
    source: str = "preconfirm",
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
        )
    )
