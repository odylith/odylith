"""Structural implementation handoffs for model-authored Greenfield intent.

The model-authoring boundary has already selected and source-bound canonical
meaning. This module copies those typed facts into coding-readiness and
component handoffs without parsing, clipping, repairing, or reclassifying prose.
"""

from __future__ import annotations

from typing import Any, Mapping, Protocol, Sequence

from odylith.runtime.domain_intelligence.greenfield_authored_semantics import (
    GreenfieldAuthoredSemanticsError,
    authored_projection_relations,
)
from odylith.runtime.domain_intelligence.greenfield_handoff_contract import (
    build_coding_readiness_contract,
    render_coding_readiness_gates,
)
from odylith.runtime.domain_intelligence.greenfield_rows import mapping_rows


class _TraceabilityPlan(Protocol):
    component_workstreams: Mapping[str, Sequence[str]]


def row_text_tuple(row: Mapping[str, Any], *keys: str) -> tuple[str, ...]:
    """Return exact string rows from the first populated typed field."""

    for key in keys:
        value = row.get(key)
        if isinstance(value, str):
            values = (value,) if value.strip() else ()
        elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
            values = tuple(item for item in value if isinstance(item, str) and item.strip())
        else:
            values = ()
        if values:
            return values
    return ()


def _require_authored_relations(proposal: Mapping[str, Any]) -> tuple[dict[str, Any], ...]:
    relations = authored_projection_relations(proposal)
    if not relations:
        raise GreenfieldAuthoredSemanticsError(
            "Greenfield implementation handoff requires model-authored typed intent"
        )
    return relations


def build_next_steps(
    *,
    proposal: Mapping[str, Any],
    backlog_result: Mapping[str, Any],
    first_release_workstreams: Sequence[str],
    release_selector: str,
) -> dict[str, Any]:
    """Project verified authored fields into the completion handoff without reinterpretation."""

    _require_authored_relations(proposal)
    created = mapping_rows(backlog_result.get("created"))
    by_id = _created_by_id(created)
    project_id = next(iter(by_id), "")
    if not project_id:
        raise GreenfieldAuthoredSemanticsError(
            "Greenfield implementation handoff is missing its created project workstream"
        )
    candidate_ids = _candidate_start_ids(
        first_release_workstreams=first_release_workstreams,
        project_id=project_id,
    )
    start_id = candidate_ids[0] if candidate_ids else project_id
    if start_id not in by_id:
        raise GreenfieldAuthoredSemanticsError(
            "Greenfield implementation handoff references an unknown first-release workstream"
        )
    project_row = by_id.get(project_id, {})
    start_row = by_id.get(start_id, {})
    proposal_row = _proposal_row_for_created_id(
        proposal=proposal,
        created=created,
        created_id=start_id,
    )
    if not proposal_row:
        raise GreenfieldAuthoredSemanticsError(
            "Greenfield implementation handoff is missing its typed backlog projection"
        )
    intent = proposal.get("intent") if isinstance(proposal.get("intent"), Mapping) else {}
    project_brief = (
        proposal.get("project_brief")
        if isinstance(proposal.get("project_brief"), Mapping)
        else {}
    )
    project_title = str(project_row.get("title") or intent.get("title") or "").strip()
    start_title = str(start_row.get("title") or project_title).strip()
    first_path_value = intent.get("first_path")
    first_path = first_path_value if isinstance(first_path_value, str) else ""
    proof_boundary_value = intent.get("proof_boundary")
    proof_boundary = proof_boundary_value if isinstance(proof_boundary_value, str) else ""
    validation_metrics = list(
        dict.fromkeys(
            [
                *row_text_tuple(intent, "success_metrics"),
                *row_text_tuple(proposal_row, "success_metrics"),
            ]
        )
    )
    validation_items = list(dict.fromkeys([proof_boundary, *validation_metrics]))
    customization_options = list(row_text_tuple(project_brief, "customization_options"))
    readiness_contract = build_coding_readiness_contract(
        workstream_id=start_id,
        workstream_title=start_title,
        release_selector=release_selector,
        accepted_first_path=first_path,
        proof_boundary=proof_boundary,
        evidence_requirements=row_text_tuple(intent, "evidence_requirements"),
        operational_constraints=row_text_tuple(intent, "operational_constraints"),
        non_goals=row_text_tuple(intent, "non_goals"),
    )
    readiness_gates = render_coding_readiness_gates(readiness_contract)
    return {
        "project_workstream_id": project_id,
        "project_workstream_title": project_title,
        "start_workstream_id": start_id,
        "start_workstream_title": start_title,
        "release_selector": release_selector,
        "project_first_prompt": _project_first_prompt(
            project_id=project_id,
            project_title=project_title,
            start_id=start_id,
            start_title=start_title,
        ),
        "implementation_prompt": _implementation_prompt(
            start_id=start_id,
            title=start_title,
            first_path=first_path,
            release_requirements=proof_boundary,
        ),
        "customization_options": customization_options,
        "coding_readiness_gates": readiness_gates,
        "coding_readiness_contract": readiness_contract,
        "validation_gates": validation_items,
        "operator_sequence": [
            "Do not start source edits from this closeout; treat the applied records as the project review board.",
            (
                f"Open the project dashboard for `{project_id or start_id}` and review the project brief, "
                "direction choices, non-goals, diagrams, and proof gates."
            ),
            (
                f"Open `{start_id}` and verify its first-release scope and release "
                f"`{release_selector or '0.0.1'}` match the accepted project shape."
            ),
            (
                "Answer or explicitly accept the choices that materially change runtime, data posture, "
                "architecture, validation, release ambition, or first user."
            ),
            (
                f"Only after the coding-readiness gates are accepted, open `{start_id}` and author the first "
                "technical plan before source writes."
            ),
        ],
        "verification_commands": verification_commands(start_id),
    }


