"""Final governed writes for confirmed greenfield apply."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from odylith.runtime.common.value_coercion import dedupe_strings
from odylith.runtime.artifact_quality.generated_copy_quality import generated_public_copy_issues
from odylith.runtime.artifact_quality.greenfield_package_quality import greenfield_rendered_package_quality_findings
from odylith.runtime.artifact_quality.greenfield_package_repetition import (
    package_repetition_sample_matches_source_truth,
)
from odylith.runtime.artifact_quality.greenfield_rendered_artifacts import RenderedPackageQualityFinding
from odylith.runtime.domain_intelligence import greenfield_apply_prewrite
from odylith.runtime.domain_intelligence import greenfield_apply_diagrams
from odylith.runtime.domain_intelligence import greenfield_backlog_commit
from odylith.runtime.domain_intelligence import greenfield_component_commit
from odylith.runtime.domain_intelligence import greenfield_component_registry_scope
from odylith.runtime.domain_intelligence import greenfield_compiled_package_contract
from odylith.runtime.domain_intelligence import greenfield_compiled_readback
from odylith.runtime.domain_intelligence import greenfield_compiled_memory_readback
from odylith.runtime.domain_intelligence import greenfield_experience
from odylith.runtime.domain_intelligence import greenfield_programs
from odylith.runtime.domain_intelligence import greenfield_release_commit
from odylith.runtime.domain_intelligence import greenfield_source_casing
from odylith.runtime.domain_intelligence import greenfield_traceability
from odylith.runtime.domain_intelligence import greenfield_traceability_commit
from odylith.runtime.domain_intelligence.greenfield_apply_components import component_dependency_lookup_for
from odylith.runtime.domain_intelligence.greenfield_apply_components import first_release_component_rows
from odylith.runtime.domain_intelligence.greenfield_component_contract import rendered_component_spec_quality_issues
from odylith.runtime.domain_intelligence.greenfield_component_contract_targets import operator_component_spec_issues
from odylith.runtime.domain_intelligence.greenfield_post_confirm_completion import GreenfieldCompletionPackage
from odylith.runtime.domain_intelligence.greenfield_post_confirm_completion import build_greenfield_completion_report
from odylith.runtime.domain_intelligence.proposal_memory import record_compiled_greenfield_acceptance
from odylith.runtime.domain_intelligence.proposal_memory import record_greenfield_acceptance
from odylith.runtime.governance import owned_surface_refresh
from odylith.runtime.governance import release_planning_authoring
from odylith.runtime.project_intelligence import builder as project_intelligence_builder


def release_assignment_note(*, selector: str) -> str:
    return f"Target confirmed first-wave greenfield workstream(s) for release `{selector}`."


def write_greenfield_proposal(
    *,
    root: Path,
    proposal: Mapping[str, Any],
    release_selector: str,
    tribunal: Any,
    backlog_result: Mapping[str, Any],
    prewrite_package: GreenfieldCompletionPackage | None = None,
    completion_priority_write_policy: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Apply accepted Radar, Registry, Atlas, release, and memory records."""

    completion_quality_debt: list[str] = []
    source_text = "" if prewrite_package is not None else greenfield_source_casing.proposal_source_casing_text(proposal)
    if source_text:
        restored_proposal = greenfield_source_casing.restore_source_casing_in_public_copy(
            proposal,
            source_text=source_text,
        )
        if isinstance(restored_proposal, Mapping):
            proposal = restored_proposal
        restored_backlog_result = greenfield_source_casing.restore_source_casing_in_public_copy(
            backlog_result,
            source_text=source_text,
        )
        if isinstance(restored_backlog_result, Mapping):
            backlog_result = restored_backlog_result
    if prewrite_package is not None:
        greenfield_compiled_package_contract.require_complete_compiled_greenfield_package(
            prewrite_package,
            release_selector=release_selector,
        )
    validation_gate = _source_cased_validation_gate(tribunal, source_text=source_text)
    release_bootstrap = None
    release_targeting = None
    has_compiled_package = prewrite_package is not None
    rendered_atlas_sources = dict(prewrite_package.rendered_atlas_sources or {}) if prewrite_package else {}
    rendered_component_specs = dict(prewrite_package.rendered_component_specs or {}) if prewrite_package else {}
    atlas_review_date = greenfield_apply_diagrams.atlas_review_date(prewrite_package)
    for raw_path in backlog_result.get("stale_idea_files", []):
        path = Path(str(raw_path))
        if path.is_file():
            path.unlink()
    greenfield_apply_prewrite.remove_stale_workstream_artifacts(root=root, stale_ids=backlog_result.get("stale_idea_ids", []))
    if release_selector and prewrite_package is None:
        release_bootstrap = greenfield_apply_prewrite.ensure_release_target(repo_root=root, proposal=proposal, selector=release_selector)
    greenfield_backlog_commit.write_backlog_files(backlog_result, repo_root=root)
    if release_selector and prewrite_package is not None:
        release_bootstrap = greenfield_release_commit.materialize_compiled_release_target(repo_root=root, release_selector=release_selector, release_target_result=prewrite_package.release_target_result or {})
    if prewrite_package is not None and isinstance(prewrite_package.program_result, Mapping):
        program_result = greenfield_programs.materialize_compiled_greenfield_program(
            repo_root=root,
            backlog_result=backlog_result,
            program_result=prewrite_package.program_result,
        )
    else:
        program_result = greenfield_programs.create_greenfield_program(
            repo_root=root,
            proposal=proposal,
            backlog_result=backlog_result,
        )
    first_release_workstreams = (
        [str(item).strip().upper() for item in prewrite_package.release_workstream_ids if str(item).strip()]
        if prewrite_package is not None and prewrite_package.release_workstream_ids
        else greenfield_programs.first_release_workstream_ids(
            proposal=proposal,
            created_backlog=backlog_result["created"],
            program_result=program_result,
        )
    )
    if release_selector and prewrite_package is not None:
        release_targeting = greenfield_release_commit.materialize_compiled_release_assignment(repo_root=root, release_assignment_result=prewrite_package.release_assignment_result or {})
    elif release_selector:
        release_targeting = release_planning_authoring.add_workstreams_to_release(
            repo_root=root,
            workstream_ids=first_release_workstreams,
            selector=release_selector,
            note=release_assignment_note(selector=release_selector),
            idea_specs=backlog_result["_candidate_idea_specs"],
            allow_existing=True,
            dry_run=False,
        )
    if isinstance(release_targeting, dict) and isinstance(release_targeting.get("release"), Mapping):
        release_targeting.setdefault("release_id", str(release_targeting["release"].get("release_id", "")).strip())
    diagram_rows = [row for row in proposal.get("diagrams", []) if isinstance(row, Mapping)]
    diagram_ids = (
        greenfield_apply_diagrams.compiled_atlas_diagram_ids(prewrite_package, expected_count=len(diagram_rows))
        if has_compiled_package
        else greenfield_apply_diagrams.allocated_diagram_ids(root, len(diagram_rows), rows=diagram_rows)
    )
    traceability_plan = (
        greenfield_traceability_commit.compiled_traceability_plan(getattr(prewrite_package, "traceability_plan", None))
        if has_compiled_package
        else greenfield_traceability.build_traceability_plan(
            proposal=proposal,
            created_backlog=backlog_result["created"],
            diagram_ids=diagram_ids,
        )
    )
    if has_compiled_package:
        traceability_plan = greenfield_traceability_commit.rebase_compiled_traceability_plan(
            traceability_plan,
            backlog_result=backlog_result,
        )
    diagram_write = greenfield_apply_diagrams.materialize_apply_diagrams(
        root=root,
        rows=diagram_rows,
        diagram_ids=diagram_ids,
        traceability_plan=traceability_plan,
        rendered_atlas_sources=rendered_atlas_sources,
        review_date=atlas_review_date,
        require_compiled_sources=has_compiled_package,
        compiled_catalog_rows=prewrite_package.atlas_catalog_rows if prewrite_package is not None else (),
    )
    diagrams_created = list(diagram_write.diagram_ids)
    atlas_scaffold_logs = list(diagram_write.scaffold_logs)
    touched_backlog_paths = (
        greenfield_backlog_commit.compiled_backlog_traceability_paths(repo_root=root, backlog_result=backlog_result)
        if has_compiled_package
        else greenfield_traceability.apply_backlog_traceability(
            repo_root=root,
            proposal=proposal,
            plan=traceability_plan,
        )
    )
    if has_compiled_package:
        greenfield_compiled_readback.raise_for_compiled_backlog_and_atlas_readback(root=root, package=prewrite_package)
    component_handoffs = greenfield_component_commit.precompiled_component_handoffs(prewrite_package)
    if not component_handoffs:
        component_handoffs = greenfield_experience.build_component_handoffs(
            proposal=proposal,
            backlog_result=backlog_result,
            first_release_workstreams=first_release_workstreams,
            program_result=program_result,
            traceability_plan=traceability_plan,
            release_selector=release_selector,
        )
    component_diagram_scope = (
        {}
        if has_compiled_package
        else greenfield_component_registry_scope.build_component_diagram_scope(
            rows=diagram_rows,
            diagram_ids=diagram_ids,
        )
    )

    component_rows = first_release_component_rows(proposal)
    compiled_component_previews = greenfield_component_commit.compiled_component_previews_for_rows(
        prewrite_package,
        component_rows,
    )
    component_dependency_lookup = {} if has_compiled_package else component_dependency_lookup_for(component_rows)
    components_created: list[dict[str, Any]] = []
    for row in component_rows:
        if not isinstance(row, Mapping):
            continue
        key = greenfield_traceability.component_key(row)
        if has_compiled_package:
            preview = compiled_component_previews.get(key)
            if not preview:
                raise ValueError(f"compiled component registry preview missing for {key or '<unknown component>'}")
            created = greenfield_component_commit.materialize_compiled_component_from_preview(
                root=root,
                preview=preview,
                rendered_component_specs=rendered_component_specs,
            )
        else:
            handoff = component_handoffs.get(key, {})
            authoring_input = greenfield_component_commit.legacy_component_authoring_input(
                row=row,
                handoff=handoff,
                traceability_plan=traceability_plan,
                component_diagram_scope=component_diagram_scope,
                component_dependency_lookup=component_dependency_lookup,
                proposal=proposal,
            )
            created = greenfield_component_commit.register_component_from_authoring_input(
                root=root,
                authoring_input=authoring_input,
            )
            greenfield_component_commit.write_repaired_component_spec(
                root=root,
                created=created.as_dict(),
                rendered_component_specs=rendered_component_specs,
            )
        components_created.append(created.as_dict())
    if has_compiled_package:
        greenfield_component_commit.raise_for_compiled_component_registry_readback(
            root=root,
            previews=compiled_component_previews,
            rendered_component_specs=rendered_component_specs,
        )
    if not has_compiled_package:
        _raise_for_component_spec_quality(
            root=root,
            proposal=proposal,
            components=components_created,
            completion_priority_write_policy=completion_priority_write_policy,
            completion_quality_debt=completion_quality_debt,
        )

    release_id = "none"
    if isinstance(release_targeting, Mapping):
        release_id = str(release_targeting.get("release_id", "")).strip() or "none"
    if prewrite_package is not None and isinstance(prewrite_package.next_steps_preview, Mapping):
        next_steps = dict(prewrite_package.next_steps_preview)
    else:
        next_steps = greenfield_experience.build_next_steps(
            proposal=proposal,
            backlog_result=backlog_result,
            first_release_workstreams=first_release_workstreams,
            program_result=program_result,
            release_selector=release_selector,
        )
    if source_text and not (prewrite_package is not None and isinstance(prewrite_package.next_steps_preview, Mapping)):
        restored_next_steps = greenfield_source_casing.restore_source_casing_in_public_copy(
            next_steps,
            source_text=source_text,
        )
        if isinstance(restored_next_steps, Mapping):
            next_steps = restored_next_steps
    if not has_compiled_package:
        _raise_for_final_next_steps_quality(
            next_steps,
            completion_priority_write_policy=completion_priority_write_policy,
            completion_quality_debt=completion_quality_debt,
        )
    if _has_compiled_memory_package(prewrite_package):
        memory_record = record_compiled_greenfield_acceptance(
            repo_root=root,
            accepted_project_preview=prewrite_package.accepted_project_preview or {},
            project_brief_record_text=prewrite_package.project_brief_record_text,
            compass_memory_preview=prewrite_package.compass_memory_preview or {},
        )
        greenfield_compiled_memory_readback.raise_for_compiled_memory_readback(
            root=root,
            prewrite_package=prewrite_package,
            memory_record=memory_record,
        )
    else:
        memory_record = record_greenfield_acceptance(
            repo_root=root,
            proposal=proposal,
            backlog_items=backlog_result["created"],
            component_items=components_created,
            diagram_ids=diagrams_created,
            release_selector=release_selector,
            release_id=release_id,
            validation_gate=validation_gate,
            source_launch_context=next_steps,
        )
    if not has_compiled_package:
        _raise_for_final_package_quality(
            root=root,
            proposal=proposal,
            release_selector=release_selector,
            tribunal=tribunal,
            backlog_result=backlog_result,
            program_result=program_result,
            release_bootstrap=release_bootstrap,
            release_targeting=release_targeting,
            first_release_workstreams=first_release_workstreams,
            component_rows=components_created,
            diagram_rows=diagram_rows,
            diagram_ids=diagram_ids,
            atlas_review_date=atlas_review_date,
            memory_record=memory_record,
            next_steps=next_steps,
            validation_gate=validation_gate,
            completion_priority_write_policy=completion_priority_write_policy,
            completion_quality_debt=completion_quality_debt,
        )
    if completion_quality_debt:
        _persist_completion_quality_debt(root=root, debt=completion_quality_debt)
    dashboard_refresh = _refresh_greenfield_dashboard(repo_root=root)
    dashboard_refresh["rendered_surface_custody"] = greenfield_apply_diagrams.raise_for_greenfield_rendered_surface_custody(
        repo_root=root,
        diagram_ids=diagrams_created,
    )
    dashboard_refresh["managed_brand_assets"] = {
        "status": "passed",
        "seeded_count": len(prewrite_package.brand_asset_writes or {}) if prewrite_package else 0,
    }

    return {
        "mode": "applied",
        "validation_gate": validation_gate,
        "backlog": backlog_result["created"],
        "components": components_created,
        "diagrams": diagrams_created,
        "program": program_result,
        "backlog_topology": touched_backlog_paths,
        "atlas_scaffold_logs": atlas_scaffold_logs,
        "memory": memory_record,
        "dashboard_refresh": dashboard_refresh,
        "next_steps": next_steps,
        "prewrite_safety": dict(prewrite_package.prewrite_safety_preview or {}) if prewrite_package else {},
        "release_bootstrap": release_bootstrap or {"created": False, "release": {}},
        "release_target": release_targeting or {"selector": release_selector, "release_id": "none", "events": []},
        "completion_priority_quality_debt": completion_quality_debt,
    }


