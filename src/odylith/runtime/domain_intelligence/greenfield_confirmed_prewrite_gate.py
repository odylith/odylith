"""Prewrite semantic and Tribunal gates for confirmed greenfield completion."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from odylith.runtime.domain_intelligence import greenfield_programs
from odylith.runtime.domain_intelligence.greenfield_authored_semantics import (
    authored_projection_relations,
    authored_source_custody,
)
from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import (
    PRODUCT_INTENT_AUTHORITY_KEY,
)
from odylith.runtime.domain_intelligence.greenfield_rows import mapping_rows
from odylith.runtime.domain_intelligence.greenfield_text import unique_text
from odylith.runtime.domain_intelligence.proposal_tribunal import (
    run_greenfield_tribunal,
)
from odylith.runtime.domain_intelligence.proposal_validation import (
    collect_host_reasoned_proposal_issues,
)
from odylith.runtime.governance import artifact_tribunal


def preflight_issues(proposal: Mapping[str, Any], *, release_selector: str) -> list[str]:
    issues: list[str] = []
    model_authored = bool(authored_projection_relations(proposal))
    source_custody: Mapping[str, Any] | None = None
    if model_authored:
        intent = proposal.get("intent")
        authority = proposal.get(PRODUCT_INTENT_AUTHORITY_KEY)
        if not isinstance(intent, Mapping) or not isinstance(authority, Mapping):
            raise ValueError("model-authored prewrite is missing sealed Product Intent authority")
        source_custody = authored_source_custody(intent=intent, authority=authority)
    else:
        return ["Greenfield prewrite requires sealed model-authored typed intent"]
    issues.extend(collect_host_reasoned_proposal_issues(proposal))
    selector = greenfield_programs.proposal_release_selector(proposal, release_selector)
    tribunal = run_greenfield_tribunal(proposal, release_selector=selector)
    issues.extend(tribunal.issues)
    issues.extend(
        _artifact_issues(
            proposal,
            source_custody=source_custody,
        )
    )
    return list(unique_text(issues))


def _artifact_issues(
    proposal: Mapping[str, Any],
    *,
    source_custody: Mapping[str, Any] | None = None,
) -> list[str]:
    issues: list[str] = []
    for index, row in enumerate(mapping_rows(proposal.get("backlog")), start=1):
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
            source_custody=source_custody,
        )
        issues.extend(f"backlog row {index}: {issue}" for issue in decision.issues)
    for index, row in enumerate(mapping_rows(proposal.get("components")), start=1):
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
            source_custody=source_custody,
        )
        issues.extend(f"component row {index}: {issue}" for issue in decision.issues)
    for index, row in enumerate(mapping_rows(proposal.get("diagrams")), start=1):
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
                "watch_paths": row.get("watch_paths", "") or row.get("intended_paths", ""),
                "related_backlog": row.get("related_backlog", "") or row.get("related_diagrams", ""),
                "related_code": row.get("related_code", ""),
            },
            source_custody=source_custody,
        )
        issues.extend(f"diagram row {index}: {issue}" for issue in decision.issues)
    return issues


__all__ = ["preflight_issues"]
