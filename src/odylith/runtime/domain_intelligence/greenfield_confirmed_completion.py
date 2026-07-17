"""Completion gate for confirmed greenfield project artifacts."""

from __future__ import annotations

import copy
from collections.abc import Mapping
from typing import Any

from odylith.runtime.domain_intelligence import greenfield_programs
from odylith.runtime.domain_intelligence import greenfield_confirmed_completion_text_model as completion_text
from odylith.runtime.domain_intelligence.greenfield_confirmed_component_completion import (
    complete_component_rows,
    repair_component_sentence_lists,
)
from odylith.runtime.domain_intelligence.greenfield_component_contract_differentiation import (
    differentiate_component_contracts,
)
from odylith.runtime.domain_intelligence.greenfield_confirmed_actor_completion import (
    value_starts_with_generic_actor_label,
)
from odylith.runtime.domain_intelligence.greenfield_confirmed_backlog_text_model import (
    validation_proof_summary as _validation_proof_summary,
)
from odylith.runtime.domain_intelligence.greenfield_confirmed_completion_helpers import append_suffix_once as _append_suffix_once
from odylith.runtime.domain_intelligence.greenfield_confirmed_completion_helpers import (
    ensure_text as _ensure_text,
)
from odylith.runtime.domain_intelligence.greenfield_confirmed_completion_helpers import (
    path_phrase as _path_phrase,
)
from odylith.runtime.domain_intelligence.greenfield_confirmed_completion_helpers import (
    security_posture_text as _security_posture_text,
)
from odylith.runtime.domain_intelligence.greenfield_confirmed_project_intelligence import complete_project_intelligence
from odylith.runtime.domain_intelligence.greenfield_confirmed_title_repair import repair_project_title
from odylith.runtime.domain_intelligence.greenfield_confirmed_prewrite_gate import complete_semantic_model as _complete_semantic_model
from odylith.runtime.domain_intelligence.greenfield_confirmed_prewrite_gate import preflight_issues as _preflight_issues
from odylith.runtime.domain_intelligence.greenfield_confirmed_diagram_projection import (
    refresh_confirmed_diagram_projection as _refresh_confirmed_diagram_projection,
)
from odylith.runtime.domain_intelligence.greenfield_confirmed_modal_grammar_repair import (
    repair_generated_modal_grammar as _repair_generated_modal_grammar,
)
from odylith.runtime.domain_intelligence.greenfield_confirmed_completion_quality import (
    sequence_has_text_repair as _sequence_has_text_repair,
)
from odylith.runtime.domain_intelligence.greenfield_confirmed_completion_quality import (
    sequence_needs_repair as _sequence_needs_repair,
)
from odylith.runtime.domain_intelligence.greenfield_confirmed_completion_quality import (
    text_needs_repair as _text_needs_repair,
)
from odylith.runtime.domain_intelligence.greenfield_confirmed_completion_quality import (
    validation_strategy_needs_repair as _validation_strategy_needs_repair,
)
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import clean_generated_text as _clean
from odylith.runtime.domain_intelligence.greenfield_confirmed_preflight_repair import (
    repair_preflight_issues,
)
from odylith.runtime.domain_intelligence.greenfield_product_risks import build_product_risks_from_proposal
from odylith.runtime.domain_intelligence.greenfield_product_risks import risk_text_has_framework_leak
from odylith.runtime.domain_intelligence.greenfield_release_scope_limits import proof_boundary_limit_text
from odylith.runtime.domain_intelligence.greenfield_rows import dict_rows
from odylith.runtime.domain_intelligence.greenfield_semantic_compiler import repair_greenfield_semantic_projections
from odylith.runtime.domain_intelligence.greenfield_text import delimited_text_values
from odylith.runtime.domain_intelligence.greenfield_text import text_values
from odylith.runtime.domain_intelligence.greenfield_text import unique_text
from odylith.runtime.domain_intelligence.greenfield_workstream_risk_projection import domain_risk_for_row
from odylith.runtime.domain_intelligence.greenfield_workstream_risk_projection import proposal_risk_lines
from odylith.runtime.domain_intelligence.greenfield_workstream_risk_projection import workstream_risk_lines
from odylith.runtime.domain_intelligence.proposal_validation import format_proposal_issue_report


_MAX_COMPLETION_PASSES = 10