def build_component_handoffs(
    *,
    proposal: Mapping[str, Any],
    backlog_result: Mapping[str, Any],
    first_release_workstreams: Sequence[str],
    traceability_plan: _TraceabilityPlan,
    release_selector: str,
) -> dict[str, dict[str, Any]]:
    """Bind each typed component to its exact authored workstream and proof facts."""

    _require_authored_relations(proposal)
    created = mapping_rows(backlog_result.get("created"))
    by_id = _created_by_id(created)
    project_id = next(iter(by_id), "")
    first_release_ids = [
        str(item).strip().upper()
        for item in first_release_workstreams
        if str(item).strip()
    ]
    handoffs: dict[str, dict[str, Any]] = {}
    components = mapping_rows(proposal.get("components"))
    if not components:
        raise GreenfieldAuthoredSemanticsError(
            "Greenfield component handoff is missing its typed components"
        )
    project_context = _project_context(proposal)
    intent = proposal.get("intent") if isinstance(proposal.get("intent"), Mapping) else {}
    first_path = intent.get("first_path") if isinstance(intent.get("first_path"), str) else ""
    proof_boundary = (
        intent.get("proof_boundary") if isinstance(intent.get("proof_boundary"), str) else ""
    )
    success_metrics = row_text_tuple(intent, "success_metrics")
    for row in components:
        component_id = str(row.get("component_id") or "").strip()
        if not component_id:
            raise GreenfieldAuthoredSemanticsError(
                "Greenfield component handoff is missing its typed component id"
            )
        component_workstreams = [
            str(item).strip().upper()
            for item in traceability_plan.component_workstreams.get(component_id, ())
            if str(item).strip()
        ]
        if not component_workstreams:
            raise GreenfieldAuthoredSemanticsError(
                f"Greenfield component `{component_id}` is missing its typed workstream binding"
            )
        child_ids = [item for item in component_workstreams if item != project_id]
        release_child_ids = [item for item in first_release_ids if item in child_ids]
        start_id = (release_child_ids or child_ids or component_workstreams)[0]
        if start_id not in by_id:
            raise GreenfieldAuthoredSemanticsError(
                f"Greenfield component `{component_id}` references an unknown workstream"
            )
        proposal_row = _proposal_row_for_created_id(
            proposal=proposal,
            created=created,
            created_id=start_id,
        )
        if not proposal_row:
            raise GreenfieldAuthoredSemanticsError(
                f"Greenfield component `{component_id}` is missing its typed backlog projection"
            )
        title = str(by_id.get(start_id, {}).get("title", "")).strip()
        first_slice_rows = row_text_tuple(proposal_row, "recommended_first_slice")
        first_slice = first_slice_rows[0] if first_slice_rows else first_path
        if not isinstance(row.get("component_contract"), Mapping):
            raise GreenfieldAuthoredSemanticsError(
                f"Greenfield component `{component_id}` is missing its typed component contract"
            )
        component_contract = dict(row["component_contract"])
        validation_gates = list(
            dict.fromkeys(
                [
                    proof_boundary,
                    *row_text_tuple(proposal_row, "validation"),
                    *row_text_tuple(proposal_row, "success_metrics"),
                    *success_metrics,
                ]
            )
        )
        handoffs[component_id] = {
            **project_context,
            "workstream_id": start_id,
            "workstream_title": title,
            "release_selector": release_selector,
            "first_slice": first_slice,
            "accepted_first_path": first_path,
            "proof_boundary": proof_boundary,
            "success_metrics": list(success_metrics),
            "component_contract": component_contract,
            "validation_gates": validation_gates,
            "verification_commands": verification_commands(start_id),
        }
    return handoffs