_GREENFIELD_VISIBLE_SURFACES = ("radar", "registry", "atlas", "compass", "tooling_shell")


def _source_cased_validation_gate(tribunal: Any, *, source_text: str) -> dict[str, Any]:
    """Return the validation gate using the same visible source-casing custody as durable memory."""

    if isinstance(tribunal, Mapping):
        gate = dict(tribunal)
    else:
        gate = tribunal.to_dict() if hasattr(tribunal, "to_dict") else {}
    if not isinstance(gate, Mapping):
        return {}
    if not source_text:
        return dict(gate)
    restored = greenfield_source_casing.restore_source_casing_in_public_copy(
        gate,
        source_text=source_text,
    )
    return dict(restored) if isinstance(restored, Mapping) else dict(gate)


def _refresh_greenfield_dashboard(*, repo_root: Path) -> dict[str, Any]:
    view = owned_surface_refresh.dashboard_handoff(surface="project")
    owned_surface_refresh.raise_for_failed_refreshes(
        repo_root=Path(repo_root).resolve(),
        surfaces=_GREENFIELD_VISIBLE_SURFACES,
        operation_label="Greenfield apply dashboard visibility",
    )
    return {
        "status": "passed",
        "surfaces": list(_GREENFIELD_VISIBLE_SURFACES),
        "view": view,
    }


