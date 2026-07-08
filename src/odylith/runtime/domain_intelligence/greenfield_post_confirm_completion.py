"""Post-confirm completion gate for greenfield governed artifacts.

Product Intent Confirmation stays a lightweight no-write interaction. After
confirmation, this gate treats the generated proposal and in-memory rendered
artifacts as one completion package and fails before governed writes begin.
"""

from __future__ import annotations

from collections.abc import Mapping
from collections.abc import Sequence
from dataclasses import asdict
from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any

from odylith.runtime.artifact_quality.generated_copy_quality import generated_public_copy_issues
from odylith.runtime.artifact_quality.greenfield_package_quality import (
    greenfield_rendered_package_quality_issues,
)
from odylith.runtime.domain_intelligence.greenfield_project_brief import PROJECT_BRIEF_SCHEMA_VERSION
from odylith.runtime.domain_intelligence.greenfield_project_brief import project_brief_issues
from odylith.runtime.domain_intelligence.greenfield_atlas_semantic_coverage import (
    atlas_first_path_contract_coverage_text,
)
from odylith.runtime.domain_intelligence.greenfield_first_path_coverage import first_path_contract_has_coverage
from odylith.runtime.domain_intelligence.greenfield_domain_term_index import ordered_terms
from odylith.runtime.domain_intelligence.greenfield_rows import mapping_rows
from odylith.runtime.domain_intelligence.greenfield_rows import mapping_count
from odylith.runtime.domain_intelligence.greenfield_rows import row_count
from odylith.runtime.domain_intelligence.greenfield_post_confirm_semantic_drift import (
    semantic_overlap_ratio as _semantic_overlap_ratio,
)
from odylith.runtime.domain_intelligence.greenfield_post_confirm_findings import (
    completion_review_findings,
)
from odylith.runtime.domain_intelligence.greenfield_post_confirm_findings import (
    package_review_findings,
)
from odylith.runtime.domain_intelligence.greenfield_post_confirm_package_findings import (
    package_artifact_findings,
)
from odylith.runtime.domain_intelligence.greenfield_post_confirm_review import (
    GreenfieldReviewFinding,
)
from odylith.runtime.domain_intelligence.greenfield_post_confirm_review import (
    dedupe_review_findings,
)
from odylith.runtime.domain_intelligence.greenfield_post_confirm_review import (
    review_report_from_findings,
)
from odylith.runtime.domain_intelligence.greenfield_text import clean_text
from odylith.runtime.domain_intelligence.greenfield_text import text_values
from odylith.runtime.domain_intelligence.greenfield_text import unique_text
from odylith.runtime.domain_intelligence.proposal_tribunal import run_greenfield_tribunal


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
    """In-memory post-confirm package that must pass before governed writes."""

    proposal: Mapping[str, Any]
    release_selector: str = ""
    rendered_component_specs: Mapping[str, str] | None = None
    rendered_atlas_sources: Mapping[str, str] | None = None
    atlas_review_date: str = ""
    atlas_diagram_ids: tuple[str, ...] = ()
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
    prewrite_safety_preview: Mapping[str, Any] | None = None
    release_target_result: Mapping[str, Any] | None = None
    release_assignment_result: Mapping[str, Any] | None = None
    release_workstream_ids: tuple[str, ...] = ()


def build_greenfield_completion_report(
    proposal: Mapping[str, Any],
    *,
    release_selector: str = "",
    rendered_component_specs: Mapping[str, str] | None = None,
    tribunal_preview: Mapping[str, Any] | None = None,
) -> GreenfieldCompletionReport:
    """Evaluate the full post-confirm package before any governed write."""

    rendered_specs = dict(rendered_component_specs or {})
    cached_tribunal = _cached_tribunal_result(tribunal_preview)
    if cached_tribunal is None:
        tribunal = run_greenfield_tribunal(proposal, release_selector=release_selector)
        tribunal_status = str(tribunal.status)
        tribunal_issues = [str(issue) for issue in tribunal.issues]
    else:
        tribunal_status, tribunal_issues = cached_tribunal
    findings = list(
        completion_review_findings(
            proposal,
            rendered_specs=rendered_specs,
            tribunal_issues=tribunal_issues,
        )
    )
    issues = unique_text([finding.message for finding in findings])
    issues = unique_text(issues)
    return GreenfieldCompletionReport(
        status="failed" if issues or findings else "passed",
        version="greenfield-post-confirm-completion-v1",
        semantic_model=isinstance(proposal.get("semantic_model"), Mapping),
        artifact_counts={
            "workstreams": row_count(proposal.get("backlog")),
            "components": row_count(proposal.get("components")),
            "diagrams": row_count(proposal.get("diagrams")),
            "rendered_component_specs": len(rendered_specs),
        },
        tribunal_status=tribunal_status,
        issues=tuple(issues),
        findings=tuple(findings),
    )


