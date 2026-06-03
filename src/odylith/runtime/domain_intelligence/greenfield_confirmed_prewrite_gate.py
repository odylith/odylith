"""Prewrite semantic and Tribunal gates for confirmed greenfield completion."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from odylith.runtime.domain_intelligence import greenfield_programs
from odylith.runtime.domain_intelligence.greenfield_component_contract import component_contract_issues
from odylith.runtime.domain_intelligence.greenfield_component_contract_differentiation import component_spec_preflight_issues
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import clean_generated_text as _clean
from odylith.runtime.domain_intelligence.greenfield_semantic_model import build_greenfield_semantic_model
from odylith.runtime.domain_intelligence.greenfield_semantic_model import semantic_model_mapping
from odylith.runtime.domain_intelligence.greenfield_text import text_values
from odylith.runtime.domain_intelligence.greenfield_text import unique_text
from odylith.runtime.domain_intelligence.proposal_tribunal import run_greenfield_tribunal
from odylith.runtime.domain_intelligence.proposal_validation import collect_host_reasoned_proposal_issues
from odylith.runtime.governance import artifact_tribunal


def complete_semantic_model(
    proposal: dict[str, Any],
    *,
    title: str,
    state_object: str,
    first_path: str,
    proof_boundary: str,
) -> bool:
    intent = proposal.get("intent") if isinstance(proposal.get("intent"), Mapping) else {}
    model = semantic_model_mapping(
        build_greenfield_semantic_model(
            title=title,
            state_object=_clean(intent.get("state_object")) or state_object,
            first_path=first_path,
            proof_boundary=proof_boundary,
            components=_dict_rows(proposal.get("components")),
            human_actors=text_values(intent.get("human_actors")),
            internal_systems=text_values(intent.get("internal_systems")),
            external_systems=text_values(intent.get("external_systems")),
            non_goals=text_values(proposal.get("non_goals") or intent.get("non_goals")),
            workstreams=_mapping_rows(proposal.get("backlog")),
        )
    )
    if proposal.get("semantic_model") == model:
        return False
    proposal["semantic_model"] = model
    return True


def preflight_issues(proposal: Mapping[str, Any], *, release_selector: str) -> list[str]:
    issues: list[str] = []
    issues.extend(collect_host_reasoned_proposal_issues(proposal))
    issues.extend(component_contract_issues(proposal))
    issues.extend(component_spec_preflight_issues(proposal))
    selector = greenfield_programs.proposal_release_selector(proposal, release_selector)
    tribunal = run_greenfield_tribunal(proposal, release_selector=selector)
    issues.extend(tribunal.issues)
    issues.extend(_artifact_issues(proposal))
    return list(unique_text(issues))


def _artifact_issues(proposal: Mapping[str, Any]) -> list[str]:
    issues: list[str] = []
    for index, row in enumerate(_mapping_rows(proposal.get("backlog")), start=1):
        decision = artifact_tribunal.run_governed_artifact_tribunal(
            artifact_kind="backlog",
            payload={
                "title": row.get("title", ""),
                "problem": row.get("problem", ""),
                "customer": row.get("customer", ""),
                "opportunity": row.get("opportunity", ""),
                "product_view": row.get("product_view", ""),
                "success_metrics": row.get("success_metrics", ""),
                "risks": [row.get("domain_risk", ""), row.get("security_posture", ""), row.get("risks", "")],
                "validation": row.get("validation", ""),
            },
        )
        issues.extend(f"backlog row {index}: {issue}" for issue in decision.issues)
    for index, row in enumerate(_mapping_rows(proposal.get("components")), start=1):
        decision = artifact_tribunal.run_governed_artifact_tribunal(
            artifact_kind="component",
            payload={
                "component_id": row.get("component_id", ""),
                "label": row.get("label", ""),
                "path": row.get("intended_path", "") or row.get("path", ""),
                "kind": row.get("kind", ""),
                "responsibility": row.get("responsibility", ""),
                "boundary": row.get("boundary", ""),
                "interfaces": row.get("interfaces", ""),
                "dependencies": row.get("dependencies", ""),
                "validation": row.get("validation", ""),
                "risks": row.get("risks", ""),
            },
        )
        issues.extend(f"component row {index}: {issue}" for issue in decision.issues)
    for index, row in enumerate(_mapping_rows(proposal.get("diagrams")), start=1):
        decision = artifact_tribunal.run_governed_artifact_tribunal(
            artifact_kind="atlas_diagram",
            payload={
                "diagram_id": row.get("diagram_id", "") or f"DRAFT-{index:03d}",
                "slug": row.get("slug", ""),
                "title": row.get("title", ""),
                "kind": row.get("kind", ""),
                "owner": row.get("owner", "repo"),
                "summary": row.get("summary", ""),
                "components": row.get("components", "") or row.get("related_components", ""),
                "watch_paths": row.get("watch_paths", ""),
                "related_backlog": row.get("related_backlog", "") or row.get("related_diagrams", ""),
                "related_code": row.get("related_code", ""),
            },
        )
        issues.extend(f"diagram row {index}: {issue}" for issue in decision.issues)
    return issues


def _dict_rows(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [row for row in value if isinstance(row, dict)]


def _mapping_rows(value: Any) -> list[Mapping[str, Any]]:
    if not isinstance(value, list):
        return []
    return [row for row in value if isinstance(row, Mapping)]


__all__ = ["complete_semantic_model", "preflight_issues"]