def _has_compiled_memory_package(prewrite_package: GreenfieldCompletionPackage | None) -> bool:
    return bool(
        prewrite_package is not None
        and isinstance(prewrite_package.accepted_project_preview, Mapping)
        and str(prewrite_package.project_brief_record_text or "").strip()
        and isinstance(prewrite_package.compass_memory_preview, Mapping)
    )


def _raise_for_final_package_quality(
    *,
    root: Path,
    proposal: Mapping[str, Any],
    release_selector: str,
    tribunal: Any,
    backlog_result: Mapping[str, Any],
    program_result: Mapping[str, Any],
    release_bootstrap: Mapping[str, Any] | None,
    release_targeting: Mapping[str, Any] | None,
    first_release_workstreams: Sequence[str],
    component_rows: Sequence[Mapping[str, Any]],
    diagram_rows: Sequence[Mapping[str, Any]],
    diagram_ids: Sequence[str],
    atlas_review_date: str,
    memory_record: Mapping[str, Any],
    next_steps: Mapping[str, Any],
    validation_gate: Mapping[str, Any] | None = None,
    completion_priority_write_policy: Mapping[str, Any] | None = None,
    completion_quality_debt: list[str] | None = None,
) -> None:
    accepted_project_preview = _read_json_mapping(root / "odylith/runtime/source/accepted-project.v1.json")
    project_dashboard_preview = project_intelligence_builder.build_project_intelligence_payload(
        repo_root=root,
        shell_payload={},
    )
    package = GreenfieldCompletionPackage(
        proposal=proposal,
        release_selector=release_selector,
        rendered_component_specs=_actual_component_specs(root=root, components=component_rows),
        rendered_atlas_sources=greenfield_apply_diagrams.actual_atlas_sources(root=root, rows=diagram_rows),
        atlas_review_date=atlas_review_date,
        atlas_diagram_ids=tuple(diagram_ids),
        atlas_catalog_rows=(),
        component_registry_preview=tuple(dict(row) for row in component_rows),
        project_brief_preview=proposal.get("project_brief") if isinstance(proposal.get("project_brief"), Mapping) else {},
        project_brief_record_text=_read_text(root / "odylith/runtime/source/project-brief.v1.md"),
        tribunal_preview=dict(validation_gate or tribunal.to_dict()),
        accepted_project_preview=accepted_project_preview,
        project_dashboard_preview=project_dashboard_preview,
        compass_memory_preview=memory_record.get("event") if isinstance(memory_record.get("event"), Mapping) else {},
        next_steps_preview=next_steps,
        backlog_result=backlog_result,
        program_result=program_result,
        release_target_result=release_bootstrap or {"created": False, "release": {}},
        release_assignment_result=release_targeting or {"selector": release_selector, "release_id": "none", "events": []},
        release_workstream_ids=tuple(str(item) for item in first_release_workstreams if str(item).strip()),
    )
    completion = build_greenfield_completion_report(
        proposal,
        release_selector=release_selector,
        rendered_component_specs=package.rendered_component_specs,
        tribunal_preview=package.tribunal_preview,
    )
    package_findings = greenfield_rendered_package_quality_findings(package)
    package_debt_messages = [
        finding.message
        for finding in package_findings
        if _structured_package_repetition_debt_allowed(finding, package=package)
    ]
    package_blocker_messages = [
        finding.message
        for finding in package_findings
        if finding.message not in set(package_debt_messages)
    ]
    issues = dedupe_strings(
        [
            *completion.issues,
            *package_blocker_messages,
            *generated_public_copy_issues("accepted-project final memory", accepted_project_preview),
            *generated_public_copy_issues("Compass final memory", package.compass_memory_preview),
        ]
    )
    if issues:
        _record_or_raise_completion_quality_debt(
            issues,
            error_prefix="greenfield post-confirm final write quality failed",
            debt_prefix="final write quality",
            completion_priority_write_policy=completion_priority_write_policy,
            completion_quality_debt=completion_quality_debt,
            projection_copy_debt_allowed=True,
        )
    if package_debt_messages:
        _record_or_raise_structured_completion_quality_debt(
            package_debt_messages,
            error_prefix="greenfield post-confirm final write quality failed",
            debt_prefix="final write quality",
            completion_priority_write_policy=completion_priority_write_policy,
            completion_quality_debt=completion_quality_debt,
        )