def build_greenfield_package_report(package: GreenfieldCompletionPackage) -> GreenfieldCompletionReport:
    """Evaluate the named in-memory package used by confirmed greenfield writes."""

    report = build_greenfield_completion_report(
        package.proposal,
        release_selector=package.release_selector,
        rendered_component_specs=package.rendered_component_specs,
        tribunal_preview=package.tribunal_preview,
    )
    package_issues = _package_artifact_issues(package)
    package_findings = package_review_findings(
        package,
        package_issues=package_issues,
        package_findings=package_artifact_findings(package),
    )
    findings = dedupe_review_findings([*report.findings, *package_findings])
    issues = unique_text([*report.issues, *(finding.message for finding in package_findings)])
    status = "failed" if issues or findings else "passed"
    return GreenfieldCompletionReport(
        status=status,
        version=report.version,
        semantic_model=report.semantic_model,
        artifact_counts={
            **report.artifact_counts,
            "rendered_workstream_files": mapping_count((package.backlog_result or {}).get("idea_files")),
            "rendered_atlas_sources": mapping_count(package.rendered_atlas_sources),
            "component_registry_previews": len(package.component_registry_preview),
            "project_brief_previews": 1 if isinstance(package.project_brief_preview, Mapping) else 0,
            "tribunal_previews": 1 if isinstance(package.tribunal_preview, Mapping) else 0,
            "accepted_project_previews": 1 if isinstance(package.accepted_project_preview, Mapping) else 0,
            "compass_memory_previews": 1 if isinstance(package.compass_memory_preview, Mapping) else 0,
            "next_steps_previews": 1 if isinstance(package.next_steps_preview, Mapping) else 0,
            "release_assignment_previews": 1 if isinstance(package.release_assignment_result, Mapping) else 0,
            "release_workstream_ids": len(package.release_workstream_ids),
        },
        tribunal_status=report.tribunal_status,
        issues=tuple(issues),
        findings=findings,
    )


def raise_for_failed_greenfield_completion(report: GreenfieldCompletionReport) -> None:
    """Fail with an operator-safe post-confirm completion report."""

    if report.passed:
        return
    raise ValueError(_format_completion_issue_report(report))


def assert_greenfield_completion_ready(
    proposal: Mapping[str, Any],
    *,
    release_selector: str = "",
    rendered_component_specs: Mapping[str, str] | None = None,
) -> GreenfieldCompletionReport:
    """Build and enforce the post-confirm completion report."""

    report = build_greenfield_completion_report(
        proposal,
        release_selector=release_selector,
        rendered_component_specs=rendered_component_specs,
    )
    raise_for_failed_greenfield_completion(report)
    return report


def assert_greenfield_package_ready(package: GreenfieldCompletionPackage) -> GreenfieldCompletionReport:
    """Enforce the full post-confirm package before write application continues."""

    report = build_greenfield_package_report(package)
    raise_for_failed_greenfield_completion(report)
    return report


def _cached_tribunal_result(preview: Mapping[str, Any] | None) -> tuple[str, list[str]] | None:
    """Return a same-package Tribunal result when it was already computed."""

    if not isinstance(preview, Mapping):
        return None
    if str(preview.get("version", "")).strip() != "greenfield-validation-gate-v1":
        return None
    status = str(preview.get("status", "")).strip()
    raw_issues = preview.get("issues")
    issues = [str(issue).strip() for issue in raw_issues if str(issue).strip()] if isinstance(raw_issues, list) else []
    if status and status != "passed" and not issues:
        issues.append(f"greenfield Tribunal returned {status}")
    return status or "unknown", issues