def complete_confirmed_proposal(
    proposal: Mapping[str, Any],
    *,
    release_selector: str = "",
) -> dict[str, Any]:
    """Fill deterministic omissions in a confirmed proposal before writes."""

    payload = copy.deepcopy(dict(proposal))
    if not _is_confirmed_greenfield(payload):
        return payload
    return greenfield_repair_until_clean(payload, release_selector=release_selector)


def greenfield_repair_until_clean(
    proposal: dict[str, Any],
    *,
    release_selector: str = "",
) -> dict[str, Any]:
    """Run deterministic confirmed-create repairs until all pre-write gates pass."""

    payload = proposal
    last_issues: tuple[str, ...] = ()
    for _pass in range(_MAX_COMPLETION_PASSES):
        changed = False
        changed |= repair_project_title(payload)
        changed |= _complete_project_posture(payload)
        changed |= complete_project_intelligence(
            payload,
            release_selector=release_selector,
            project_title=completion_text.project_title(payload),
            first_path=completion_text.first_path(payload),
            state_object=completion_text.state_object(payload),
            proof_boundary=completion_text.proof_boundary(payload),
            text_needs_repair=_text_needs_repair,
            visible_result=completion_text.outcome_phrase(payload),
        )
        changed |= repair_greenfield_semantic_projections(payload)
        changed |= _complete_backlog(payload)
        changed |= complete_component_rows(payload)
        changed |= differentiate_component_contracts(payload)
        changed |= _reconcile_backlog_with_components(payload)
        changed |= _reconcile_release_plan_with_backlog(payload)
        changed |= _complete_semantic_model(
            payload,
            title=completion_text.project_title(payload),
            state_object=completion_text.state_object(payload),
            first_path=completion_text.first_path(payload),
            proof_boundary=completion_text.proof_boundary(payload),
        )
        if repair_greenfield_semantic_projections(payload):
            changed = True
            changed |= _complete_backlog(payload)
        changed |= _complete_diagrams(payload)
        changed |= _repair_generated_modal_grammar(payload)
        issues = _preflight_issues(payload, release_selector=release_selector)
        if not issues:
            return payload
        changed |= repair_preflight_issues(
            payload,
            issues=issues,
            release_selector=release_selector,
            max_completion_passes=_MAX_COMPLETION_PASSES,
        )
        if tuple(issues) == last_issues and not changed:
            break
        last_issues = tuple(issues)
    final_issues = _preflight_issues(payload, release_selector=release_selector)
    if not final_issues:
        return payload
    raise ValueError(format_proposal_issue_report("confirmed completion", list(final_issues)))


def _is_confirmed_greenfield(proposal: Mapping[str, Any]) -> bool:
    intent = proposal.get("intent")
    if not isinstance(intent, Mapping):
        return False
    return (
        str(intent.get("reasoning_mode", "")).strip() == "odylith_confirmed_governed_proposal"
        and str(proposal.get("write_policy", "")).strip() == "confirmed_intent_before_confirmed_create"
    )


def _complete_project_posture(proposal: dict[str, Any]) -> bool:
    changed = False
    risks = proposal.get("risks")
    if (
        not isinstance(risks, list)
        or not risks
        or _sequence_has_text_repair(risks)
        or any(risk_text_has_framework_leak(row) for row in risks)
        or any(
            value_starts_with_generic_actor_label(row.get("statement"))
            or value_starts_with_generic_actor_label(row.get("mitigation"))
            for row in dict_rows(risks)
        )
    ):
        proposal["risks"] = build_product_risks_from_proposal(
            proposal,
            release=greenfield_programs.proposal_release_selector(proposal, ""),
        )
        changed = True
    posture = proposal.get("security_compliance")
    if not isinstance(posture, Mapping) or not text_values(posture) or _sequence_has_text_repair(posture):
        label = completion_text.project_title(proposal)
        outcome = completion_text.outcome_phrase(proposal)
        proposal["security_compliance"] = {
            "domain": (
                f"{label} carries domain risk when people rely on {outcome} while required input is incomplete, stale, or misunderstood."
            ),
            "security": (
                f"Security posture for {label} covers authorization, ownership checks, access control, private data handling, "
                "credential isolation, abuse prevention, and clear recovery behavior."
            ),
            "policy": (
                f"Compliance policy for {label} keeps privacy, audit, retention, accessibility, safety, and review obligations "
                "visible before production claims are made."
            ),
        }
        changed = True
    validation = proposal.get("validation_strategy")
    if not isinstance(validation, list) or _validation_strategy_needs_repair(proposal):
        outcome = completion_text.outcome_phrase(proposal)
        outcome_action = completion_text.outcome_action_phrase(outcome)
        proof_capability = completion_text.proof_capability_phrase(proposal)
        proof_summary = _validation_proof_summary(completion_text.proof_boundary(proposal))
        proposal["validation_strategy"] = list(
            unique_text(
                [
                    *(validation if isinstance(validation, list) else []),
                    f"Success proof includes {proof_capability}.",
                    f"Result proof confirms the user can {outcome_action} with the visible result explained.",
                    f"Release proof stays inside this promise: {proof_summary}.",
                    f"{completion_text.state_reference(proposal)} can be reconstructed with actor, timestamp, status, and result.",
                    f"Readiness fails when required input, access, privacy, safety, or result explanation is missing.",
                ]
            )
        )
        changed = True
    return changed