def _raise_for_final_next_steps_quality(
    next_steps: Mapping[str, Any],
    *,
    completion_priority_write_policy: Mapping[str, Any] | None = None,
    completion_quality_debt: list[str] | None = None,
) -> None:
    issues = dedupe_strings(
        generated_public_copy_issues("operator next-steps final memory", next_steps)
    )
    if issues:
        _record_or_raise_completion_quality_debt(
            issues,
            error_prefix="greenfield post-confirm final next steps quality failed",
            debt_prefix="final next steps quality",
            completion_priority_write_policy=completion_priority_write_policy,
            completion_quality_debt=completion_quality_debt,
            projection_copy_debt_allowed=True,
        )


def _actual_component_specs(*, root: Path, components: Sequence[Mapping[str, Any]]) -> dict[str, str]:
    specs: dict[str, str] = {}
    for component in components:
        label = str(component.get("label", "")).strip()
        spec_path = Path(str(component.get("spec_path", "")))
        if not label:
            continue
        if not spec_path.is_absolute():
            spec_path = root / spec_path
        if spec_path.is_file():
            specs[label] = spec_path.read_text(encoding="utf-8")
    return specs


def _read_json_mapping(path: Path) -> Mapping[str, Any]:
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, Mapping) else {}


def _read_text(path: Path) -> str:
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8")