def _package_artifact_issues(package: GreenfieldCompletionPackage) -> list[str]:
    issues: list[str] = []
    backlog_result = package.backlog_result if isinstance(package.backlog_result, Mapping) else {}
    program_result = package.program_result if isinstance(package.program_result, Mapping) else {}
    atlas_sources = package.rendered_atlas_sources if isinstance(package.rendered_atlas_sources, Mapping) else {}
    component_preview = [row for row in package.component_registry_preview if isinstance(row, Mapping)]
    project_brief_preview = package.project_brief_preview if isinstance(package.project_brief_preview, Mapping) else {}
    tribunal_preview = package.tribunal_preview if isinstance(package.tribunal_preview, Mapping) else {}
    accepted_preview = package.accepted_project_preview if isinstance(package.accepted_project_preview, Mapping) else {}
    project_dashboard_preview = package.project_dashboard_preview if isinstance(package.project_dashboard_preview, Mapping) else {}
    compass_preview = package.compass_memory_preview if isinstance(package.compass_memory_preview, Mapping) else {}
    next_steps_preview = package.next_steps_preview if isinstance(package.next_steps_preview, Mapping) else {}
    if backlog_result:
        created = mapping_rows(backlog_result.get("created"))
        idea_files = backlog_result.get("idea_files") if isinstance(backlog_result.get("idea_files"), Mapping) else {}
        proposal_titles = {
            clean_text(row.get("title"))
            for row in mapping_rows(package.proposal.get("backlog"))
            if clean_text(row.get("title"))
        }
        created_titles = {clean_text(row.get("title")) for row in created if clean_text(row.get("title"))}
        if proposal_titles != created_titles:
            issues.append("prewrite Radar package drifted from WorkstreamContracts")
        if len(idea_files) != len(created):
            issues.append("prewrite Radar package must render one workstream file per created workstream")
        if not clean_text(backlog_result.get("backlog_index_text")):
            issues.append("prewrite Radar package missing rendered backlog index text")
        issues.extend(generated_public_copy_issues("prewrite Radar package", idea_files))
        validation_gate = backlog_result.get("validation_gate") if isinstance(backlog_result.get("validation_gate"), Mapping) else {}
        if clean_text(validation_gate.get("status")) != "passed":
            issues.append("prewrite Radar package validation gate did not pass")
        issues.extend(_radar_preview_semantic_issues(package, idea_files=idea_files))
    elif package.rendered_component_specs:
        issues.append("prewrite package with Registry specs must include Radar workstream render output")
    if backlog_result and not atlas_sources:
        issues.append("prewrite package must include rendered Atlas Mermaid sources")
    if atlas_sources:
        if len(package.atlas_diagram_ids) != len(atlas_sources):
            issues.append("prewrite Atlas package must include one compiled diagram id per Mermaid source")
        for diagram_id in package.atlas_diagram_ids:
            if not re.fullmatch(r"D-\d{3,}", clean_text(diagram_id)):
                issues.append("prewrite Atlas package contains an invalid compiled diagram id")
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", clean_text(package.atlas_review_date)):
            issues.append("prewrite Atlas package must include a compiled review date")
        diagram_rows = mapping_rows(package.proposal.get("diagrams"))
        if len(atlas_sources) != len(diagram_rows):
            issues.append("prewrite Atlas package must render one Mermaid source per DiagramEventGraph diagram")
        for raw_path, source in atlas_sources.items():
            path = clean_text(raw_path)
            text = str(source or "").strip()
            if not path.endswith(".mmd"):
                issues.append("prewrite Atlas package contains a non-Mermaid source path")
                continue
            if not text:
                issues.append("prewrite Atlas package contains an empty Mermaid source")
                continue
            if not _has_mermaid_declaration(text):
                issues.append("prewrite Atlas package contains Mermaid source without a diagram declaration")
        issues.extend(_atlas_preview_semantic_issues(package, atlas_sources))
    if package.rendered_component_specs and not component_preview:
        issues.append("prewrite Registry package must include component authoring previews")
    if component_preview:
        expected_components = {
            clean_text(row.get("component_id"))
            for row in _active_component_rows(package.proposal)
            if clean_text(row.get("component_id"))
        }
        preview_components = {clean_text(row.get("component_id")) for row in component_preview if clean_text(row.get("component_id"))}
        if expected_components != preview_components:
            issues.append("prewrite component authoring preview drifted from active ComponentContracts")
        for row in component_preview:
            gate = row.get("validation_gate") if isinstance(row.get("validation_gate"), Mapping) else {}
            if clean_text(gate.get("status")) != "passed":
                issues.append("prewrite component authoring preview validation gate did not pass")
            authoring_input = row.get("authoring_input") if isinstance(row.get("authoring_input"), Mapping) else {}
            if not authoring_input:
                issues.append("prewrite component authoring preview missing compiled authoring input")
            elif clean_text(authoring_input.get("component_id")) != clean_text(row.get("component_id")):
                issues.append("prewrite component authoring input drifted from Registry preview component id")
        issues.extend(generated_public_copy_issues("prewrite Registry preview", component_preview))
    if backlog_result and not project_brief_preview:
        issues.append("prewrite package must include project brief preview")
    if project_brief_preview:
        issues.extend(_project_brief_preview_issues(package, project_brief_preview))
    if backlog_result and not tribunal_preview:
        issues.append("prewrite package must include Tribunal evidence preview")
    if tribunal_preview:
        issues.extend(_tribunal_preview_issues(tribunal_preview))
    if backlog_result and component_preview and atlas_sources and not accepted_preview:
        issues.append("prewrite package must include accepted-project memory preview")
    if accepted_preview:
        issues.extend(_accepted_project_preview_issues(package, accepted_preview, component_preview, atlas_sources))
        issues.extend(generated_public_copy_issues("accepted-project memory preview", accepted_preview))
    if backlog_result and component_preview and atlas_sources and not project_dashboard_preview:
        issues.append("prewrite package must include Project dashboard preview")
    if project_dashboard_preview:
        issues.extend(_project_dashboard_preview_issues(project_dashboard_preview))
    if backlog_result and component_preview and atlas_sources and not compass_preview:
        issues.append("prewrite package must include Compass memory event preview")
    if compass_preview:
        issues.extend(_compass_memory_preview_issues(package, compass_preview, component_preview))
    if backlog_result and program_result and not next_steps_preview:
        issues.append("prewrite package must include operator next-steps preview")
    if next_steps_preview:
        issues.extend(_next_steps_preview_issues(package, next_steps_preview))
    if program_result and bool(program_result.get("created")) and clean_text(program_result.get("dry_run")).casefold() not in {"true", "1"}:
        issues.append("prewrite program package must be rendered in dry-run mode before governed writes")
    if package.release_selector and backlog_result and not package.release_workstream_ids:
        issues.append("prewrite release package must resolve first-release workstream ids")
    if package.release_selector:
        release_target = package.release_target_result if isinstance(package.release_target_result, Mapping) else {}
        release_assignment = package.release_assignment_result if isinstance(package.release_assignment_result, Mapping) else {}
        if not isinstance(release_target.get("release"), Mapping):
            issues.append("prewrite release package missing release target preview")
        elif clean_text(release_target.get("dry_run")).casefold() not in {"true", "1"}:
            issues.append("prewrite release target preview must run in dry-run mode")
        if not release_assignment:
            issues.append("prewrite release package missing release assignment preview")
        else:
            if clean_text(release_assignment.get("dry_run")).casefold() not in {"true", "1"}:
                issues.append("prewrite release assignment preview must run in dry-run mode")
            assigned_ids = {
                clean_text(item).upper()
                for item in release_assignment.get("workstream_ids", [])
                if clean_text(item)
            }
            expected_ids = {clean_text(item).upper() for item in package.release_workstream_ids if clean_text(item)}
            if expected_ids and not expected_ids.issubset(assigned_ids):
                issues.append("prewrite release assignment preview did not cover first-release workstream ids")
            target_release = release_target.get("release") if isinstance(release_target.get("release"), Mapping) else {}
            assignment_release = release_assignment.get("release") if isinstance(release_assignment.get("release"), Mapping) else {}
            if clean_text(target_release.get("release_id")) and clean_text(assignment_release.get("release_id")):
                if clean_text(target_release.get("release_id")) != clean_text(assignment_release.get("release_id")):
                    issues.append("prewrite release target preview drifted from release assignment preview")
    issues.extend(greenfield_rendered_package_quality_issues(package))
    return issues


