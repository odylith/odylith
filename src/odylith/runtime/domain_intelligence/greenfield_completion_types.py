"""Shared greenfield completion package data types."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict
from dataclasses import dataclass
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_post_confirm_review import GreenfieldReviewFinding
from odylith.runtime.domain_intelligence.greenfield_post_confirm_review import review_report_from_findings


@dataclass(frozen=True)
class GreenfieldCompletionReport:
    """Deterministic result for the in-memory post-confirm package."""

    status: str
    version: str
    semantic_model: bool
    artifact_counts: dict[str, int]
    tribunal_status: str
    issues: tuple[str, ...]
    findings: tuple[GreenfieldReviewFinding, ...] = ()

    @property
    def passed(self) -> bool:
        return self.status == "passed"

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["review_report"] = review_report_from_findings(self.findings).to_dict()
        return payload


@dataclass(frozen=True)
class GreenfieldCompletionPackage:
    """In-memory pre-confirm package that must pass before governed writes."""

    proposal: Mapping[str, Any]
    release_selector: str = ""
    rendered_component_specs: Mapping[str, str] | None = None
    rendered_atlas_sources: Mapping[str, str] | None = None
    atlas_review_date: str = ""
    atlas_diagram_ids: tuple[str, ...] = ()
    atlas_catalog_rows: tuple[Mapping[str, Any], ...] = ()
    component_registry_preview: tuple[Mapping[str, Any], ...] = ()
    project_brief_preview: Mapping[str, Any] | None = None
    project_brief_record_text: str = ""
    tribunal_preview: Mapping[str, Any] | None = None
    accepted_project_preview: Mapping[str, Any] | None = None
    project_dashboard_preview: Mapping[str, Any] | None = None
    compass_memory_preview: Mapping[str, Any] | None = None
    next_steps_preview: Mapping[str, Any] | None = None
    backlog_result: Mapping[str, Any] | None = None
    program_result: Mapping[str, Any] | None = None
    traceability_plan: Any = None
    baseline_writes: Mapping[str, str] | None = None
    brand_asset_writes: Mapping[str, Mapping[str, str]] | None = None
    prewrite_safety_preview: Mapping[str, Any] | None = None
    release_target_result: Mapping[str, Any] | None = None
    release_assignment_result: Mapping[str, Any] | None = None
    release_workstream_ids: tuple[str, ...] = ()


__all__ = ["GreenfieldCompletionPackage", "GreenfieldCompletionReport"]
