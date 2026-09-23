"""Copy canonical Greenfield meaning into a dependency-ready delivery handoff.

Project-wide context and the selected workstream remain distinct. Allocation
and prerequisite validity belong to traceability, not presentation order.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from odylith.runtime.domain_intelligence.greenfield_authored_first_run import authored_first_run_text
from odylith.runtime.domain_intelligence.greenfield_authored_assumptions import decision_copy
from odylith.runtime.domain_intelligence.greenfield_authored_semantics import (
    GreenfieldAuthoredSemanticsError,
    authored_projection_relations,
)
from odylith.runtime.domain_intelligence.greenfield_handoff_contract import (
    build_coding_readiness_contract,
    render_coding_readiness_gates,
    render_selected_workstream_scope,
)
from odylith.runtime.domain_intelligence.greenfield_rows import mapping_rows
from odylith.runtime.domain_intelligence.greenfield_traceability import first_executable_workstream
from odylith.runtime.context_engine import execution_engine_handshake


GREENFIELD_EXECUTION_HANDOFF_SCHEMA_VERSION = "odylith.greenfield.execution-handoff.v1"


def build_execution_handoff(
    *, target: Mapping[str, Any], verification_commands: Sequence[str],
    proof_boundary: str, operational_constraints: Sequence[str],
) -> dict[str, Any]:
    """Bind the selected typed slice to the real Execution Engine contract.

    Greenfield is an authoring path, so it must not invent execution meaning
    from prose. The existing Execution Engine snapshot is invoked with the
    selected typed target and its proof commands, then projected into a small
    host-neutral handoff carried into the sealed package.
    """

    component_refs = tuple(row_text_tuple(target, "component_refs"))
    payload = {
        "component_id": execution_engine_handshake.CANONICAL_EXECUTION_ENGINE_COMPONENT_ID,
        "target_component_ids": [
            execution_engine_handshake.CANONICAL_EXECUTION_ENGINE_COMPONENT_ID,
            *component_refs,
        ],
        "workstream_context": {
            "workstream_id": str(target.get("workstream_id", "")).strip(),
            "component_ids": list(component_refs),
        },
        "validation_bundle": {
            "strict_gate_commands": list(verification_commands),
            "strict_gate_command_count": len(tuple(verification_commands)),
            "plan_binding_required": True,
            "governed_surface_sync_required": True,
        },
        "turn_context": {
            "proof_boundary": str(proof_boundary or "").strip(),
            "operational_constraints": list(operational_constraints),
        },
    }
    handshake = execution_engine_handshake.normalize_execution_engine_handshake(
        payload=payload,
        routing_handoff={"route_ready": True, "narrowing_required": False},
    )
    snapshot = execution_engine_handshake.compact_execution_engine_snapshot_for_packet(
        payload=payload,
        routing_handoff={"route_ready": True, "narrowing_required": False},
        reuse_existing=False,
    )
    snapshot_fields = (
        "present", "objective", "outcome", "rationale", "mode", "next_move",
        "current_phase", "last_successful_phase", "closure", "resume_token",
        "validation_archetype", "validation_minimum_pass_count", "blocker",
        "requires_reanchor", "component_id", "canonical_component_id",
        "identity_status", "target_component_id", "target_component_ids",
        "target_component_status", "handshake_version",
    )
    compact_snapshot = {
        key: snapshot[key]
        for key in snapshot_fields
        if key in snapshot and snapshot[key] not in ("", [], {}, None)
    }
    return {
        "schema_version": GREENFIELD_EXECUTION_HANDOFF_SCHEMA_VERSION,
        "semantic_authority": "typed_canonical_intent",
        "projection_policy": "execution_engine_snapshot_projection",
        "target": dict(target),
        "handshake": handshake,
        "snapshot": compact_snapshot,
    }


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


def build_next_steps(
    *, proposal: Mapping[str, Any], backlog_result: Mapping[str, Any],
    first_release_workstreams: Sequence[str], release_selector: str,
) -> dict[str, Any]:
    """Bind the first executable delivery slice without inventing a parent record."""

    if not authored_projection_relations(proposal):
        raise GreenfieldAuthoredSemanticsError(
            "Greenfield implementation handoff requires model-authored typed intent"
        )
    selected = first_executable_workstream(
        proposal=proposal, created_backlog=mapping_rows(backlog_result.get("created")),
        first_release_workstreams=first_release_workstreams,
    )
    design = selected.row["provisional_workstream_contract"]["provisional_workstream"]
    intent = proposal["intent"]
    brief = proposal.get("project_brief")
    project_brief = brief if isinstance(brief, Mapping) else {}
    first_path = authored_first_run_text(intent)
    proof_boundary = decision_copy(intent, "proof_boundary")
    target = {
        "workstream_id": selected.idea_id,
        "workstream_title": selected.title,
        "deliverable": design["deliverable"],
        "verification": design["verification"],
        "component_refs": tuple(row_text_tuple(selected.row, "component_focus")),
    }
    readiness_contract = build_coding_readiness_contract(
        workstream_id=selected.idea_id, workstream_title=selected.title,
        release_selector=release_selector, accepted_first_path=first_path,
        proof_boundary=proof_boundary,
        evidence_requirements=row_text_tuple(intent, "evidence_requirements"),
        operational_constraints=row_text_tuple(intent, "operational_constraints"),
        non_goals=row_text_tuple(intent, "non_goals"),
    )
    execution_handoff = build_execution_handoff(
        target=target,
        verification_commands=verification_commands(selected.idea_id),
        proof_boundary=proof_boundary,
        operational_constraints=row_text_tuple(intent, "operational_constraints"),
    )
    return {
        "project_title": intent["title"],
        "first_release_workstream_ids": list(first_release_workstreams),
        "start_workstream_id": selected.idea_id,
        "start_workstream_title": selected.title,
        "implementation_target": target,
        "release_selector": release_selector,
        "project_review_prompt": (
            f"Review {intent['title']} in the Project dashboard, including its release workstreams, "
            "proposed design, constraints, exclusions, and proof requirements. "
            f"After readiness decisions are recorded, plan {selected.idea_id} {selected.title}."
        ),
        "implementation_prompt": _implementation_prompt(
            target=target,
            first_path=first_path, release_requirements=proof_boundary,
        ),
        "customization_options": list(row_text_tuple(project_brief, "customization_options")),
        "coding_readiness_gates": render_coding_readiness_gates(readiness_contract),
        "coding_readiness_contract": readiness_contract,
        "execution_engine_handoff": execution_handoff,
        "validation_gates": list(dict.fromkeys([
            design["verification"], *row_text_tuple(selected.row, "validation"),
            *row_text_tuple(selected.row, "success_metrics"),
        ])),
        "release_validation_gates": list(dict.fromkeys([
            proof_boundary, *row_text_tuple(intent, "success_metrics"),
        ])),
        "operator_sequence": [
            "Review the accepted project in odylith/index.html?tab=project before source edits.",
            f"Review release {release_selector} and its allocated workstreams.",
            "Record material runtime, data, architecture, and validation decisions before planning.",
            f"Open {selected.idea_id} {selected.title}, the first dependency-free proposed workstream.",
            "Plan and prove that workstream's deliverable; track remaining release work separately.",
        ],
        "verification_commands": verification_commands(selected.idea_id),
    }


def verification_commands(start_workstream_id: str) -> list[str]:
    start_id = str(start_workstream_id or "").strip() or "<first-workstream-id>"
    return [
        f"./.odylith/bin/odylith context --repo-root . {start_id}",
        "./.odylith/bin/odylith validate plan-workstream-binding --repo-root .",
        "./.odylith/bin/odylith validate plan-traceability --repo-root .",
        "./.odylith/bin/odylith sync --repo-root . --impact-mode selective",
    ]


def _implementation_prompt(
    *, target: Mapping[str, Any],
    first_path: str, release_requirements: str,
) -> str:
    return (
        "After project readiness decisions are recorded, plan and implement only the selected workstream.\n"
        f"{render_selected_workstream_scope(target)}\n\n"
        "Release context — preserve this direction without treating the whole release as this slice:\n"
        f"{first_path}\n\nRelease proof boundary:\n{release_requirements}\n\n"
        "Stop after the selected deliverable is proved. Record remaining release work explicitly; "
        "do not claim the complete first run or release is implemented."
    )