def _project_dashboard_preview_issues(project_dashboard_preview: Mapping[str, Any]) -> list[str]:
    issues: list[str] = []
    prompts = mapping_rows(project_dashboard_preview.get("host_handoff_prompts"))
    if len(prompts) < 5:
        issues.append("Project dashboard preview must include all source-launch implementation prompts")
    return issues


def _project_brief_preview_issues(
    package: GreenfieldCompletionPackage,
    project_brief_preview: Mapping[str, Any],
) -> list[str]:
    issues = [
        issue.replace("proposal `project_brief`", "project brief preview")
        for issue in project_brief_issues(project_brief_preview)
    ]
    if clean_text(project_brief_preview.get("schema_version")) != PROJECT_BRIEF_SCHEMA_VERSION:
        issues.append("project brief preview has an unsupported schema version")
    if not _confirmed_greenfield_package(package.proposal):
        return issues
    semantic = package.proposal.get("semantic_model") if isinstance(package.proposal.get("semantic_model"), Mapping) else {}
    first_path = semantic.get("first_path_contract") if isinstance(semantic.get("first_path_contract"), Mapping) else {}
    proof_boundary = (
        semantic.get("domain_ontology", {}).get("proof_boundary")
        if isinstance(semantic.get("domain_ontology"), Mapping)
        else ""
    )
    preview_text = clean_text(" ".join(value for item in text_values(project_brief_preview) for value in text_values(item)))
    first_path_capability = clean_text(first_path.get("capability"))
    first_path_raw_path = clean_text(first_path.get("raw_path"))
    if (
        first_path_capability
        and _semantic_overlap_ratio(first_path_capability, preview_text) < 0.16
        and (not first_path_raw_path or _semantic_overlap_ratio(first_path_raw_path, preview_text) < 0.16)
    ):
        issues.append("project brief preview missing semantic coverage for FirstPathContract")
    if clean_text(proof_boundary) and _semantic_overlap_ratio(clean_text(proof_boundary), preview_text) < 0.12:
        issues.append("project brief preview missing semantic coverage for proof boundary")
    return issues