def _raise_for_component_spec_quality(
    *,
    root: Path,
    proposal: Mapping[str, Any],
    components: Sequence[Mapping[str, Any]],
    completion_priority_write_policy: Mapping[str, Any] | None = None,
    completion_quality_debt: list[str] | None = None,
) -> None:
    specs: dict[str, str] = {}
    for component in components:
        spec_path = Path(str(component.get("spec_path", "")))
        if not spec_path.is_absolute():
            spec_path = root / spec_path
        label = str(component.get("label", "") or component.get("component_id", "") or spec_path.parent.name).strip()
        if spec_path.is_file() and label:
            specs[label] = spec_path.read_text(encoding="utf-8")
    if not specs:
        return
    intent = proposal.get("intent") if isinstance(proposal.get("intent"), Mapping) else {}
    title = str(intent.get("title", "")).strip()
    issues = rendered_component_spec_quality_issues(specs, project_title=title)
    if issues:
        _record_or_raise_completion_quality_debt(
            operator_component_spec_issues(issues),
            error_prefix="greenfield component spec quality gate failed",
            debt_prefix="component spec quality",
            completion_priority_write_policy=completion_priority_write_policy,
            completion_quality_debt=completion_quality_debt,
            projection_copy_debt_allowed=True,
        )


def _record_or_raise_completion_quality_debt(
    issues: Sequence[str],
    *,
    error_prefix: str,
    debt_prefix: str,
    completion_priority_write_policy: Mapping[str, Any] | None,
    completion_quality_debt: list[str] | None,
    projection_copy_debt_allowed: bool = False,
) -> None:
    if not issues:
        return
    issue_rows = dedupe_strings(str(issue) for issue in issues if str(issue).strip())
    if not issue_rows:
        return
    if _completion_priority_write_allowed(
        completion_priority_write_policy,
        debt_prefix=debt_prefix,
        issue_rows=issue_rows,
        projection_copy_debt_allowed=projection_copy_debt_allowed,
    ):
        if completion_quality_debt is not None:
            completion_quality_debt.extend(f"{debt_prefix}: {issue}" for issue in issue_rows)
        return
    detail = "\n".join(f"- {issue}" for issue in issue_rows)
    raise ValueError(f"{error_prefix} with {len(issue_rows)} issue(s):\n{detail}")


