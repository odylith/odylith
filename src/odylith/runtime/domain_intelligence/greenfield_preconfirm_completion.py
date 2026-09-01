"""Pre-confirm completion gate for greenfield governed artifacts.

The compiler treats the proposal and staged rendered artifacts as one package,
repairs and validates it before final confirmation, and never writes target
governance truth from this gate.
"""

from __future__ import annotations

from collections.abc import Mapping
from collections.abc import Sequence
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_confirmed_proposal import (
    sealed_authored_projection,
)
from odylith.runtime.domain_intelligence.greenfield_rows import mapping_rows
from odylith.runtime.domain_intelligence.greenfield_preconfirm_handoff_quality import (
    next_steps_preview_issues,
    project_dashboard_preview_issues,
)
from odylith.runtime.domain_intelligence.greenfield_rows import mapping_count
from odylith.runtime.domain_intelligence.greenfield_rows import row_count
from odylith.runtime.domain_intelligence.greenfield_sealed_product_intent_authority import (
    PRODUCT_INTENT_AUTHORITY_KEY,
)
from odylith.runtime.domain_intelligence.greenfield_preconfirm_findings import (
    completion_review_findings,
)
from odylith.runtime.domain_intelligence.greenfield_preconfirm_findings import (
    package_review_findings,
)
from odylith.runtime.domain_intelligence.greenfield_preconfirm_package_findings import (
    package_artifact_findings,
)
from odylith.runtime.domain_intelligence.greenfield_preconfirm_package_hygiene import (
    prewrite_path_leak_issues as _prewrite_path_leak_issues,
)
from odylith.runtime.domain_intelligence.greenfield_preconfirm_package_hygiene import (
    same_component_artifact_path as _same_component_artifact_path,
)
from odylith.runtime.domain_intelligence.greenfield_preconfirm_review import (
    dedupe_review_findings,
)
from odylith.runtime.domain_intelligence.greenfield_surface_refresh_proof import (
    surface_refresh_preview_issues,
)
from odylith.runtime.domain_intelligence.greenfield_completion_types import (
    GreenfieldCompletionPackage,
)
from odylith.runtime.domain_intelligence.greenfield_completion_types import (
    GreenfieldCompletionReport,
)
from odylith.runtime.domain_intelligence.greenfield_text import clean_text
from odylith.runtime.domain_intelligence.greenfield_text import unique_text
from odylith.runtime.domain_intelligence.proposal_tribunal import run_greenfield_tribunal


PROJECT_BRIEF_SCHEMA_VERSION = "odylith.greenfield.project_brief.v1"


def build_greenfield_completion_report(
    proposal: Mapping[str, Any],
    *,
    release_selector: str = "",
    rendered_component_specs: Mapping[str, str] | None = None,
    tribunal_preview: Mapping[str, Any] | None = None,
    model_authored: bool = False,
) -> GreenfieldCompletionReport:
    """Evaluate the full pre-confirm package before any governed write."""

    del model_authored
    if not sealed_authored_projection(proposal):
        raise ValueError("Greenfield pre-confirm completion requires a sealed authored projection")
    model_authored = True
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
            model_authored=model_authored,
        )
    )
    issues = unique_text([finding.message for finding in findings])
    return GreenfieldCompletionReport(
        status="failed" if issues or findings else "passed",
        version="greenfield-pre-confirm-completion-v1",
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


def build_greenfield_package_report(
    package: GreenfieldCompletionPackage,
    *,
    model_authored: bool = False,
) -> GreenfieldCompletionReport:
    """Evaluate the named in-memory package used by confirmed greenfield writes."""

    del model_authored
    if not sealed_authored_projection(package.proposal):
        raise ValueError("Greenfield prewrite package requires a sealed authored projection")
    model_authored = True
    report = build_greenfield_completion_report(
        package.proposal,
        release_selector=package.release_selector,
        rendered_component_specs=package.rendered_component_specs,
        tribunal_preview=package.tribunal_preview,
        model_authored=model_authored,
    )
    package_issues = _package_artifact_issues(package, model_authored=model_authored)
    package_findings = package_review_findings(
        package,
        package_issues=package_issues,
        package_findings=package_artifact_findings(package, model_authored=model_authored),
        model_authored=model_authored,
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
            "atlas_catalog_rows": len(package.atlas_catalog_rows),
            "component_registry_previews": len(package.component_registry_preview),
            "project_brief_previews": 1 if isinstance(package.project_brief_preview, Mapping) else 0,
            "tribunal_previews": 1 if isinstance(package.tribunal_preview, Mapping) else 0,
            "accepted_project_previews": 1 if isinstance(package.accepted_project_preview, Mapping) else 0,
            "compass_memory_previews": 1 if isinstance(package.compass_memory_preview, Mapping) else 0,
            "next_steps_previews": 1 if isinstance(package.next_steps_preview, Mapping) else 0,
            "surface_refresh_previews": 1 if isinstance(package.surface_refresh_preview, Mapping) else 0,
            "release_assignment_previews": 1 if isinstance(package.release_assignment_result, Mapping) else 0,
            "release_workstream_ids": len(package.release_workstream_ids),
        },
        tribunal_status=report.tribunal_status,
        issues=tuple(issues),
        findings=findings,
    )