def _tribunal_preview_issues(tribunal_preview: Mapping[str, Any]) -> list[str]:
    issues: list[str] = []
    if clean_text(tribunal_preview.get("status")) != "passed":
        issues.append("Tribunal evidence preview did not pass")
    if clean_text(tribunal_preview.get("version")) != "greenfield-validation-gate-v1":
        issues.append("Tribunal evidence preview has an unsupported version")
    if not clean_text(tribunal_preview.get("summary")):
        issues.append("Tribunal evidence preview must include a summary")
    dimensions = tribunal_preview.get("dimensions") if isinstance(tribunal_preview.get("dimensions"), Mapping) else {}
    if len(dimensions) < 4:
        issues.append("Tribunal evidence preview must include dimension evidence")
    if isinstance(tribunal_preview.get("issues"), list) and tribunal_preview.get("issues"):
        issues.append("Tribunal evidence preview must not carry unresolved issues")
    return issues


def _next_steps_preview_issues(
    package: GreenfieldCompletionPackage,
    next_steps_preview: Mapping[str, Any],
) -> list[str]:
    issues: list[str] = []
    created_ids = {
        clean_text(row.get("idea_id")).upper()
        for row in mapping_rows((package.backlog_result or {}).get("created"))
        if clean_text(row.get("idea_id"))
    }
    start_id = clean_text(next_steps_preview.get("start_workstream_id")).upper()
    project_id = clean_text(next_steps_preview.get("project_workstream_id")).upper()
    if not start_id:
        issues.append("operator next-steps preview must identify the first implementation workstream")
    elif created_ids and start_id not in created_ids:
        issues.append("operator next-steps preview start workstream drifted from Radar prewrite output")
    if project_id and created_ids and project_id not in created_ids:
        issues.append("operator next-steps preview project workstream drifted from Radar prewrite output")
    if clean_text(next_steps_preview.get("release_selector")) != clean_text(package.release_selector):
        issues.append("operator next-steps preview release selector drifted from requested release")
    _require_preview_text(
        next_steps_preview,
        "implementation_prompt",
        issues,
        "operator next-steps preview must include an implementation prompt",
        min_words=18,
    )
    prompt = clean_text(next_steps_preview.get("implementation_prompt"))
    title = clean_text(next_steps_preview.get("start_workstream_title"))
    if start_id and start_id not in prompt.upper():
        issues.append("operator next-steps implementation prompt must name the first implementation workstream")
    if title and _semantic_overlap_ratio(title, prompt) < 0.32:
        issues.append("operator next-steps implementation prompt must mention the first implementation workstream title")
    semantic = package.proposal.get("semantic_model") if isinstance(package.proposal.get("semantic_model"), Mapping) else {}
    first_path = semantic.get("first_path_contract") if isinstance(semantic.get("first_path_contract"), Mapping) else {}
    first_path_text = _next_step_first_path_overlap_text(first_path)
    if first_path_text and not _next_step_prompt_preserves_first_path(first_path, prompt):
        issues.append("operator next-steps implementation prompt must overlap the accepted first path")
    operator_sequence = text_values(next_steps_preview.get("operator_sequence"))
    if len(operator_sequence) < 3:
        issues.append("operator next-steps preview must include an actionable operator sequence")
    gates = text_values(next_steps_preview.get("coding_readiness_gates"))
    if len(gates) < 4:
        issues.append("operator next-steps preview must carry coding-readiness gates")
    commands = text_values(next_steps_preview.get("verification_commands"))
    if len(commands) < 2:
        issues.append("operator next-steps preview must include multiple verification commands")
    issues.extend(_operator_next_step_copy_issues(next_steps_preview))
    return issues


def _operator_next_step_copy_issues(next_steps_preview: Mapping[str, Any]) -> list[str]:
    return list(generated_public_copy_issues("operator next-steps preview", next_steps_preview))


def _next_step_prompt_preserves_first_path(first_path: Mapping[str, Any], prompt: str) -> bool:
    prompt_text = clean_text(prompt).casefold()
    if not prompt_text:
        return False
    for candidate in _next_step_first_path_literal_candidates(first_path):
        text = clean_text(candidate)
        if text and text.casefold() in prompt_text:
            return True
    overlap_text = _next_step_first_path_overlap_text(first_path)
    return bool(overlap_text and _semantic_overlap_ratio(overlap_text, prompt) >= 0.08)