def _record_or_raise_structured_completion_quality_debt(
    issues: Sequence[str],
    *,
    error_prefix: str,
    debt_prefix: str,
    completion_priority_write_policy: Mapping[str, Any] | None,
    completion_quality_debt: list[str] | None,
) -> None:
    issue_rows = dedupe_strings(str(issue) for issue in issues if str(issue).strip())
    if not issue_rows:
        return
    if _completion_priority_policy_base_allowed(completion_priority_write_policy):
        if completion_quality_debt is not None:
            completion_quality_debt.extend(f"{debt_prefix}: {issue}" for issue in issue_rows)
        return
    detail = "\n".join(f"- {issue}" for issue in issue_rows)
    raise ValueError(f"{error_prefix} with {len(issue_rows)} issue(s):\n{detail}")


def _completion_priority_write_allowed(
    policy: Mapping[str, Any] | None,
    *,
    debt_prefix: str,
    issue_rows: Sequence[str],
    projection_copy_debt_allowed: bool,
) -> bool:
    if not _completion_priority_policy_base_allowed(policy):
        return False
    if not projection_copy_debt_allowed:
        return False
    return all(
        _late_projection_copy_debt_issue(debt_prefix=debt_prefix, issue=issue)
        or _completion_priority_policy_covers_late_issue(policy, issue)
        for issue in issue_rows
    )