def _complete_backlog(proposal: dict[str, Any]) -> bool:
    rows = proposal.get("backlog")
    if not isinstance(rows, list):
        return False
    changed = False
    action = completion_text.action_phrase(proposal)
    outcome = completion_text.outcome_phrase(proposal)
    outcome_action = completion_text.outcome_action_phrase(outcome)
    proof_capability = completion_text.proof_capability_phrase(proposal)
    state = completion_text.state_reference(proposal)
    state_label = completion_text.state_object(proposal)
    actors = completion_text.actor_summary(proposal)
    primary_actor = completion_text.primary_actor_phrase(proposal)
    components = [row for row in proposal.get("components", []) if isinstance(row, Mapping)]
    for index, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            continue
        title = _clean(row.get("title")) or f"{completion_text.project_title(proposal)} Workstream {index}"
        label = completion_text.workstream_subject(row, fallback=title, components=components)
        if not _clean(row.get("problem")) or _text_needs_repair(row.get("problem")):
            row["problem"] = completion_text.workstream_problem(label=label, action=action, outcome=outcome, state=state)
            changed = True
        if not _clean(row.get("customer")) or _text_needs_repair(row.get("customer")):
            row["customer"] = actors
            changed = True
        if not _clean(row.get("opportunity")) or _text_needs_repair(row.get("opportunity")):
            row["opportunity"] = completion_text.workstream_opportunity(
                label=label,
                actor=primary_actor,
                action=action,
                outcome=outcome,
            )
            changed = True
        if not _clean(row.get("product_view")) or _text_needs_repair(row.get("product_view")):
            row["product_view"] = completion_text.workstream_product_view(label=label, action=action, outcome=outcome)
            changed = True
        raw_metrics = row.get("success_metrics")
        metrics = list(delimited_text_values(raw_metrics)) if isinstance(raw_metrics, str) else list(text_values(raw_metrics))
        if isinstance(raw_metrics, str) and metrics != list(text_values(raw_metrics)):
            row["success_metrics"] = metrics
            changed = True
        if len(metrics) < 3 or _sequence_has_text_repair(row.get("success_metrics")):
            row["success_metrics"] = list(
                unique_text(
                    [
                        f"Success proof includes {proof_capability}.",
                        f"Result proof confirms the user can {outcome_action} with a clear explanation.",
                        f"Missing or incorrect input produces a clear correction path instead of a misleading result.",
                        f"The result can be explained from the recorded {state_label} without relying on memory or hidden assumptions.",
                    ]
                )
            )
            changed = True
        projected_domain_risk = domain_risk_for_row(row, proposal)
        if (
            not _clean(row.get("domain_risk"))
            or _text_needs_repair(row.get("domain_risk"))
            or completion_text.has_connector_clipped_risk_subject(row.get("domain_risk", ""))
            or (projected_domain_risk and projected_domain_risk != _clean(row.get("domain_risk")))
        ):
            row["domain_risk"] = projected_domain_risk or completion_text.workstream_risk(label=label, outcome=outcome, state=state)
            changed = True
        if (
            not _clean(row.get("security_posture"))
            or _text_needs_repair(row.get("security_posture"))
            or completion_text.has_connector_clipped_risk_subject(row.get("security_posture", ""))
        ):
            row["security_posture"] = _security_posture_text(label)
            changed = True
        risk_values = list(text_values(row.get("risks")))
        projected_risks = workstream_risk_lines(
            row=row,
            proposal=proposal,
            proposal_risks=proposal_risk_lines(proposal),
            local_risks=risk_values,
        )
        if risk_values and projected_risks != risk_values:
            row["risks"] = projected_risks
            changed = True
        elif (
            not text_values(row.get("risks"))
            or _sequence_has_text_repair(row.get("risks"))
            or any(completion_text.has_connector_clipped_risk_subject(value) for value in text_values(row.get("risks")))
        ):
            row["risks"] = [
                row["domain_risk"],
                row["security_posture"],
            ]
            changed = True
    return changed