def _next_step_first_path_literal_candidates(first_path: Mapping[str, Any]) -> tuple[str, ...]:
    values: list[str] = []
    for key in ("raw_path",):
        text = clean_text(first_path.get(key))
        if text:
            values.append(text)
    return tuple(dict.fromkeys(values))


def _next_step_first_path_overlap_text(first_path: Mapping[str, Any]) -> str:
    """Return the semantic first-path projection that operator handoff copy must preserve."""

    values: list[str] = []
    for key in ("raw_path", "capability", "visible_result", "mutation", "action", "entity"):
        text = clean_text(first_path.get(key))
        if text:
            values.append(text)
    events = first_path.get("events")
    if isinstance(events, Sequence) and not isinstance(events, (str, bytes)):
        for event in events:
            if not isinstance(event, Mapping):
                continue
            for key in ("text", "mutation", "action", "target_entity"):
                text = clean_text(event.get(key))
                if text:
                    values.append(text)
    return clean_text(" ".join(values))


def _require_preview_text(
    value: Mapping[str, Any],
    key: str,
    issues: list[str],
    message: str,
    *,
    min_words: int,
) -> None:
    text = clean_text(value.get(key))
    if not text:
        issues.append(message)
        return
    if len([part for part in text.replace("/", " ").split() if part.strip()]) < min_words:
        issues.append(message)


def _radar_preview_semantic_issues(package: GreenfieldCompletionPackage, *, idea_files: Mapping[Any, Any]) -> list[str]:
    if not _confirmed_greenfield_package(package.proposal):
        return []
    text = clean_text(" ".join(str(value or "") for value in idea_files.values()))
    if not text:
        return []
    semantic = package.proposal.get("semantic_model") if isinstance(package.proposal.get("semantic_model"), Mapping) else {}
    first_path = semantic.get("first_path_contract") if isinstance(semantic.get("first_path_contract"), Mapping) else {}
    ontology = semantic.get("domain_ontology") if isinstance(semantic.get("domain_ontology"), Mapping) else {}
    issues: list[str] = []
    if not first_path_contract_has_coverage(
        first_path,
        text,
        overlap_ratio=_semantic_overlap_ratio,
        threshold=0.18,
    ):
        issues.append("prewrite Radar package missing semantic coverage for first path")
    proof_boundary = clean_text(ontology.get("proof_boundary"))
    if proof_boundary and _semantic_overlap_ratio(proof_boundary, text) < 0.18:
        issues.append("prewrite Radar package missing semantic coverage for proof boundary")
    return issues


def _atlas_preview_semantic_issues(package: GreenfieldCompletionPackage, atlas_sources: Mapping[str, str]) -> list[str]:
    if not _confirmed_greenfield_package(package.proposal):
        return []
    text = clean_text(" ".join(str(value or "") for value in atlas_sources.values()))
    if not text:
        return []
    semantic = package.proposal.get("semantic_model") if isinstance(package.proposal.get("semantic_model"), Mapping) else {}
    graph = semantic.get("diagram_event_graph") if isinstance(semantic.get("diagram_event_graph"), Mapping) else {}
    first_path = semantic.get("first_path_contract") if isinstance(semantic.get("first_path_contract"), Mapping) else {}
    issues: list[str] = []
    first_path_text = atlas_first_path_contract_coverage_text(semantic)
    if first_path_text and _semantic_overlap_ratio(first_path_text, text) < 0.16:
        issues.append("prewrite Atlas package missing semantic coverage for FirstPathContract")
    if "proof checkpoint" not in text.casefold():
        issues.append("prewrite Atlas package missing proof checkpoint diagram label")
    checkpoint = _atlas_checkpoint_search_text(clean_text(graph.get("proof_checkpoint")))
    if checkpoint and _semantic_overlap_ratio(checkpoint, text) < 0.12:
        issues.append("prewrite Atlas package missing semantic coverage for DiagramEventGraph proof checkpoint")
    return issues


def _atlas_checkpoint_search_text(value: str) -> str:
    text = clean_text(value)
    text = re.sub(r"^accepted\s+first\s+path\s+proof\s*:\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^proven\s+when\s+", "", text, flags=re.IGNORECASE)
    return text