def _completion_priority_policy_base_allowed(policy: Mapping[str, Any] | None) -> bool:
    return bool(
        isinstance(policy, Mapping)
        and str(policy.get("status", "")).strip() == "write_allowed_with_projection_quality_debt"
        and int(policy.get("hard_blocker_count", 1) or 0) == 0
    )


def _structured_package_repetition_debt_allowed(
    finding: RenderedPackageQualityFinding,
    *,
    package: GreenfieldCompletionPackage,
) -> bool:
    if finding.code != "package_repetition":
        return False
    if finding.source != "package_repetition_quality":
        return False
    if finding.severity not in {"low", "medium"}:
        return False
    if not finding.projection_id or finding.projection_id in {"release", "review_report"}:
        return False
    if finding.surface in {"release", "semantic_model", "tribunal"}:
        return False
    if not finding.semantic_node_id.startswith("ArtifactPlanIR."):
        return False
    if package_repetition_sample_matches_source_truth(package, finding.sample):
        return False
    return bool(finding.owner == "typed_package_artifact_gate" or finding.owner.endswith("_renderer"))


def _late_projection_copy_debt_issue(*, debt_prefix: str, issue: str) -> bool:
    text = str(issue or "").casefold()
    prefix = str(debt_prefix or "").casefold()
    if any(
        marker in text
        for marker in (
            "missing proof contract",
            "project implementation prompt",
            "release package",
            "semantic",
            "source token",
            "domain term",
            "accepted assumption",
        )
    ):
        return False
    if prefix == "final next steps quality":
        return _mechanical_projection_copy_issue(text)
    if prefix in {"component spec quality", "final write quality"}:
        return _mechanical_projection_copy_issue(text)
    return False