def _project_context(proposal: Mapping[str, Any]) -> dict[str, str]:
    intent = proposal.get("intent") if isinstance(proposal.get("intent"), Mapping) else {}
    project_brief = (
        proposal.get("project_brief")
        if isinstance(proposal.get("project_brief"), Mapping)
        else {}
    )
    return {
        "project_title": intent.get("title") if isinstance(intent.get("title"), str) else "",
        "project_purpose": (
            project_brief.get("purpose")
            if isinstance(project_brief.get("purpose"), str)
            else ""
        ),
        "project_outcome": (
            project_brief.get("project_outcome")
            if isinstance(project_brief.get("project_outcome"), str)
            else ""
        ),
    }


def verification_commands(start_workstream_id: str) -> list[str]:
    start_id = str(start_workstream_id or "").strip() or "<first-workstream-id>"
    return [
        f"./.odylith/bin/odylith context --repo-root . {start_id}",
        "./.odylith/bin/odylith validate plan-workstream-binding --repo-root .",
        "./.odylith/bin/odylith validate plan-traceability --repo-root .",
        "./.odylith/bin/odylith sync --repo-root . --impact-mode selective",
    ]


def _created_by_id(created: Sequence[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    return {
        str(row.get("idea_id", "")).strip().upper(): row
        for row in created
        if str(row.get("idea_id", "")).strip()
    }


def _candidate_start_ids(
    *,
    first_release_workstreams: Sequence[str],
    project_id: str,
) -> list[str]:
    candidate_ids = [
        str(item).strip().upper()
        for item in first_release_workstreams
        if str(item).strip().upper() and str(item).strip().upper() != project_id
    ]
    return candidate_ids


def _proposal_row_for_created_id(
    *,
    proposal: Mapping[str, Any],
    created: Sequence[Mapping[str, Any]],
    created_id: str,
) -> Mapping[str, Any]:
    proposal_rows = mapping_rows(proposal.get("backlog"))
    target = str(created_id or "").strip().upper()
    for index, created_row in enumerate(created):
        idea_id = str(created_row.get("idea_id", "")).strip().upper()
        if idea_id == target and index < len(proposal_rows):
            return proposal_rows[index]
    return {}


def _project_first_prompt(
    *,
    project_id: str,
    project_title: str,
    start_id: str,
    start_title: str,
) -> str:
    target = project_id or start_id or "<project-workstream-id>"
    next_lane = f"{start_id} {start_title}".strip() if start_id else "the first targeted child workstream"
    return (
        f"Deepen {target}: review `{project_title}`, choose or accept the project direction options, "
        f"confirm coding-readiness gates, then plan {next_lane} only after the project shape is accepted."
    )


def _implementation_prompt(
    *,
    start_id: str,
    title: str,
    first_path: str,
    release_requirements: str,
) -> str:
    title_text = title or "the first targeted workstream"
    first_path_text = str(first_path or "").strip()
    release_requirements_text = str(release_requirements or "").strip()
    if release_requirements_text and release_requirements_text in first_path_text:
        release_requirements_text = ""
    if first_path_text and first_path_text[-1] not in ".!?":
        first_path_text = f"{first_path_text}."
    if release_requirements_text and release_requirements_text[-1] not in ".!?":
        release_requirements_text = f"{release_requirements_text}."
    return (
        f"After project-first scope is accepted, start {start_id}. "
        f"Preserve this accepted first path: {first_path_text} "
        f"{release_requirements_text + ' ' if release_requirements_text else ''}"
        f"Treat `{title_text}` as the first coding scope and do not expand scope until success, blocked-input, "
        "replay, and handoff evidence is written and reviewed."
    )