def _accepted_project_preview_issues(
    package: GreenfieldCompletionPackage,
    accepted_preview: Mapping[str, Any],
    component_preview: Sequence[Mapping[str, Any]],
    atlas_sources: Mapping[str, str],
) -> list[str]:
    issues: list[str] = []
    if clean_text(accepted_preview.get("schema_version")) != "odylith.accepted_project.v1":
        issues.append("accepted-project memory preview has an unsupported schema version")
    if clean_text(accepted_preview.get("origin")) != "greenfield":
        issues.append("accepted-project memory preview must preserve greenfield origin")
    gate = accepted_preview.get("validation_gate") if isinstance(accepted_preview.get("validation_gate"), Mapping) else {}
    if clean_text(gate.get("status")) != "passed":
        issues.append("accepted-project memory preview validation gate did not pass")
    proposal = accepted_preview.get("proposal") if isinstance(accepted_preview.get("proposal"), Mapping) else {}
    if not isinstance(proposal.get("semantic_model"), Mapping):
        issues.append("accepted-project memory preview must include the GreenfieldSemanticModel")
    created = accepted_preview.get("created") if isinstance(accepted_preview.get("created"), Mapping) else {}
    if len(mapping_rows(created.get("workstreams"))) != len(mapping_rows((package.backlog_result or {}).get("created"))):
        issues.append("accepted-project memory preview workstream count drifted from Radar prewrite output")
    if len(mapping_rows(created.get("components"))) != len(component_preview):
        issues.append("accepted-project memory preview component count drifted from Registry prewrite output")
    diagram_ids = [item for item in created.get("diagrams", []) if clean_text(item)] if isinstance(created.get("diagrams"), list) else []
    if len(diagram_ids) != len(atlas_sources):
        issues.append("accepted-project memory preview diagram count drifted from Atlas prewrite output")
    if package.release_selector and clean_text(created.get("release_selector")) != clean_text(package.release_selector):
        issues.append("accepted-project memory preview release selector drifted from requested release")
    issues.extend(_source_launch_preview_issues(package, accepted_preview))
    issues.extend(_prewrite_path_leak_issues("accepted-project memory preview", accepted_preview))
    issues.extend(
        _component_preview_path_fidelity_issues(
            owner="accepted-project memory preview",
            expected=component_preview,
            actual=mapping_rows(created.get("components")),
        )
    )
    return issues


_SOURCE_LAUNCH_TERM_STOPWORDS = frozenset(
    {
        "accepted",
        "action",
        "after",
        "before",
        "blocked",
        "coding",
        "complete",
        "evidence",
        "first",
        "handoff",
        "path",
        "product",
        "project",
        "proof",
        "release",
        "result",
        "scope",
        "source",
        "state",
        "success",
        "this",
        "until",
        "user",
        "workstream",
    }
)


def _source_launch_preview_issues(
    package: GreenfieldCompletionPackage,
    accepted_preview: Mapping[str, Any],
) -> list[str]:
    source_launch = accepted_preview.get("source_launch") if isinstance(accepted_preview.get("source_launch"), Mapping) else {}
    prompt = clean_text(source_launch.get("implementation_prompt"))
    if not prompt:
        return []
    issues = list(generated_public_copy_issues("accepted-project source launch", prompt))
    proposal = accepted_preview.get("proposal") if isinstance(accepted_preview.get("proposal"), Mapping) else package.proposal
    semantic = proposal.get("semantic_model") if isinstance(proposal.get("semantic_model"), Mapping) else {}
    contract = semantic.get("first_path_contract") if isinstance(semantic.get("first_path_contract"), Mapping) else {}
    intent = proposal.get("intent") if isinstance(proposal.get("intent"), Mapping) else {}
    raw_path = clean_text(contract.get("raw_path") or intent.get("first_path"))
    state_object = clean_text(intent.get("state_object"))
    accepted_segment = _source_launch_accepted_path_segment(prompt)
    if (
        accepted_segment
        and raw_path
        and state_object
        and _source_launch_has_state_object_drift(accepted_segment, raw_path=raw_path, state_object=state_object)
    ):
        issues.append("accepted-project source launch implementation prompt mixes state-object terms into the accepted first-path clause")
    return issues


def _source_launch_accepted_path_segment(value: str) -> str:
    match = re.search(
        r"\bPreserve this accepted first path:\s*(?P<body>.+?)(?:\s+Treat\b|$)",
        clean_text(value),
        flags=re.I,
    )
    return clean_text(match.group("body")) if match else ""


def _source_launch_has_state_object_drift(segment: str, *, raw_path: str, state_object: str) -> bool:
    path_terms = set(ordered_terms(raw_path, minimum=4, stopwords=_SOURCE_LAUNCH_TERM_STOPWORDS, stem_ing=True))
    state_terms = set(ordered_terms(state_object, minimum=4, stopwords=_SOURCE_LAUNCH_TERM_STOPWORDS, stem_ing=True))
    segment_terms = set(ordered_terms(segment, minimum=4, stopwords=_SOURCE_LAUNCH_TERM_STOPWORDS, stem_ing=True))
    unexpected_state_terms = (state_terms - path_terms) & segment_terms
    return len(unexpected_state_terms) >= 2


