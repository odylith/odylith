"""Scoped prewrite package refresh for typed greenfield projection repair."""

from __future__ import annotations

from collections.abc import Mapping
from collections.abc import Sequence
from dataclasses import replace
from pathlib import Path
from typing import Any

from odylith.runtime.domain_intelligence import greenfield_apply_components
from odylith.runtime.domain_intelligence import greenfield_apply_diagrams
from odylith.runtime.domain_intelligence import greenfield_apply_prewrite
from odylith.runtime.domain_intelligence import greenfield_experience
from odylith.runtime.domain_intelligence import greenfield_programs
from odylith.runtime.domain_intelligence import greenfield_source_casing
from odylith.runtime.governance import release_planning_authoring


def rerender_prewrite_package_projections(
    *,
    root: Path,
    previous_prewrite_build: greenfield_apply_prewrite.GreenfieldPrewriteBuild,
    proposal: Mapping[str, Any],
    release_selector: str,
    validation_gate: Mapping[str, Any],
    projections: Sequence[str],
    release_assignment_note: str,
) -> greenfield_apply_prewrite.GreenfieldPrewriteBuild:
    """Refresh package previews for an explicit projection scope."""

    scope = {str(projection).strip() for projection in projections if str(projection).strip()}
    if not scope:
        return previous_prewrite_build
    target_root = Path(root).expanduser().resolve()
    package = previous_prewrite_build.package
    backlog_result = package.backlog_result or previous_prewrite_build.backlog_result
    program_result = package.program_result or {}
    package_proposal = greenfield_apply_prewrite.proposal_with_component_brief_gate(proposal)
    component_preview: Sequence[Mapping[str, Any]] = package.component_registry_preview
    release_target_result = package.release_target_result
    release_assignment_result = package.release_assignment_result
    release_workstream_ids = package.release_workstream_ids
    prewrite_safety_preview = package.prewrite_safety_preview
    source_text = greenfield_source_casing.proposal_source_casing_text(package_proposal)
    if source_text:
        restored_proposal = greenfield_source_casing.restore_source_casing_in_public_copy(
            package_proposal,
            source_text=source_text,
        )
        if isinstance(restored_proposal, Mapping):
            package_proposal = restored_proposal
    updates: dict[str, Any] = {"proposal": package_proposal, "tribunal_preview": validation_gate}

    if "atlas" in scope:
        updates["rendered_atlas_sources"] = greenfield_apply_diagrams.render_prewrite_atlas_sources(package_proposal)

    if "release" in scope and release_selector:
        release_workstream_ids = tuple(
            greenfield_programs.first_release_workstream_ids(
                proposal=package_proposal,
                created_backlog=backlog_result.get("created", ()),
                program_result=program_result,
            )
        )
        release_target_result = greenfield_apply_prewrite.ensure_release_target(
            repo_root=target_root,
            proposal=package_proposal,
            selector=release_selector,
            dry_run=True,
        )
        release_assignment_result = release_planning_authoring.add_workstreams_to_release(
            repo_root=target_root,
            workstream_ids=release_workstream_ids,
            selector=release_selector,
            note=release_assignment_note,
            idea_specs=backlog_result.get("_candidate_idea_specs", {}),
            allow_existing=True,
            dry_run=True,
        )
        updates["release_target_result"] = release_target_result
        updates["release_assignment_result"] = release_assignment_result
        updates["release_workstream_ids"] = release_workstream_ids
        prewrite_safety_preview = greenfield_apply_prewrite.prewrite_safety_evidence(
            validation_gate=validation_gate,
            program_result=program_result,
            release_target_result=release_target_result,
            release_assignment_result=release_assignment_result,
            release_selector=release_selector,
        )
        updates["prewrite_safety_preview"] = prewrite_safety_preview

    if "registry" in scope:
        component_preview = greenfield_apply_components.preview_prewrite_components(
            root=target_root,
            proposal=package_proposal,
            release_selector=release_selector,
            backlog_result=backlog_result,
            program_result=program_result,
        )
        updates["rendered_component_specs"] = greenfield_apply_components.render_prewrite_component_specs(
            root=target_root,
            proposal=package_proposal,
            release_selector=release_selector,
            backlog_result=backlog_result,
            program_result=program_result,
        )
        updates["component_registry_preview"] = tuple(component_preview)

    if "project_brief" in scope or "registry" in scope:
        updates["project_brief_preview"] = (
            package_proposal.get("project_brief") if isinstance(package_proposal.get("project_brief"), Mapping) else {}
        )

    next_steps_context = (
        greenfield_experience.build_next_steps(
            proposal=package_proposal,
            backlog_result=backlog_result,
            first_release_workstreams=release_workstream_ids,
            program_result=program_result,
            release_selector=release_selector,
        )
        if {"accepted_project", "next_steps", "project_dashboard"} & scope
        else None
    )

    if "accepted_project" in scope:
        updates["accepted_project_preview"] = greenfield_apply_prewrite.preview_accepted_project_memory(
            root=target_root,
            proposal=package_proposal,
            backlog_result=backlog_result,
            component_items=component_preview,
            release_selector=release_selector,
            release_target_result=release_target_result,
            release_assignment_result=release_assignment_result,
            validation_gate=validation_gate,
            source_launch_context=next_steps_context if isinstance(next_steps_context, Mapping) else None,
        )

    if "next_steps" in scope:
        updates["next_steps_preview"] = next_steps_context if isinstance(next_steps_context, Mapping) else {}

    if "project_dashboard" in scope:
        accepted_project_preview = (
            updates.get("accepted_project_preview")
            if isinstance(updates.get("accepted_project_preview"), Mapping)
            else package.accepted_project_preview
            if isinstance(package.accepted_project_preview, Mapping)
            else {}
        )
        source_launch_context = (
            next_steps_context
            if isinstance(next_steps_context, Mapping)
            else updates.get("next_steps_preview")
            if isinstance(updates.get("next_steps_preview"), Mapping)
            else package.next_steps_preview
            if isinstance(package.next_steps_preview, Mapping)
            else {}
        )
        updates["project_dashboard_preview"] = greenfield_apply_prewrite.preview_project_dashboard_payload(
            root=target_root,
            proposal=package_proposal,
            accepted_project_preview=accepted_project_preview,
            source_launch_context=source_launch_context,
        )

    if "compass" in scope:
        updates["compass_memory_preview"] = greenfield_apply_prewrite.preview_compass_acceptance_event(
            root=target_root,
            proposal=package_proposal,
            backlog_result=backlog_result,
            component_items=component_preview,
            release_selector=release_selector,
            release_target_result=release_target_result,
            release_assignment_result=release_assignment_result,
        )

    restored_package = greenfield_source_casing.package_with_source_casing(replace(package, **updates))
    return replace(
        previous_prewrite_build,
        package=restored_package,
        backlog_result=restored_package.backlog_result or backlog_result,
    )


__all__ = ["rerender_prewrite_package_projections"]