def raise_for_failed_greenfield_completion(report: GreenfieldCompletionReport) -> None:
    """Fail with an operator-safe pre-confirm completion report."""

    if report.passed:
        return
    raise ValueError(_format_completion_issue_report(report))


def assert_greenfield_completion_ready(
    proposal: Mapping[str, Any],
    *,
    release_selector: str = "",
    rendered_component_specs: Mapping[str, str] | None = None,
) -> GreenfieldCompletionReport:
    """Build and enforce the pre-confirm completion report."""

    report = build_greenfield_completion_report(
        proposal,
        release_selector=release_selector,
        rendered_component_specs=rendered_component_specs,
    )
    raise_for_failed_greenfield_completion(report)
    return report


def assert_greenfield_package_ready(
    package: GreenfieldCompletionPackage,
    *,
    model_authored: bool = False,
) -> GreenfieldCompletionReport:
    """Enforce the full pre-confirm package before write application continues."""

    del model_authored
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


def _package_artifact_issues(
    package: GreenfieldCompletionPackage,
    *,
    model_authored: bool = False,
) -> list[str]:
    del model_authored
    if not sealed_authored_projection(package.proposal):
        return ["prewrite package requires a sealed authored projection"]
    issues: list[str] = []
    backlog_result = package.backlog_result if isinstance(package.backlog_result, Mapping) else {}
    atlas_sources = package.rendered_atlas_sources if isinstance(package.rendered_atlas_sources, Mapping) else {}
    atlas_catalog_rows = [row for row in package.atlas_catalog_rows if isinstance(row, Mapping)]
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
        validation_gate = backlog_result.get("validation_gate") if isinstance(backlog_result.get("validation_gate"), Mapping) else {}
        if clean_text(validation_gate.get("status")) != "passed":
            issues.append("prewrite Radar package validation gate did not pass")
    elif package.rendered_component_specs:
        issues.append("prewrite package with Registry specs must include Radar workstream render output")
    if backlog_result and not atlas_sources:
        issues.append("prewrite package must include rendered Atlas Mermaid sources")
    if atlas_sources:
        if len(package.atlas_diagram_ids) != len(atlas_sources):
            issues.append("prewrite Atlas package must include one compiled diagram id per Mermaid source")
        for diagram_id in package.atlas_diagram_ids:
            if not _valid_compiled_diagram_id(clean_text(diagram_id)):
                issues.append("prewrite Atlas package contains an invalid compiled diagram id")
        if not _valid_iso_date_shape(clean_text(package.atlas_review_date)):
            issues.append("prewrite Atlas package must include a compiled review date")
        diagram_rows = mapping_rows(package.proposal.get("diagrams"))
        if len(atlas_sources) != len(diagram_rows):
            issues.append("prewrite Atlas package must render one Mermaid source per DiagramEventGraph diagram")
        if len(atlas_catalog_rows) != len(diagram_rows):
            issues.append("prewrite Atlas package must include one compiled catalog row per DiagramEventGraph diagram")
        catalog_ids = {clean_text(row.get("diagram_id")).upper() for row in atlas_catalog_rows if clean_text(row.get("diagram_id"))}
        diagram_ids = {clean_text(diagram_id).upper() for diagram_id in package.atlas_diagram_ids if clean_text(diagram_id)}
        if catalog_ids != diagram_ids:
            issues.append("prewrite Atlas catalog rows drifted from compiled diagram ids")
        source_paths = {clean_text(path) for path in atlas_sources if clean_text(path)}
        catalog_source_paths = {clean_text(row.get("source_mmd")) for row in atlas_catalog_rows if clean_text(row.get("source_mmd"))}
        if catalog_source_paths != source_paths:
            issues.append("prewrite Atlas catalog rows drifted from rendered Mermaid source paths")
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
    if backlog_result and not project_brief_preview:
        issues.append("prewrite package must include project brief preview")
    if project_brief_preview:
        issues.extend(
            _project_brief_preview_issues(project_brief_preview)
        )
    if backlog_result and not tribunal_preview:
        issues.append("prewrite package must include Tribunal evidence preview")
    if tribunal_preview:
        issues.extend(_tribunal_preview_issues(tribunal_preview))
    if backlog_result and component_preview and atlas_sources and not accepted_preview:
        issues.append("prewrite package must include accepted-project memory preview")
    if accepted_preview:
        issues.extend(
            _accepted_project_preview_issues(package, accepted_preview, component_preview, atlas_sources)
        )
    if backlog_result and component_preview and atlas_sources and not project_dashboard_preview:
        issues.append("prewrite package must include Project dashboard preview")
    if project_dashboard_preview:
        issues.extend(
            project_dashboard_preview_issues(
                package,
                project_dashboard_preview,
                model_authored=True,
            )
        )
    if backlog_result and component_preview and atlas_sources and not compass_preview:
        issues.append("prewrite package must include Compass memory event preview")
    if compass_preview:
        issues.extend(_compass_memory_preview_issues(package, compass_preview, component_preview))
    if backlog_result and not next_steps_preview:
        issues.append("prewrite package must include operator next-steps preview")
    if next_steps_preview:
        issues.extend(
            next_steps_preview_issues(
                package,
                next_steps_preview,
                semantic_checks=False,
            )
        )
    issues.extend(surface_refresh_preview_issues(package.surface_refresh_preview))
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
    return issues