def _mechanical_projection_copy_issue(text: str) -> bool:
    if any(
        marker in text
        for marker in (
            "adjacent duplicate word",
            "repeats adjacent word",
            "clipped or dangling",
            "clipped action phrase",
            "clipped boundary phrase",
            "malformed ownership verb pair",
            "malformed connector sequence",
            "sentence-fragment drift",
            "invalid verb inflection",
            "doubled sentence punctuation",
            "comma-spliced capitalized clause",
            "repeats the same visible result",
        )
    ):
        return True
    return _mechanical_generated_prose_issue(text)


def _completion_priority_policy_covers_late_issue(policy: Mapping[str, Any] | None, issue: str) -> bool:
    if not isinstance(policy, Mapping):
        return False
    codes = {str(code or "").strip() for code in policy.get("debt_issue_codes", []) if str(code or "").strip()}
    text = str(issue or "").casefold()
    return "component_contract_quality" in codes and "finite/finite ownership verb drift" in text


_MECHANICAL_GENERATED_PROSE_LABELS = (
    "malformed ownership verb pair",
    "malformed ownership sentence",
    "duplicated evidence word",
    "dangling close-parenthesis token",
    "missing sentence boundary before proof obligation",
)


def _mechanical_generated_prose_issue(text: str) -> bool:
    prefix = "generated prose uses "
    if not text.startswith(prefix):
        return False
    return any(text.startswith(f"{prefix}{label}") for label in _MECHANICAL_GENERATED_PROSE_LABELS)


def _persist_completion_quality_debt(*, root: Path, debt: Sequence[str]) -> None:
    rows = dedupe_strings(str(item) for item in debt if str(item).strip())
    if not rows:
        return
    path = root / "odylith/runtime/source/accepted-project.v1.json"
    payload = dict(_read_json_mapping(path))
    if not payload:
        return
    ledger = {
        "status": "recorded",
        "guard": "typed_noncritical_projection_debt_only",
        "count": len(rows),
        "items": rows,
    }
    payload["completion_priority_quality_debt"] = ledger
    source_launch = payload.get("source_launch")
    if isinstance(source_launch, Mapping):
        source_launch_payload = dict(source_launch)
    else:
        source_launch_payload = {}
    source_launch_payload["completion_priority_quality_debt"] = ledger
    payload["source_launch"] = source_launch_payload
    path.write_text(f"{json.dumps(payload, indent=2, sort_keys=True)}\n", encoding="utf-8")


def completion_priority_write_policy_from_manifest(manifest: Mapping[str, Any]) -> Mapping[str, Any] | None:
    priority = manifest.get("completion_priority") if isinstance(manifest.get("completion_priority"), Mapping) else None
    if priority is not None:
        return priority
    if str(manifest.get("status", "")).strip() != "passed":
        return None
    return {
        "status": "write_allowed_with_projection_quality_debt",
        "policy": (
            "post-confirm governed record creation takes priority when a final persisted-projection "
            "quality gate finds non-critical debt after a clean prewrite manifest"
        ),
        "original_stop_reason": str(manifest.get("stop_reason", "")).strip() or "passed",
        "debt_issue_count": 0,
        "debt_issue_codes": [],
        "hard_blocker_count": 0,
    }


__all__ = [
    "completion_priority_write_policy_from_manifest",
    "release_assignment_note",
    "write_greenfield_proposal",
]
