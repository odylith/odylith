"""Post-confirm completion gate for greenfield governed artifacts.

Product Intent Confirmation stays a lightweight no-write interaction. After
confirmation, this gate treats the generated proposal and in-memory rendered
artifacts as one completion package and fails before governed writes begin.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict
from dataclasses import dataclass
import re
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_component_contract import (
    component_contract_issues,
    rendered_component_spec_quality_issues,
)
from odylith.runtime.domain_intelligence.greenfield_component_contract_differentiation import (
    component_spec_preflight_issues,
    operator_component_spec_issues,
)
from odylith.runtime.domain_intelligence.greenfield_project_brief import PROJECT_BRIEF_SCHEMA_VERSION
from odylith.runtime.domain_intelligence.greenfield_project_brief import project_brief_issues
from odylith.runtime.domain_intelligence.greenfield_quality_gate import greenfield_quality_issues
from odylith.runtime.domain_intelligence.greenfield_text import clean_text
from odylith.runtime.domain_intelligence.greenfield_text import normalize_domain_token
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

    @property
    def passed(self) -> bool:
        return self.status == "passed"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class GreenfieldCompletionPackage:
    """In-memory post-confirm package that must pass before governed writes."""

    proposal: Mapping[str, Any]
    release_selector: str = ""
    rendered_component_specs: Mapping[str, str] | None = None
    rendered_atlas_sources: Mapping[str, str] | None = None
    component_registry_preview: tuple[Mapping[str, Any], ...] = ()
    project_brief_preview: Mapping[str, Any] | None = None
    tribunal_preview: Mapping[str, Any] | None = None
    accepted_project_preview: Mapping[str, Any] | None = None
    compass_memory_preview: Mapping[str, Any] | None = None
    next_steps_preview: Mapping[str, Any] | None = None
    backlog_result: Mapping[str, Any] | None = None
    program_result: Mapping[str, Any] | None = None
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
    issues: list[str] = []
    issues.extend(_post_confirm_contract_issues(proposal, rendered_specs=rendered_specs))
    issues.extend(greenfield_quality_issues(proposal))
    issues.extend(component_contract_issues(proposal))
    issues.extend(component_spec_preflight_issues(proposal))
    if rendered_specs:
        title = _project_title(proposal)
        spec_issues = rendered_component_spec_quality_issues(rendered_specs, project_title=title)
        issues.extend(operator_component_spec_issues(spec_issues))
    issues.extend(tribunal_issues)
    issues = unique_text(issues)
    return GreenfieldCompletionReport(
        status="failed" if issues else "passed",
        version="greenfield-post-confirm-completion-v1",
        semantic_model=isinstance(proposal.get("semantic_model"), Mapping),
        artifact_counts={
            "workstreams": _row_count(proposal.get("backlog")),
            "components": _row_count(proposal.get("components")),
            "diagrams": _row_count(proposal.get("diagrams")),
            "rendered_component_specs": len(rendered_specs),
        },
        tribunal_status=tribunal_status,
        issues=tuple(issues),
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
    issues = unique_text([*report.issues, *package_issues])
    status = "failed" if issues else "passed"
    return GreenfieldCompletionReport(
        status=status,
        version=report.version,
        semantic_model=report.semantic_model,
        artifact_counts={
            **report.artifact_counts,
            "rendered_workstream_files": _mapping_count((package.backlog_result or {}).get("idea_files")),
            "rendered_atlas_sources": _mapping_count(package.rendered_atlas_sources),
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


def _project_title(proposal: Mapping[str, Any]) -> str:
    intent = proposal.get("intent") if isinstance(proposal.get("intent"), Mapping) else {}
    return str(intent.get("title", "")).strip()


def _post_confirm_contract_issues(proposal: Mapping[str, Any], *, rendered_specs: Mapping[str, str]) -> list[str]:
    """Check the package contract that makes Confirm a complete write boundary."""

    issues: list[str] = []
    if int(proposal.get("provider_calls") or 0) != 0:
        issues.append("post-confirm completion must be provider-free by default")
    semantic = proposal.get("semantic_model")
    if not isinstance(semantic, Mapping):
        return ["post-confirm completion requires GreenfieldSemanticModel before rendering governed artifacts"]
    issues.extend(_semantic_model_shape_issues(semantic))
    issues.extend(_semantic_component_alignment_issues(proposal, semantic))
    issues.extend(_semantic_workstream_alignment_issues(proposal, semantic))
    issues.extend(_semantic_diagram_alignment_issues(proposal, semantic))
    issues.extend(_contrastive_domain_drift_issues(proposal, semantic))
    issues.extend(_semantic_repetition_issues(proposal))
    if rendered_specs:
        issues.extend(_rendered_spec_alignment_issues(proposal, rendered_specs))
    return issues


def _package_artifact_issues(package: GreenfieldCompletionPackage) -> list[str]:
    issues: list[str] = []
    backlog_result = package.backlog_result if isinstance(package.backlog_result, Mapping) else {}
    program_result = package.program_result if isinstance(package.program_result, Mapping) else {}
    atlas_sources = package.rendered_atlas_sources if isinstance(package.rendered_atlas_sources, Mapping) else {}
    component_preview = [row for row in package.component_registry_preview if isinstance(row, Mapping)]
    project_brief_preview = package.project_brief_preview if isinstance(package.project_brief_preview, Mapping) else {}
    tribunal_preview = package.tribunal_preview if isinstance(package.tribunal_preview, Mapping) else {}
    accepted_preview = package.accepted_project_preview if isinstance(package.accepted_project_preview, Mapping) else {}
    compass_preview = package.compass_memory_preview if isinstance(package.compass_memory_preview, Mapping) else {}
    next_steps_preview = package.next_steps_preview if isinstance(package.next_steps_preview, Mapping) else {}
    if backlog_result:
        created = _mapping_rows(backlog_result.get("created"))
        idea_files = backlog_result.get("idea_files") if isinstance(backlog_result.get("idea_files"), Mapping) else {}
        proposal_titles = {
            clean_text(row.get("title"))
            for row in _mapping_rows(package.proposal.get("backlog"))
            if clean_text(row.get("title"))
        }
        created_titles = {clean_text(row.get("title")) for row in created if clean_text(row.get("title"))}
        if proposal_titles != created_titles:
            issues.append("prewrite Radar package drifted from WorkstreamContracts")
        if len(idea_files) != len(created):
            issues.append("prewrite Radar package must render one workstream file per created workstream")
        if not clean_text(backlog_result.get("backlog_index_text")):
            issues.append("prewrite Radar package missing rendered backlog index text")
        issues.extend(_mechanical_public_copy_issues("prewrite Radar package", " ".join(str(value or "") for value in idea_files.values())))
        validation_gate = backlog_result.get("validation_gate") if isinstance(backlog_result.get("validation_gate"), Mapping) else {}
        if clean_text(validation_gate.get("status")) != "passed":
            issues.append("prewrite Radar package validation gate did not pass")
        issues.extend(_radar_preview_semantic_issues(package, idea_files=idea_files))
    elif package.rendered_component_specs:
        issues.append("prewrite package with Registry specs must include Radar workstream render output")
    if backlog_result and not atlas_sources:
        issues.append("prewrite package must include rendered Atlas Mermaid sources")
    if atlas_sources:
        diagram_rows = _mapping_rows(package.proposal.get("diagrams"))
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
        issues.extend(_mechanical_public_copy_issues("prewrite Registry preview", " ".join(text_values(component_preview))))
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
        issues.extend(_mechanical_public_copy_issues("accepted-project memory preview", " ".join(text_values(accepted_preview))))
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
    if clean_text(first_path.get("capability")) and _semantic_overlap_ratio(clean_text(first_path.get("capability")), preview_text) < 0.16:
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
        for row in _mapping_rows((package.backlog_result or {}).get("created"))
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
        min_words=10,
    )
    operator_sequence = text_values(next_steps_preview.get("operator_sequence"))
    if len(operator_sequence) < 3:
        issues.append("operator next-steps preview must include an actionable operator sequence")
    gates = text_values(next_steps_preview.get("coding_readiness_gates"))
    if len(gates) < 3:
        issues.append("operator next-steps preview must carry coding-readiness gates")
    commands = text_values(next_steps_preview.get("verification_commands"))
    if not commands:
        issues.append("operator next-steps preview must include verification commands")
    issues.extend(_operator_next_step_copy_issues(next_steps_preview))
    return issues


def _operator_next_step_copy_issues(next_steps_preview: Mapping[str, Any]) -> list[str]:
    return _mechanical_public_copy_issues("operator next-steps preview", " ".join(text_values(next_steps_preview)))


def _mechanical_public_copy_issues(scope: str, value: str) -> list[str]:
    issues: list[str] = []
    text = clean_text(value)
    lowered = text.casefold()
    if re.search(r"\bcan\s+act\s+where\s+the\s+accepted\s+path\s+requires\b", lowered):
        issues.append(f"{scope} leaked mechanical actor-path prose")
    if re.search(r"\bexpected\s+local\s+output\s*:", lowered):
        issues.append(f"{scope} leaked generic local-output prose")
    if re.search(r"\bactor\s+identity,\s+validation\s+context,\s+and\s+upstream\s+handoff\b", lowered):
        issues.append(f"{scope} leaked Registry contract tuple prose")
    if re.search(r"\bblocker\s+signal,\s+review\s+rationale,\s+and\s+downstream\s+handoff\b", lowered):
        issues.append(f"{scope} leaked produced-output tuple prose")
    if re.search(r"\bvalidate\s+that\s+.+?\bsatisfies\s+its\s+local\s+success\s+criteria\s*:", lowered):
        issues.append(f"{scope} leaked raw success-metric gate prose")
    return issues


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
    intent = package.proposal.get("intent") if isinstance(package.proposal.get("intent"), Mapping) else {}
    required = {
        "first path": clean_text(first_path.get("capability") or intent.get("first_path")),
        "proof boundary": clean_text(ontology.get("proof_boundary")),
    }
    issues: list[str] = []
    for label, value in required.items():
        if value and _semantic_overlap_ratio(value, text) < 0.18:
            issues.append(f"prewrite Radar package missing semantic coverage for {label}")
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
    first_path_text = clean_text(first_path.get("capability"))
    if first_path_text and _semantic_overlap_ratio(first_path_text, text) < 0.16:
        issues.append("prewrite Atlas package missing semantic coverage for FirstPathContract")
    if "proof checkpoint" not in text.casefold():
        issues.append("prewrite Atlas package missing proof checkpoint diagram label")
    checkpoint = clean_text(graph.get("proof_checkpoint"))
    if checkpoint and _semantic_overlap_ratio(checkpoint, text) < 0.12:
        issues.append("prewrite Atlas package missing semantic coverage for DiagramEventGraph proof checkpoint")
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
    if not isinstance(proposal.get("semantic_model"), Mapping):
        issues.append("accepted-project memory preview must include the GreenfieldSemanticModel")
    created = accepted_preview.get("created") if isinstance(accepted_preview.get("created"), Mapping) else {}
    if len(_mapping_rows(created.get("workstreams"))) != len(_mapping_rows((package.backlog_result or {}).get("created"))):
        issues.append("accepted-project memory preview workstream count drifted from Radar prewrite output")
    if len(_mapping_rows(created.get("components"))) != len(component_preview):
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
            actual=_mapping_rows(created.get("components")),
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
    if len(workstreams) != len(_mapping_rows((package.backlog_result or {}).get("created"))):
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
            if expected_path and actual_path and expected_path != actual_path:
                issues.append(f"{owner} component `{component_id}` {key} drifted from Registry prewrite output")
    return issues


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


def _semantic_overlap_ratio(source: str, target: str) -> float:
    source_terms = _term_signature(source, minimum=5)
    if not source_terms:
        return 1.0
    target_terms = _term_signature(target, minimum=5)
    if not target_terms:
        return 0.0
    return len(source_terms & target_terms) / max(1, len(source_terms))


def _confirmed_greenfield_package(proposal: Mapping[str, Any]) -> bool:
    intent = proposal.get("intent") if isinstance(proposal.get("intent"), Mapping) else {}
    return clean_text(intent.get("reasoning_mode")) == "odylith_confirmed_governed_proposal"


def _active_component_rows(proposal: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    rows = _mapping_rows(proposal.get("components"))
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


def _semantic_model_shape_issues(semantic: Mapping[str, Any]) -> list[str]:
    required = (
        "first_path_contract",
        "domain_ontology",
        "components",
        "workstreams",
        "diagram_event_graph",
        "proof_obligations",
    )
    issues = [f"GreenfieldSemanticModel missing `{key}`" for key in required if not isinstance(semantic.get(key), (Mapping, list))]
    if clean_text(semantic.get("schema_version")) != "odylith.greenfield.semantic_model.v1":
        issues.append("GreenfieldSemanticModel schema_version is missing or unsupported")
    first_path = semantic.get("first_path_contract") if isinstance(semantic.get("first_path_contract"), Mapping) else {}
    events = first_path.get("events") if isinstance(first_path, Mapping) else None
    if not isinstance(events, list) or not events:
        issues.append("FirstPathContract must include structured first-path events")
    elif not any(isinstance(row, Mapping) and row.get("visible_result") for row in events):
        issues.append("FirstPathContract must identify at least one visible result event")
    if not clean_text(first_path.get("capability") if isinstance(first_path, Mapping) else ""):
        issues.append("FirstPathContract must preserve the accepted path capability")
    ontology = semantic.get("domain_ontology") if isinstance(semantic.get("domain_ontology"), Mapping) else {}
    if not clean_text(ontology.get("product_title") if isinstance(ontology, Mapping) else ""):
        issues.append("DomainOntology must carry the canonical product title")
    graph = semantic.get("diagram_event_graph") if isinstance(semantic.get("diagram_event_graph"), Mapping) else {}
    if not clean_text(graph.get("proof_checkpoint") if isinstance(graph, Mapping) else ""):
        issues.append("DiagramEventGraph must carry a readable proof checkpoint")
    proof_keys = {
        clean_text(row.get("key"))
        for row in _mapping_rows(semantic.get("proof_obligations"))
        if clean_text(row.get("key"))
    }
    for key in ("first_path_contract", "release_boundary"):
        if key not in proof_keys:
            issues.append(f"GreenfieldSemanticModel missing `{key}` proof obligation")
    return issues


def _semantic_component_alignment_issues(proposal: Mapping[str, Any], semantic: Mapping[str, Any]) -> list[str]:
    proposal_components = _mapping_rows(proposal.get("components"))
    model_components = _mapping_rows(semantic.get("components"))
    issues: list[str] = []
    proposal_by_id = {_component_id(row): row for row in proposal_components if _component_id(row)}
    model_by_id = {_component_id(row): row for row in model_components if _component_id(row)}
    if set(proposal_by_id) != set(model_by_id):
        missing = sorted(set(proposal_by_id) - set(model_by_id))
        extra = sorted(set(model_by_id) - set(proposal_by_id))
        if missing:
            issues.append(f"GreenfieldSemanticModel missing component contract(s): {', '.join(missing[:5])}")
        if extra:
            issues.append(f"GreenfieldSemanticModel has component contract(s) not rendered by proposal: {', '.join(extra[:5])}")
    for component_id, row in proposal_by_id.items():
        model = model_by_id.get(component_id)
        if not isinstance(model, Mapping):
            continue
        contract = row.get("component_contract") if isinstance(row.get("component_contract"), Mapping) else {}
        checks = {
            "label": clean_text(row.get("label")),
            "release_scope": clean_text(row.get("release_scope")),
            "owned_state": clean_text(contract.get("owned_state") if isinstance(contract, Mapping) else ""),
            "accepted_inputs": clean_text(contract.get("accepted_inputs") if isinstance(contract, Mapping) else ""),
            "produced_outputs": clean_text(contract.get("produced_outputs") if isinstance(contract, Mapping) else ""),
        }
        for key, expected in checks.items():
            actual = clean_text(model.get(key))
            if expected and actual != expected:
                issues.append(f"GreenfieldSemanticModel component `{component_id}` drifted from proposal `{key}`")
        proposal_proofs = tuple(clean_text(value) for value in text_values(contract.get("local_proof") if isinstance(contract, Mapping) else ()) if clean_text(value))
        model_proofs = tuple(clean_text(value) for value in text_values(model.get("proof_obligations")) if clean_text(value))
        if proposal_proofs and proposal_proofs != model_proofs:
            issues.append(f"GreenfieldSemanticModel component `{component_id}` proof obligations drifted from ComponentContract")
    proof_keys = {
        clean_text(row.get("key"))
        for row in _mapping_rows(semantic.get("proof_obligations"))
    }
    for component_id, row in proposal_by_id.items():
        if clean_text(row.get("release_scope")) == "out_of_scope":
            continue
        if f"component_{component_id}" not in proof_keys:
            issues.append(f"GreenfieldSemanticModel missing proof obligation for active component `{component_id}`")
    return issues


def _semantic_workstream_alignment_issues(proposal: Mapping[str, Any], semantic: Mapping[str, Any]) -> list[str]:
    proposal_rows = _mapping_rows(proposal.get("backlog"))
    model_rows = _mapping_rows(semantic.get("workstreams"))
    proposal_by_title = {clean_text(row.get("title")): row for row in proposal_rows if clean_text(row.get("title"))}
    model_by_title = {clean_text(row.get("title")): row for row in model_rows if clean_text(row.get("title"))}
    proposal_titles = set(proposal_by_title)
    model_titles = set(model_by_title)
    missing = sorted(proposal_titles - model_titles)
    extra = sorted(model_titles - proposal_titles)
    issues: list[str] = []
    if missing:
        issues.append(f"GreenfieldSemanticModel missing workstream contract(s): {', '.join(missing[:4])}")
    if extra:
        issues.append(f"GreenfieldSemanticModel has workstream contract(s) not rendered by proposal: {', '.join(extra[:4])}")
    for title in sorted(proposal_titles.intersection(model_titles)):
        proposal_row = proposal_by_title[title]
        model_row = model_by_title[title]
        checks = {
            "local_problem": clean_text(proposal_row.get("problem")),
            "first_slice": clean_text(proposal_row.get("recommended_first_slice")),
            "proof": " ".join(clean_text(value) for value in text_values(proposal_row.get("validation")) if clean_text(value)),
        }
        for key, expected in checks.items():
            actual = clean_text(model_row.get(key))
            if expected and actual != expected:
                issues.append(f"GreenfieldSemanticModel workstream `{title}` drifted from proposal `{key}`")
        proposal_components = tuple(clean_text(value) for value in text_values(proposal_row.get("component_focus")) if clean_text(value))
        model_components = tuple(clean_text(value) for value in text_values(model_row.get("component_ids")) if clean_text(value))
        if proposal_components and proposal_components != model_components:
            issues.append(f"GreenfieldSemanticModel workstream `{title}` component_ids drifted from proposal component_focus")
    return issues


def _semantic_diagram_alignment_issues(proposal: Mapping[str, Any], semantic: Mapping[str, Any]) -> list[str]:
    graph = semantic.get("diagram_event_graph") if isinstance(semantic.get("diagram_event_graph"), Mapping) else {}
    active_components = {
        _component_id(row)
        for row in _mapping_rows(proposal.get("components"))
        if _component_id(row) and _is_first_release_scope(row.get("release_scope"))
    }
    graph_components = {clean_text(value) for value in text_values(graph.get("component_sequence") if isinstance(graph, Mapping) else ()) if clean_text(value)}
    issues: list[str] = []
    if active_components != graph_components:
        issues.append("DiagramEventGraph component sequence drifted from active ReleaseScope components")
    first_path = semantic.get("first_path_contract") if isinstance(semantic.get("first_path_contract"), Mapping) else {}
    first_path_events = tuple(
        clean_text(row.get("text"))
        for row in _mapping_rows(first_path.get("events") if isinstance(first_path, Mapping) else ())
        if clean_text(row.get("text"))
    )
    graph_events = tuple(
        clean_text(row.get("text"))
        for row in _mapping_rows(graph.get("events") if isinstance(graph, Mapping) else ())
        if clean_text(row.get("text"))
    )
    if first_path_events and graph_events != first_path_events:
        issues.append("DiagramEventGraph events drifted from FirstPathContract events")
    diagram_rows = _mapping_rows(proposal.get("diagrams"))
    if not diagram_rows:
        issues.append("post-confirm completion requires in-memory Atlas diagram artifacts")
    for row in diagram_rows:
        if not clean_text(row.get("mermaid_source")):
            issues.append(f"Atlas diagram `{clean_text(row.get('title')) or clean_text(row.get('slug'))}` missing in-memory Mermaid source")
    return issues


def _rendered_spec_alignment_issues(proposal: Mapping[str, Any], rendered_specs: Mapping[str, str]) -> list[str]:
    active_labels = {
        clean_text(row.get("label"))
        for row in _mapping_rows(proposal.get("components"))
        if clean_text(row.get("label")) and clean_text(row.get("release_scope")) != "out_of_scope"
    }
    rendered_labels = {clean_text(label) for label in rendered_specs}
    issues: list[str] = []
    if active_labels and rendered_labels != active_labels:
        missing = sorted(active_labels - rendered_labels)
        extra = sorted(rendered_labels - active_labels)
        if missing:
            issues.append(f"prewrite Registry package missing rendered active component spec(s): {', '.join(missing[:5])}")
        if extra:
            issues.append(f"prewrite Registry package rendered component spec(s) outside active release scope: {', '.join(extra[:5])}")
    return issues


def _contrastive_domain_drift_issues(proposal: Mapping[str, Any], semantic: Mapping[str, Any]) -> list[str]:
    """Flag repeated high-signal terms not grounded in this intent or model."""

    signature_terms = _term_signature(_intent_signature_text(proposal), minimum=4)
    ontology = semantic.get("domain_ontology") if isinstance(semantic.get("domain_ontology"), Mapping) else {}
    first_path = semantic.get("first_path_contract") if isinstance(semantic.get("first_path_contract"), Mapping) else {}
    signature_terms.update(_term_signature(" ".join(text_values(ontology)), minimum=4))
    signature_terms.update(_term_signature(" ".join(text_values(first_path)), minimum=4))
    signature_terms.update(_term_signature(_component_signature_text(proposal), minimum=4))
    generated_text = _generated_artifact_text(proposal)
    generated_counts: dict[str, int] = {}
    for term in _term_signature(generated_text, minimum=5):
        if term in signature_terms or term in _CONTRASTIVE_GENERIC_TERMS:
            continue
        generated_counts[term] = len(re.findall(rf"\b{re.escape(term)}\b", generated_text.casefold()))
    leaked = sorted(
        term
        for term, count in generated_counts.items()
        if count >= _CONTRASTIVE_REPEAT_THRESHOLD and len(term) >= _CONTRASTIVE_MIN_UNGROUNDED_TERM_LENGTH
    )
    if leaked:
        return [f"contrastive domain drift: generated artifact terms are not grounded in accepted intent: {', '.join(leaked[:8])}"]
    return []


def _semantic_repetition_issues(proposal: Mapping[str, Any]) -> list[str]:
    """Cluster near-duplicate public sentences across generated surfaces."""

    sentences = _generated_artifact_sentences(proposal)
    signatures: list[tuple[str, set[str]]] = []
    for sentence in sentences:
        signature = _sentence_signature(sentence)
        if len(signature) >= 8:
            signatures.append((sentence, signature))
    if len(signatures) < _REPETITION_CLUSTER_SIZE:
        return []
    for left_index, (sentence, left_terms) in enumerate(signatures):
        near_duplicate_count = 1
        for right_index in range(left_index + 1, len(signatures)):
            right_terms = signatures[right_index][1]
            overlap = len(left_terms & right_terms)
            if overlap < _REPETITION_MIN_SHARED_TERMS:
                continue
            union_size = len(left_terms | right_terms)
            similarity = overlap / max(1, union_size)
            if similarity >= _REPETITION_SIMILARITY_THRESHOLD:
                near_duplicate_count += 1
        if near_duplicate_count >= _REPETITION_CLUSTER_SIZE:
            sample = clean_text(sentence)
            return [
                "semantic repetition: generated artifacts repeat the same sentence shape across "
                f"{near_duplicate_count} surfaces; sample `{sample[:140]}`"
            ]
    return []


def _generated_artifact_sentences(proposal: Mapping[str, Any]) -> list[str]:
    sentences: list[str] = []
    for text in _generated_repetition_value_texts(proposal):
        for sentence in re.split(r"(?<=[.!?])\s+|\n+|;\s+", text):
            cleaned = clean_text(sentence).strip(" -•")
            if len(re.findall(r"[A-Za-z0-9][A-Za-z0-9'-]*", cleaned)) >= 10:
                sentences.append(cleaned)
    return sentences


def _sentence_signature(value: str) -> set[str]:
    terms: set[str] = set()
    for raw in re.findall(r"[A-Za-z0-9][A-Za-z0-9_-]*", clean_text(value).casefold()):
        token = normalize_domain_token(
            raw,
            minimum=4,
            stopwords=(*_CONTRASTIVE_GENERIC_TERMS, *_CONTRASTIVE_STOPWORDS),
        )
        if token and token not in _CONTRASTIVE_GENERIC_TERMS and token not in _CONTRASTIVE_STOPWORDS:
            terms.add(token)
    return terms


def _intent_signature_text(proposal: Mapping[str, Any]) -> str:
    intent = proposal.get("intent") if isinstance(proposal.get("intent"), Mapping) else {}
    rows = [
        intent.get("title"),
        intent.get("product_story"),
        intent.get("state_object"),
        intent.get("first_path"),
        intent.get("proof_boundary"),
        *text_values(intent.get("human_actors")),
        *text_values(intent.get("external_systems")),
        *text_values(intent.get("internal_systems")),
        *text_values(intent.get("critical_assumptions")),
        *text_values(intent.get("ambiguities")),
        *text_values(intent.get("non_goals")),
    ]
    return " ".join(clean_text(row) for row in rows if clean_text(row))


def _component_signature_text(proposal: Mapping[str, Any]) -> str:
    rows: list[Any] = []
    for row in _mapping_rows(proposal.get("components")):
        rows.extend([row.get("label"), row.get("source_system_description")])
    return " ".join(clean_text(row) for row in rows if clean_text(row))


def _generated_artifact_text(proposal: Mapping[str, Any]) -> str:
    return " ".join(_generated_artifact_value_texts(proposal))


def _generated_artifact_value_texts(proposal: Mapping[str, Any]) -> list[str]:
    rows: list[Any] = []
    for row in _mapping_rows(proposal.get("backlog")):
        rows.extend(
            [
                row.get("title"),
                row.get("problem"),
                row.get("opportunity"),
                row.get("product_view"),
                row.get("recommended_first_slice"),
                row.get("success_metrics"),
                row.get("validation"),
            ]
        )
    for row in _mapping_rows(proposal.get("components")):
        rows.extend([row.get("label"), row.get("source_system_description"), row.get("component_contract")])
    for row in _mapping_rows(proposal.get("diagrams")):
        rows.extend([row.get("title"), row.get("summary"), row.get("read_guide"), row.get("components")])
    release_plan = proposal.get("release_plan") if isinstance(proposal.get("release_plan"), Mapping) else {}
    rows.extend([release_plan.get("strategy"), release_plan.get("promotion_criteria")])
    brief = proposal.get("project_brief") if isinstance(proposal.get("project_brief"), Mapping) else {}
    rows.extend([brief.get("story"), brief.get("first_path"), brief.get("proof")])
    return [clean_text(value) for item in rows for value in text_values(item) if clean_text(value)]


def _generated_repetition_value_texts(proposal: Mapping[str, Any]) -> list[str]:
    rows: list[Any] = []
    for row in _mapping_rows(proposal.get("backlog")):
        rows.extend(
            [
                row.get("problem"),
                row.get("opportunity"),
                row.get("product_view"),
                row.get("recommended_first_slice"),
                row.get("success_metrics"),
                row.get("validation"),
            ]
        )
    for row in _mapping_rows(proposal.get("components")):
        rows.extend([row.get("source_system_description"), row.get("component_contract")])
    for row in _mapping_rows(proposal.get("diagrams")):
        rows.extend([row.get("summary"), row.get("read_guide")])
    release_plan = proposal.get("release_plan") if isinstance(proposal.get("release_plan"), Mapping) else {}
    rows.extend([release_plan.get("strategy"), release_plan.get("promotion_criteria")])
    brief = proposal.get("project_brief") if isinstance(proposal.get("project_brief"), Mapping) else {}
    rows.extend([brief.get("story"), brief.get("first_path"), brief.get("proof")])
    return [clean_text(value) for item in rows for value in text_values(item) if clean_text(value)]


def _term_signature(value: str, *, minimum: int) -> set[str]:
    terms: set[str] = set()
    normalized = clean_text(value).casefold().replace("-", " ").replace("_", " ")
    for raw in re.findall(r"[a-z0-9][a-z0-9]*", normalized):
        token = normalize_domain_token(
            raw,
            minimum=minimum,
            stopwords=(*_CONTRASTIVE_GENERIC_TERMS, *_CONTRASTIVE_STOPWORDS),
        )
        if token and token not in _CONTRASTIVE_GENERIC_TERMS and token not in _CONTRASTIVE_STOPWORDS:
            terms.add(token)
    return terms


_CONTRASTIVE_GENERIC_TERMS = {
    "accepted",
    "action",
    "access",
    "active",
    "adjacent",
    "against",
    "actor",
    "artifact",
    "assertion",
    "approval",
    "approved",
    "authorized",
    "assigned",
    "automation",
    "avoided",
    "backlog",
    "before",
    "behavior",
    "blocked",
    "blocker",
    "boundary",
    "build",
    "built",
    "candidate",
    "central",
    "changed",
    "classification",
    "claim",
    "command",
    "component",
    "complete",
    "completed",
    "completion",
    "context",
    "contract",
    "correction",
    "created",
    "current",
    "decision",
    "deferred",
    "dependency",
    "depend",
    "depended",
    "depends",
    "derived",
    "diagram",
    "domain",
    "downstream",
    "external",
    "evidence",
    "explanation",
    "failure",
    "final",
    "first",
    "forbidden",
    "follow",
    "gate",
    "generic",
    "governance",
    "greenfield",
    "handoff",
    "history",
    "identity",
    "implementation",
    "implement",
    "implemented",
    "implements",
    "input",
    "inside",
    "interface",
    "interfaces",
    "internal",
    "intent",
    "invalid",
    "issue",
    "local",
    "marker",
    "missing",
    "mutation",
    "named",
    "output",
    "outside",
    "own",
    "owned",
    "owner",
    "ownership",
    "owns",
    "package",
    "planned",
    "policy",
    "privacy",
    "proof",
    "proposal",
    "produce",
    "produced",
    "product",
    "rationale",
    "ready",
    "readiness",
    "record",
    "recovery",
    "refused",
    "release",
    "released",
    "require",
    "required",
    "requirement",
    "responsibility",
    "rendered",
    "replay",
    "request",
    "result",
    "review",
    "reviewable",
    "reviewer",
    "runtime",
    "scope",
    "sibling",
    "signal",
    "source",
    "state",
    "status",
    "stream",
    "stale",
    "success",
    "system",
    "target",
    "technical",
    "trace",
    "traceable",
    "transition",
    "truth",
    "upstream",
    "validation",
    "validated",
    "valid",
    "versioned",
    "visible",
    "workstream",
    "wrong",
}

_CONTRASTIVE_REPEAT_THRESHOLD = 8
_CONTRASTIVE_MIN_UNGROUNDED_TERM_LENGTH = 10
_REPETITION_CLUSTER_SIZE = 6
_REPETITION_SIMILARITY_THRESHOLD = 0.88
_REPETITION_MIN_SHARED_TERMS = 8

_CONTRASTIVE_STOPWORDS = {
    "about",
    "after",
    "again",
    "against",
    "among",
    "around",
    "because",
    "before",
    "being",
    "between",
    "could",
    "every",
    "from",
    "their",
    "there",
    "these",
    "those",
    "through",
    "until",
    "where",
    "which",
    "while",
    "within",
    "without",
    "would",
}


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


def _mapping_rows(value: Any) -> list[Mapping[str, Any]]:
    return [row for row in value if isinstance(row, Mapping)] if isinstance(value, list) else []


def _component_id(row: Mapping[str, Any]) -> str:
    return clean_text(row.get("component_id") or row.get("id") or row.get("label"))


def _row_count(value: Any) -> int:
    return len([row for row in value if isinstance(row, Mapping)]) if isinstance(value, list) else 0


def _mapping_count(value: Any) -> int:
    return len(value) if isinstance(value, Mapping) else 0


def _is_first_release_scope(value: Any) -> bool:
    return clean_text(value).casefold() not in {"deferred", "external", "out_of_scope"}


__all__ = [
    "GreenfieldCompletionPackage",
    "GreenfieldCompletionReport",
    "assert_greenfield_completion_ready",
    "assert_greenfield_package_ready",
    "build_greenfield_package_report",
    "build_greenfield_completion_report",
    "raise_for_failed_greenfield_completion",
]