def _project_brief_preview_issues(project_brief_preview: Mapping[str, Any]) -> list[str]:
    issues: list[str] = []
    if clean_text(project_brief_preview.get("schema_version")) != PROJECT_BRIEF_SCHEMA_VERSION:
        issues.append("project brief preview has an unsupported schema version")
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
    if PRODUCT_INTENT_AUTHORITY_KEY in proposal:
        issues.append("accepted-project memory preview contains the private Product Intent authority receipt")
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
    issues.extend(_prewrite_path_leak_issues("accepted-project memory preview", accepted_preview))
    issues.extend(
        _component_preview_path_fidelity_issues(
            owner="accepted-project memory preview",
            expected=component_preview,
            actual=mapping_rows(created.get("components")),
        )
    )
    return issues


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


def _active_component_rows(proposal: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    rows = mapping_rows(proposal.get("components"))
    active = [
        row
        for row in rows
        if clean_text(row.get("release_scope")).casefold() not in {"deferred", "out_of_scope", "external"}
    ]
    return active or rows


def _has_mermaid_declaration(value: str) -> bool:
    declarations = {
        "sequenceDiagram",
        "flowchart",
        "graph",
        "classDiagram",
        "stateDiagram",
        "stateDiagram-v2",
        "erDiagram",
        "journey",
        "gantt",
        "pie",
        "mindmap",
        "timeline",
        "quadrantChart",
        "gitGraph",
        "C4Context",
        "C4Container",
        "C4Component",
    }
    return any(
        line.strip().split(maxsplit=1)[0] in declarations
        for line in str(value or "").splitlines()
        if line.strip()
    )


def _valid_compiled_diagram_id(value: str) -> bool:
    suffix = value[2:] if value.startswith("D-") else ""
    return len(suffix) >= 3 and suffix.isdigit()


def _valid_iso_date_shape(value: str) -> bool:
    return (
        len(value) == 10
        and value[4:5] == "-"
        and value[7:8] == "-"
        and value[:4].isdigit()
        and value[5:7].isdigit()
        and value[8:].isdigit()
    )


def _format_completion_issue_report(report: GreenfieldCompletionReport) -> str:
    rows = [f"Odylith could not prepare a creation-ready package from the provided evidence ({len(report.issues)} issue(s)):"]
    rows.extend(f"- {issue}" for issue in report.issues)
    rows.extend(
        [
            "No governed records were written.",
            "Final CONFIRM is unavailable until Odylith compiles and validates the complete package.",
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