def _reconcile_backlog_with_components(proposal: dict[str, Any]) -> bool:
    rows = dict_rows(proposal.get("backlog"))
    components = dict_rows(proposal.get("components"))
    if len(rows) < 2 or not components:
        return False
    by_id = {_clean(component.get("component_id")): component for component in components if _clean(component.get("component_id"))}
    intent = proposal.get("intent") if isinstance(proposal.get("intent"), Mapping) else {}
    non_goal_rows = [row for row in text_values(proposal.get("non_goals") or intent.get("non_goals")) if _clean(row)]
    proof_limit = proof_boundary_limit_text(completion_text.proof_boundary(proposal))
    if proof_limit and proof_limit.casefold() not in {row.casefold() for row in non_goal_rows}:
        non_goal_rows.append(proof_limit)
    changed = False
    for row in rows[1:]:
        component = completion_text.primary_component_for_backlog(row, components=components, by_id=by_id)
        if not component:
            continue
        contract = component.get("component_contract") if isinstance(component.get("component_contract"), Mapping) else {}
        if not contract:
            continue
        label = completion_text.component_label(component, 0)
        state_object = completion_text.state_object(proposal)
        state_ref = completion_text.state_reference(proposal)
        state_change_ref = completion_text.object_reference_phrase(state_object) or completion_text.object_reference_phrase(state_ref)
        focus = completion_text.component_focus_phrase(label=label, contract=contract, fallback=state_object)
        action = completion_text.action_phrase(proposal)
        outcome = completion_text.outcome_phrase(proposal)
        outcome_action = completion_text.outcome_action_phrase(outcome)
        drifted = completion_text.row_drifted_from_component(row, component)
        row_title = completion_text.workstream_subject(row, fallback=label, components=components)
        if _text_needs_repair(row.get("product_view")):
            row["product_view"] = (
                f"{label} should support the user action: {action}. "
                f"It should check required input before it presents a result, then let the user {outcome_action}."
            )
            changed = True
        if _text_needs_repair(row.get("recommended_first_slice")):
            row["recommended_first_slice"] = (
                f"Build the smallest behavior in {label} that supports this path: {action}. It should let the user {outcome_action} "
                "and explain missing or invalid input before presenting a result."
            )
            changed = True
        if _sequence_needs_repair(row.get("success_metrics"), required_tokens=("success", "block", "evidence"), min_items=3):
            metrics = [
                f"{label} owns {_append_suffix_once(focus, 'evidence')}, review rules, and result visibility.",
                f"{label} blocks incomplete evidence before presenting a result, then explains what has to change for {focus}.",
                (
                    f"{row_title} keeps actor, source, status, result, and recovery context attached to "
                    f"{state_change_ref or state_ref}."
                ),
            ]
            if completion_text.row_is_release_proof(row):
                if non_goal_rows:
                    deferred_scope = proof_limit or non_goal_rows[0]
                    metrics.append(
                        f"Deferred scope stays out of {label} validation evidence: {_clean(deferred_scope).rstrip('.')}."
                    )
                metrics.append(
                    f"{label} validation evidence focuses on {completion_text.inline_result_phrase(outcome)}, "
                    "with blocked-input, replay, and handoff cases visible."
                )
            row["success_metrics"] = metrics
            changed = True
        if _sequence_needs_repair(row.get("interfaces"), required_tokens=("input", "output"), min_items=1) or drifted:
            row["interfaces"] = [
                f"{label} accepts the facts needed for {focus} and rejects incomplete entries before they look usable.",
                f"{row_title} hands off the {focus} result, correction state, and explanation with reviewable evidence.",
            ]
            changed = True
        projected_domain_risk = domain_risk_for_row(row, proposal)
        if (
            _text_needs_repair(row.get("domain_risk"))
            or completion_text.has_connector_clipped_risk_subject(row.get("domain_risk", ""))
            or drifted
            or (projected_domain_risk and projected_domain_risk != _clean(row.get("domain_risk")))
        ):
            row["domain_risk"] = projected_domain_risk or completion_text.workstream_risk(label=label, outcome=outcome, state=state_object)
            changed = True
        if (
            not _clean(row.get("security_posture"))
            or _text_needs_repair(row.get("security_posture"))
            or completion_text.has_connector_clipped_risk_subject(row.get("security_posture", ""))
            or drifted
        ):
            row["security_posture"] = _security_posture_text(label)
            changed = True
        risk_values = list(text_values(row.get("risks")))
        projected_risks = workstream_risk_lines(
            row=row,
            proposal=proposal,
            proposal_risks=proposal_risk_lines(proposal),
            local_risks=risk_values,
        )
        if risk_values and projected_risks != risk_values:
            row["risks"] = projected_risks
            changed = True
        elif (
            not text_values(row.get("risks"))
            or _sequence_has_text_repair(row.get("risks"))
            or any(completion_text.has_connector_clipped_risk_subject(value) for value in text_values(row.get("risks")))
            or drifted
        ):
            row["risks"] = [
                row["domain_risk"],
                row["security_posture"],
            ]
            changed = True
        if _sequence_needs_repair(row.get("validation"), required_tokens=("success", "block"), min_items=1) or drifted:
            row["validation"] = [
                f"Validate one successful {_path_phrase(label)}, one missing-input path, and one corrected path against the visible product outcome.",
            ]
            changed = True
    return changed