def _compass_memory_preview_issues(
    package: GreenfieldCompletionPackage,
    compass_preview: Mapping[str, Any],
    component_preview: Sequence[Mapping[str, Any]],
) -> list[str]:
    issues: list[str] = []
    if clean_text(compass_preview.get("kind")) != "decision":
        issues.append("Compass memory event preview must be a decision event")
    if clean_text(compass_preview.get("evidence_tier")) != "user_intent":
        issues.append("Compass memory event preview must preserve user_intent evidence tier")
    if clean_text(compass_preview.get("work_category")) != "governance":
        issues.append("Compass memory event preview must preserve governance work category")
    if not clean_text(compass_preview.get("summary")):
        issues.append("Compass memory event preview must include an acceptance summary")
    workstreams = [item for item in compass_preview.get("workstreams", []) if clean_text(item)] if isinstance(compass_preview.get("workstreams"), list) else []
    if len(workstreams) != len(mapping_rows((package.backlog_result or {}).get("created"))):
        issues.append("Compass memory event preview workstreams drifted from Radar prewrite output")
    components = [item for item in compass_preview.get("components", []) if clean_text(item)] if isinstance(compass_preview.get("components"), list) else []
    if len(components) != len(component_preview):
        issues.append("Compass memory event preview components drifted from Registry prewrite output")
    issues.extend(_prewrite_path_leak_issues("Compass memory event preview", compass_preview))
    return issues


def _component_preview_path_fidelity_issues(
    *,
    owner: str,
    expected: Sequence[Mapping[str, Any]],
    actual: Sequence[Mapping[str, Any]],
) -> list[str]:
    issues: list[str] = []
    by_id = {clean_text(row.get("component_id")): row for row in actual if clean_text(row.get("component_id"))}
    for expected_row in expected:
        component_id = clean_text(expected_row.get("component_id"))
        if not component_id:
            continue
        actual_row = by_id.get(component_id)
        if not isinstance(actual_row, Mapping):
            continue
        for key in ("registry_path", "spec_path"):
            expected_path = clean_text(expected_row.get(key))
            actual_path = clean_text(actual_row.get(key))
            if expected_path and actual_path and not _same_component_artifact_path(expected_path, actual_path):
                issues.append(f"{owner} component `{component_id}` {key} drifted from Registry prewrite output")
    return issues


def _same_component_artifact_path(expected: str, actual: str) -> bool:
    """Compare governed component artifact paths by filesystem identity when possible."""

    expected_text = clean_text(expected)
    actual_text = clean_text(actual)
    if expected_text == actual_text:
        return True
    expected_path = Path(expected_text).expanduser()
    actual_path = Path(actual_text).expanduser()
    if not expected_path.is_absolute() or not actual_path.is_absolute():
        return False
    return expected_path.resolve(strict=False) == actual_path.resolve(strict=False)


def _prewrite_path_leak_issues(owner: str, value: Any) -> list[str]:
    leaked = sorted(
        {
            token
            for token in text_values(value)
            if "odylith-greenfield-prewrite-" in token
        }
    )
    if not leaked:
        return []
    return [f"{owner} contains staged prewrite temp path(s) instead of durable target paths"]


def _confirmed_greenfield_package(proposal: Mapping[str, Any]) -> bool:
    intent = proposal.get("intent") if isinstance(proposal.get("intent"), Mapping) else {}
    return clean_text(intent.get("reasoning_mode")) == "odylith_confirmed_governed_proposal"


def _active_component_rows(proposal: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    rows = mapping_rows(proposal.get("components"))
    active = [
        row
        for row in rows
        if clean_text(row.get("release_scope")).casefold() not in {"deferred", "out_of_scope", "external"}
    ]
    return active or rows


def _has_mermaid_declaration(value: str) -> bool:
    return bool(
        re.search(
            r"(?m)^\s*(?:"
            r"sequenceDiagram|flowchart|graph|classDiagram|stateDiagram(?:-v2)?|erDiagram|"
            r"journey|gantt|pie|mindmap|timeline|quadrantChart|gitGraph|C4Context|C4Container|C4Component"
            r")\b",
            value,
        )
    )


def _format_completion_issue_report(report: GreenfieldCompletionReport) -> str:
    rows = [f"greenfield post-confirm completion failed with {len(report.issues)} issue(s):"]
    rows.extend(f"- {issue}" for issue in report.issues)
    rows.extend(
        [
            "No governed records were written.",
            "This is an internal greenfield completion failure: repair the semantic model, renderers, or gates and rerun Confirm.",
        ]
    )
    return "\n".join(rows)


__all__ = [
    "GreenfieldCompletionPackage",
    "GreenfieldCompletionReport",
    "assert_greenfield_completion_ready",
    "assert_greenfield_package_ready",
    "build_greenfield_package_report",
    "build_greenfield_completion_report",
    "raise_for_failed_greenfield_completion",
]
