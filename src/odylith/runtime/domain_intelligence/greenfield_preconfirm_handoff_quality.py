"""Validate Greenfield implementation handoffs before transaction sealing.

This owner validates Project dashboard prompts and operator next steps. The
model-authored path compares typed bindings directly; legacy packages retain
their existing presentation checks without becoming semantic authority.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from odylith.runtime.common.value_coercion import normalize_string as clean_text
from odylith.runtime.domain_intelligence.greenfield_authored_semantics import (
    AUTHORED_PROJECTION_ORIGIN,
    authored_projection_relations,
    authored_visible_result,
    component_responsibility_relations_from_intent,
    first_path_context_relations_from_intent,
)
from odylith.runtime.domain_intelligence.greenfield_completion_types import (
    GreenfieldCompletionPackage,
)
from odylith.runtime.domain_intelligence.greenfield_handoff_contract import (
    PROJECT_HANDOFF_STEP_SEQUENCE,
    coding_readiness_contract_issues,
    project_handoff_step_contract_issues,
)
from odylith.runtime.domain_intelligence.greenfield_rows import mapping_rows
from odylith.runtime.domain_intelligence.greenfield_scalar_values import (
    nested_text_values as text_values,
)
from odylith.runtime.project_intelligence.greenfield_authored_dashboard import (
    authored_actor_rows,
    authored_component_capabilities,
    authored_product_boundary,
)


def project_dashboard_preview_issues(
    package: GreenfieldCompletionPackage,
    project_dashboard_preview: Mapping[str, Any],
    *,
    model_authored: bool,
) -> list[str]:
    """Validate dashboard handoffs without recovering authored meaning from prose."""

    issues: list[str] = []
    prompts = mapping_rows(project_dashboard_preview.get("host_handoff_prompts"))
    if len(prompts) < 5:
        issues.append("Project dashboard preview must include all source-launch implementation prompts")
    if model_authored:
        issues.extend(
            _authored_project_dashboard_contract_issues(
                package,
                project_dashboard_preview,
                prompts,
            )
        )
    return issues


def _authored_project_dashboard_contract_issues(
    package: GreenfieldCompletionPackage,
    project_dashboard_preview: Mapping[str, Any],
    prompts: Sequence[Mapping[str, Any]],
) -> list[str]:
    proposal = package.proposal
    relations = authored_projection_relations(proposal)
    if not relations:
        return ["model-authored Project dashboard is missing its typed semantic authority"]
    intent = proposal.get("intent") if isinstance(proposal.get("intent"), Mapping) else {}
    projection = (
        project_dashboard_preview.get("projection")
        if isinstance(project_dashboard_preview.get("projection"), Mapping)
        else {}
    )
    facts = (
        project_dashboard_preview.get("authored_facts")
        if isinstance(project_dashboard_preview.get("authored_facts"), Mapping)
        else {}
    )
    issues: list[str] = []
    if projection.get("origin") != AUTHORED_PROJECTION_ORIGIN:
        issues.append("model-authored Project dashboard lost its projection origin")
    expected_scalars = {
        "title": intent.get("title"),
        "product_story": intent.get("product_story"),
        "first_path": intent.get("first_path"),
        "proof_boundary": intent.get("proof_boundary"),
        "visible_result": authored_visible_result(relations),
    }
    for key, expected in expected_scalars.items():
        if facts.get(key) != expected:
            issues.append(f"model-authored Project dashboard drifted from intent.{key}")
    for key in (
        "human_actors",
        "internal_systems",
        "external_systems",
        "non_goals",
        "operational_constraints",
        "evidence_requirements",
        "success_metrics",
    ):
        if _exact_rows(facts.get(key)) != _exact_rows(intent.get(key)):
            issues.append(f"model-authored Project dashboard drifted from intent.{key}")
    if [dict(row) for row in mapping_rows(facts.get("first_path_relations"))] != [
        dict(row) for row in relations
    ]:
        issues.append("model-authored Project dashboard drifted from typed first-path relations")
    context_relations = first_path_context_relations_from_intent(intent)
    if [dict(row) for row in mapping_rows(facts.get("first_path_context_relations"))] != [
        dict(row) for row in context_relations
    ]:
        issues.append("model-authored Project dashboard drifted from typed path-context relations")
    component_relations = component_responsibility_relations_from_intent(intent)
    if [dict(row) for row in mapping_rows(facts.get("component_responsibility_relations"))] != [
        dict(row) for row in component_relations
    ]:
        issues.append("model-authored Project dashboard drifted from typed component relations")
    components = mapping_rows(proposal.get("components"))
    story = (
        project_dashboard_preview.get("product_story")
        if isinstance(project_dashboard_preview.get("product_story"), Mapping)
        else {}
    )
    cards = {
        str(row.get("semantic_slot") or ""): str(row.get("body") or "")
        for row in mapping_rows(story.get("release_contract"))
    }
    expected_cards = {
        "product_boundary": authored_product_boundary(
            components=components,
            external_systems=_exact_rows(intent.get("external_systems")),
            non_goals=_exact_rows(intent.get("non_goals")),
        ),
        "owned_capabilities": "\n".join(authored_component_capabilities(components)),
    }
    for slot, expected in expected_cards.items():
        if cards.get(slot) != expected:
            issues.append(f"model-authored Project dashboard drifted from typed {slot}")
    expected_actor_cards = [
        {"role": "human", "title": actor, "body": body}
        for _role, actor, body in authored_actor_rows(
            human_actors=_exact_rows(intent.get("human_actors")),
            relations=relations,
        )
    ]
    if [dict(row) for row in mapping_rows(story.get("actors"))] != expected_actor_cards:
        issues.append("model-authored Project dashboard drifted from typed actor identities")
    if len(prompts) != len(PROJECT_HANDOFF_STEP_SEQUENCE):
        issues.append("model-authored Project dashboard must carry the exact five-step handoff")
        return issues

    created_ids = {
        clean_text(row.get("idea_id") or row.get("workstream_id") or row.get("id")).upper()
        for row in mapping_rows((package.backlog_result or {}).get("created"))
        if clean_text(row.get("idea_id") or row.get("workstream_id") or row.get("id"))
    }
    next_steps = package.next_steps_preview if isinstance(package.next_steps_preview, Mapping) else {}
    start_id = clean_text(next_steps.get("start_workstream_id")).upper()
    expected_components = tuple(
        clean_text(row.get("component_id") or row.get("id"))
        for row in mapping_rows(proposal.get("components"))
        if clean_text(row.get("component_id") or row.get("id"))
    )
    expected_commands = _exact_rows(next_steps.get("verification_commands"))
    expected_excluded_scope = _unique_exact(
        [
            *_exact_rows(intent.get("operational_constraints")),
            *_exact_rows(intent.get("non_goals")),
        ]
    )
    for index, (prompt, expected_step_id) in enumerate(
        zip(prompts, PROJECT_HANDOFF_STEP_SEQUENCE, strict=True),
        start=1,
    ):
        contract = prompt.get("contract")
        for issue in project_handoff_step_contract_issues(
            contract,
            expected_step_id=expected_step_id,
        ):
            issues.append(f"model-authored Project handoff step {index} {issue}")
        if not isinstance(contract, Mapping):
            continue
        bindings = contract.get("fact_bindings")
        if not isinstance(bindings, Mapping):
            continue
        if bindings.get("project_title") != intent.get("title"):
            issues.append(f"model-authored Project handoff step {index} drifted from intent.title")
        if bindings.get("accepted_first_path") != intent.get("first_path"):
            issues.append(f"model-authored Project handoff step {index} drifted from intent.first_path")
        if bindings.get("proof_boundary") != intent.get("proof_boundary"):
            issues.append(f"model-authored Project handoff step {index} drifted from intent.proof_boundary")
        if bindings.get("visible_result") != authored_visible_result(relations):
            issues.append(f"model-authored Project handoff step {index} drifted from the visible result")
        if _exact_rows(bindings.get("excluded_scope")) != expected_excluded_scope:
            issues.append(f"model-authored Project handoff step {index} drifted from accepted scope")
        if _exact_rows(bindings.get("component_refs")) != expected_components:
            issues.append(f"model-authored Project handoff step {index} drifted from component ids")
        if _exact_rows(bindings.get("verification_commands")) != expected_commands:
            issues.append(f"model-authored Project handoff step {index} drifted from verification commands")
        workstream_refs = {
            clean_text(item).upper()
            for item in _exact_rows(bindings.get("first_release_workstream_refs"))
            if clean_text(item)
        }
        if expected_step_id != "choose_language":
            if start_id not in workstream_refs:
                issues.append(f"model-authored Project handoff step {index} lost its start workstream")
            if created_ids and not workstream_refs.issubset(created_ids):
                issues.append(f"model-authored Project handoff step {index} contains an unallocated workstream")
    return issues


def next_steps_preview_issues(
    package: GreenfieldCompletionPackage,
    next_steps_preview: Mapping[str, Any],
    *,
    semantic_checks: bool = True,
) -> list[str]:
    """Validate the next-step surface with typed checks for authored packages."""

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
    if start_id and start_id not in prompt.upper():
        issues.append("operator next-steps implementation prompt must name the first implementation workstream")
    operator_sequence = text_values(next_steps_preview.get("operator_sequence"))
    if len(operator_sequence) < 3:
        issues.append("operator next-steps preview must include an actionable operator sequence")
    gates = text_values(next_steps_preview.get("coding_readiness_gates"))
    if not gates:
        issues.append("operator next-steps preview must show coding-readiness gates")
    if semantic_checks and len(gates) < 4:
        issues.append("operator next-steps preview must carry coding-readiness gates")
    if not semantic_checks:
        issues.extend(
            coding_readiness_contract_issues(
                next_steps_preview.get("coding_readiness_contract"),
                expected_workstream_id=start_id,
            )
        )
    commands = text_values(next_steps_preview.get("verification_commands"))
    if len(commands) < 2:
        issues.append("operator next-steps preview must include multiple verification commands")
    if semantic_checks:
        issues.append("operator next-steps preview requires the authored coding-readiness contract")
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
    if not text or len([part for part in text.replace("/", " ").split() if part.strip()]) < min_words:
        issues.append(message)


def _exact_rows(value: Any) -> tuple[str, ...]:
    rows = value if isinstance(value, Sequence) and not isinstance(value, (str, bytes)) else (value,)
    return tuple(row for row in rows if isinstance(row, str) and row)


def _unique_exact(values: Sequence[str]) -> tuple[str, ...]:
    rows: list[str] = []
    for value in values:
        if value and value not in rows:
            rows.append(value)
    return tuple(rows)


__all__ = ["next_steps_preview_issues", "project_dashboard_preview_issues"]