def _reconcile_release_plan_with_backlog(proposal: dict[str, Any]) -> bool:
    release_plan = proposal.get("release_plan")
    if not isinstance(release_plan, dict):
        return False
    child_titles = [
        _clean(row.get("title"))
        for row in dict_rows(proposal.get("backlog"))[1:]
        if _clean(row.get("title"))
    ]
    if not child_titles:
        return False
    changed = False
    if list(text_values(release_plan.get("target_workstream_titles"))) != child_titles:
        release_plan["target_workstream_titles"] = list(child_titles)
        changed = True
    stages = release_plan.get("release_stages")
    if isinstance(stages, list):
        title_lookup = {title.casefold() for title in child_titles}
        for index, stage in enumerate(stages):
            if not isinstance(stage, dict):
                continue
            current = [ref for ref in text_values(stage.get("workstream_titles")) if _clean(ref)]
            valid_current = [ref for ref in current if ref.casefold() in title_lookup]
            if valid_current and valid_current == current:
                continue
            fallback_title = child_titles[min(index, len(child_titles) - 1)]
            stage["workstream_titles"] = valid_current or [fallback_title]
            changed = True
    return changed


def _complete_diagrams(proposal: dict[str, Any]) -> bool:
    rows = proposal.get("diagrams")
    if not isinstance(rows, list):
        return False
    changed = False
    changed |= _refresh_confirmed_diagram_projection(proposal, rows)
    component_ids = [
        _clean(row.get("component_id"))
        for row in proposal.get("components", [])
        if isinstance(row, Mapping) and _clean(row.get("component_id"))
    ]
    for index, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            continue
        slug = _clean(row.get("slug")) or f"{completion_text.slug_title(proposal)}-diagram-{index}"
        changed |= _ensure_text(row, "slug", slug)
        changed |= _ensure_text(row, "title", completion_text.diagram_title(row, proposal=proposal, index=index), repair_bad_text=True)
        changed |= _ensure_text(row, "kind", "flowchart")
        changed |= _ensure_text(
            row,
            "summary",
            f"Shows how {completion_text.project_title(proposal)} preserves first-path state, evidence, and proof.",
            repair_bad_text=True,
        )
        changed |= _ensure_text(row, "owner", "repo")
        changed |= _ensure_text(row, "link_state", "atlas_first_draft")
        if not text_values(row.get("watch_paths")):
            row["watch_paths"] = [
                "odylith/radar/source",
                "odylith/registry/source",
            ]
            changed = True
        if not text_values(row.get("related_components")) and component_ids:
            row["related_components"] = component_ids[:4]
            changed = True
    return changed


__all__ = ["complete_confirmed_proposal", "greenfield_repair_until_clean"]
