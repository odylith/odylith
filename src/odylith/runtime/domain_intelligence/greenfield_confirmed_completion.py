"""Completion gate for confirmed greenfield project artifacts."""

from __future__ import annotations

import copy
import re
from collections.abc import Mapping, Sequence
from typing import Any

from odylith.runtime.domain_intelligence import greenfield_programs
from odylith.runtime.domain_intelligence import greenfield_confirmed_completion_text_model as completion_text
from odylith.runtime.domain_intelligence.greenfield_component_contract_differentiation import (
    differentiate_component_contracts,
)
from odylith.runtime.domain_intelligence.greenfield_confirmed_component_completion import (
    complete_component_rows,
    repair_component_sentence_lists,
)
from odylith.runtime.domain_intelligence.greenfield_confirmed_project_intelligence import complete_project_intelligence
from odylith.runtime.domain_intelligence.greenfield_confirmed_title_repair import repair_project_title
from odylith.runtime.domain_intelligence.greenfield_confirmed_prewrite_gate import complete_semantic_model as _complete_semantic_model
from odylith.runtime.domain_intelligence.greenfield_confirmed_prewrite_gate import preflight_issues as _preflight_issues
from odylith.runtime.domain_intelligence.greenfield_confirmed_completion_quality import (
    proof_boundary_is_weak as _proof_boundary_is_weak,
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
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import sentence_text as _sentence
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import set_sentence_list as _set_list
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import set_sentence_text as _set_text
from odylith.runtime.domain_intelligence.greenfield_product_risks import build_product_risks_from_proposal
from odylith.runtime.domain_intelligence.greenfield_product_risks import risk_text_has_framework_leak
from odylith.runtime.domain_intelligence.greenfield_rows import dict_rows
from odylith.runtime.domain_intelligence.greenfield_text import text_values
from odylith.runtime.domain_intelligence.greenfield_text import unique_text
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
        )
        changed |= _complete_backlog(payload)
        changed |= complete_component_rows(payload)
        changed |= differentiate_component_contracts(payload)
        changed |= _reconcile_backlog_with_components(payload)
        changed |= _complete_semantic_model(
            payload,
            title=completion_text.project_title(payload),
            state_object=completion_text.state_object(payload),
            first_path=completion_text.first_path(payload),
            proof_boundary=completion_text.proof_boundary(payload),
        )
        changed |= _complete_diagrams(payload)
        issues = _preflight_issues(payload, release_selector=release_selector)
        if not issues:
            return payload
        changed |= _repair_preflight_issues(payload, issues=issues, release_selector=release_selector)
        if tuple(issues) == last_issues and not changed:
            break
        last_issues = tuple(issues)
    raise ValueError(format_proposal_issue_report("confirmed completion", list(last_issues)))


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
                f"{label} carries domain risk when people rely on {outcome} while required information is incomplete, stale, or misunderstood."
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
        action = completion_text.action_phrase(proposal)
        outcome = completion_text.outcome_phrase(proposal)
        outcome_action = completion_text.outcome_action_phrase(outcome)
        proposal["validation_strategy"] = list(
            unique_text(
                [
                    *(validation if isinstance(validation, list) else []),
                    f"A representative user can {action} and {outcome_action}.",
                    f"{completion_text.state_object(proposal)} can be reconstructed with actor, timestamp, status, and result.",
                    f"Readiness fails when required information, access, privacy, safety, or result explanation is missing.",
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
    state = completion_text.state_object(proposal)
    actors = completion_text.actor_summary(proposal)
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
            row["opportunity"] = completion_text.workstream_opportunity(label=label, action=action, outcome=outcome)
            changed = True
        if not _clean(row.get("product_view")) or _text_needs_repair(row.get("product_view")):
            row["product_view"] = completion_text.workstream_product_view(label=label, action=action, outcome=outcome)
            changed = True
        metrics = list(text_values(row.get("success_metrics")))
        if len(metrics) < 3 or _sequence_has_text_repair(row.get("success_metrics")):
            row["success_metrics"] = list(
                unique_text(
                    [
                        f"A representative user can {action} and {outcome_action}.",
                        f"Missing or incorrect input produces a clear correction path instead of a misleading result.",
                        f"The result can be explained from the recorded {state} without relying on memory or hidden assumptions.",
                    ]
                )
            )
            changed = True
        if (
            not _clean(row.get("domain_risk"))
            or _text_needs_repair(row.get("domain_risk"))
            or completion_text.has_connector_clipped_risk_subject(row.get("domain_risk", ""))
        ):
            row["domain_risk"] = completion_text.workstream_risk(label=label, outcome=outcome, state=state)
            changed = True
        if (
            not _clean(row.get("security_posture"))
            or _text_needs_repair(row.get("security_posture"))
            or completion_text.has_connector_clipped_risk_subject(row.get("security_posture", ""))
        ):
            row["security_posture"] = f"Security posture: {label} protects user-entered facts, result history, and recovery details."
            changed = True
        if (
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
    if not non_goal_rows:
        proof = completion_text.proof_boundary(proposal)
        match = re.search(r"\bwithout\s+claiming\s+(?P<scope>[^.;]+)", proof, flags=re.IGNORECASE)
        if match:
            non_goal_rows = [f"No {match.group('scope').strip()}"]
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
        focus = completion_text.component_focus_phrase(label=label, contract=contract, fallback=state_object)
        action = completion_text.action_phrase(proposal)
        outcome = completion_text.outcome_phrase(proposal)
        outcome_action = completion_text.outcome_action_phrase(outcome)
        outcome_sentence = completion_text.lower_first(outcome)
        drifted = completion_text.row_drifted_from_component(row, component)
        if _text_needs_repair(row.get("product_view")) or drifted:
            row["product_view"] = (
                f"{label} should support the concrete user action: {action}. It should then show {outcome_sentence}. "
                f"If something is missing, it should explain the problem before it presents a result."
            )
            changed = True
        if _text_needs_repair(row.get("recommended_first_slice")) or drifted:
            row["recommended_first_slice"] = (
                f"Build the smallest behavior in {label} that supports this path: {action}. It should show {outcome_sentence} "
                "and explain missing or invalid information before presenting a result."
            )
            changed = True
        if _sequence_needs_repair(row.get("success_metrics"), required_tokens=("success", "block", "evidence"), min_items=3) or drifted:
            metrics = [
                f"{label} proves one complete user path where a representative user can {outcome_action}.",
                f"{label} explains blocked, missing, or invalid information before the product shows a result.",
                f"{label} preserves actor, source, status, result, and recovery context for each accepted change to {state_object}.",
            ]
            if completion_text.row_is_release_proof(row):
                if non_goal_rows:
                    metrics.append(f"{label} keeps this deferred outcome outside the release claim: {_clean(non_goal_rows[0]).rstrip('.')}.")
                metrics.append(
                    f"{label} stays inside the first-release outcome described by the accepted product direction."
                )
            row["success_metrics"] = metrics
            changed = True
        if _sequence_needs_repair(row.get("interfaces"), required_tokens=("input", "output"), min_items=1) or drifted:
            row["interfaces"] = [
                f"{label} accepts the facts needed for {focus} and rejects incomplete entries before they look usable.",
                f"{label} returns the result, correction state, or explanation needed for the next product step.",
            ]
            changed = True
        if (
            _text_needs_repair(row.get("domain_risk"))
            or completion_text.has_connector_clipped_risk_subject(row.get("domain_risk", ""))
            or drifted
        ):
            row["domain_risk"] = completion_text.workstream_risk(label=label, outcome=outcome, state=state_object)
            changed = True
        if (
            not _clean(row.get("security_posture"))
            or _text_needs_repair(row.get("security_posture"))
            or completion_text.has_connector_clipped_risk_subject(row.get("security_posture", ""))
            or drifted
        ):
            row["security_posture"] = f"Security posture: {label} protects user-entered facts, result history, and recovery details."
            changed = True
        if (
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
                f"Validate one successful {label} path, one missing-input path, and one corrected path against the visible product outcome.",
            ]
            changed = True
    return changed


def _complete_diagrams(proposal: dict[str, Any]) -> bool:
    rows = proposal.get("diagrams")
    if not isinstance(rows, list):
        return False
    changed = False
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


def _repair_preflight_issues(
    proposal: dict[str, Any],
    *,
    issues: Sequence[str],
    release_selector: str,
) -> bool:
    issue_text = " ".join(str(issue) for issue in issues).casefold()
    changed = False
    proof_or_validation = (
        _validation_strategy_needs_repair(proposal)
        or "proof boundary" in issue_text
        or "validation_strategy" in issue_text
        or "validation-strategy" in issue_text
        or "validation strategy" in issue_text
        or "clipped" in issue_text
        or "unfinished" in issue_text
        or "concrete success" in issue_text
        or "too thin to guide implementation" in issue_text
        or "not anchored to enough project-specific nouns" in issue_text
        or "repeats scaffold language" in issue_text
    )
    if proof_or_validation:
        changed |= _repair_release_success_language(proposal, release_selector=release_selector)
        changed |= _repair_validation_strategy(proposal, release_selector=release_selector)
        changed |= _repair_backlog_success_language(proposal, release_selector=release_selector)
        changed |= _repair_project_intelligence_validation(proposal, release_selector=release_selector)
    if (
        "too interchangeable" in issue_text
        or "too similar" in issue_text
        or "could not distinguish" in issue_text
        or "component-local" in issue_text
        or "clearer separation" in issue_text
    ):
        changed |= differentiate_component_contracts(proposal, max_passes=_MAX_COMPLETION_PASSES)
    if "generated prose" in issue_text or "malformed" in issue_text or "sentence" in issue_text:
        changed |= _repair_generated_sentence_lists(proposal, release_selector=release_selector)
    return changed


def _repair_release_success_language(proposal: dict[str, Any], *, release_selector: str) -> bool:
    release = greenfield_programs.proposal_release_selector(proposal, release_selector)
    label = completion_text.project_title(proposal)
    state_object = completion_text.state_object(proposal)
    proof_boundary = completion_text.proof_boundary(proposal)
    action = completion_text.action_phrase(proposal)
    outcome = completion_text.outcome_phrase(proposal)
    outcome_action = completion_text.outcome_action_phrase(outcome)
    proof_success = _sentence(
        f"Release {release} succeeds only when a representative user can {action}, the product shows {outcome}, and {state_object} remains understandable when information is missing or corrected.",
        limit=520,
    )
    changed = False
    intent = proposal.get("intent")
    if isinstance(intent, dict):
        summary = _sentence(
            f"{_clean(intent.get('product_story')) or label} {proof_success}",
            limit=620,
        )
        changed |= _set_text(intent, "summary", summary)
        if _proof_boundary_is_weak(_clean(intent.get("proof_boundary"))):
            changed |= _set_text(intent, "proof_boundary", proof_success)
    release_plan = proposal.get("release_plan")
    if isinstance(release_plan, dict):
        criteria = [
            _sentence(f"{label} success proof shows a representative user can {action} and {outcome_action}.", limit=520),
            _sentence(f"{label} replay proof reconstructs {state_object} with actor, timestamp, status, result, and explanation.", limit=520),
            _sentence(f"{label} blocked-path proof keeps missing input, failed validation, access limits, or privacy issues visible before a result is trusted.", limit=520),
            _sentence(f"{label} release proof stays within the accepted product promise: {proof_boundary}", limit=520),
        ]
        changed |= _set_list(release_plan, "promotion_criteria", criteria)
        stages = release_plan.get("release_stages")
        if isinstance(stages, list) and stages and isinstance(stages[0], dict):
            changed |= _set_text(stages[0], "release_gate", proof_success)
    return changed


def _repair_validation_strategy(proposal: dict[str, Any], *, release_selector: str) -> bool:
    release = greenfield_programs.proposal_release_selector(proposal, release_selector)
    label = completion_text.project_title(proposal)
    state_object = completion_text.state_object(proposal)
    action = completion_text.action_phrase(proposal)
    outcome = completion_text.outcome_phrase(proposal)
    outcome_action = completion_text.outcome_action_phrase(outcome)
    rows = [
        _sentence(f"Success proof: release {release} proves the first path by letting a representative user {action}; the user can {outcome_action}.", limit=700),
        _sentence(f"Blocked-path proof: missing input, invalid state, failed validation, absent explanation, or unresolved review blocks readiness for {state_object}.", limit=520),
        _sentence(f"Replay proof: {state_object} can be reconstructed with actor, timestamp, prior state, current state, result, and explanation.", limit=520),
        _sentence(f"Access and privacy proof: only authorized actors can view or mutate protected state, and audit, retention, privacy, accessibility, and safety obligations stay visible.", limit=520),
        _sentence(
            "Each owned product behavior must prove its successful path and explain what happens when required information is missing.",
            limit=520,
        ),
        _sentence(f"Release proof: {label} cannot promote unless validation output proves the visible product outcome and stays inside the first-release promise.", limit=520),
    ]
    return _set_list(proposal, "validation_strategy", rows)


def _repair_backlog_success_language(proposal: dict[str, Any], *, release_selector: str) -> bool:
    release = greenfield_programs.proposal_release_selector(proposal, release_selector)
    label = completion_text.project_title(proposal)
    state_object = completion_text.state_object(proposal)
    action = completion_text.action_phrase(proposal)
    outcome = completion_text.outcome_phrase(proposal)
    outcome_action = completion_text.outcome_action_phrase(outcome)
    changed = False
    for row in dict_rows(proposal.get("backlog")):
        title = _clean(row.get("title")) or label
        metrics = [
            _sentence(f"{title} proves the first path in release {release}: a representative user can {action} and {outcome_action}.", limit=700),
            _sentence(f"{title} explains missing or invalid information before the product shows a result.", limit=500),
            _sentence(f"{title} preserves enough {state_object} context to explain the actor, status, result, and recovery path.", limit=500),
            _sentence(f"{title} stays inside the first-release promise and keeps deferred outcomes out of the success claim.", limit=500),
        ]
        if _sequence_needs_repair(row.get("success_metrics"), required_tokens=("success", "block", "replay", "evidence")):
            changed |= _set_list(row, "success_metrics", metrics, limit=1000)
        validation = [
            _sentence(f"Validate a successful {title} path, a blocked path, replay, role access, privacy handling, and evidence visibility.", limit=360),
            _sentence(f"Reject release readiness when {title} cannot explain its result, changed state, access posture, or recovery path.", limit=420),
        ]
        if _sequence_needs_repair(row.get("validation"), required_tokens=("success", "block", "replay")):
            changed |= _set_list(row, "validation", validation)
    return changed


def _repair_project_intelligence_validation(proposal: dict[str, Any], *, release_selector: str) -> bool:
    intelligence = proposal.get("project_intelligence")
    if not isinstance(intelligence, dict):
        return False
    release = greenfield_programs.proposal_release_selector(proposal, release_selector)
    state_object = completion_text.state_object(proposal)
    action = completion_text.action_phrase(proposal)
    outcome = completion_text.outcome_phrase(proposal)
    outcome_action = completion_text.outcome_action_phrase(outcome)
    rows = [
        _sentence(f"Validate that a representative user can {action} and {outcome_action}.", limit=420),
        _sentence(f"Validate a blocked path where missing input, invalid state, failed validation, or missing explanation prevents readiness.", limit=420),
        _sentence(f"Validate replay for {state_object} with actor, timestamp, status, result, and explanation.", limit=420),
        _sentence(f"Validate role-appropriate access, privacy, audit, retention, accessibility, safety, and recovery behavior before release {release}.", limit=420),
        _sentence("Validate that release proof stays inside the accepted product promise without borrowing deferred outcomes.", limit=500),
    ]
    return _set_list(intelligence, "validation_obligations", rows)


def _repair_generated_sentence_lists(proposal: dict[str, Any], *, release_selector: str) -> bool:
    changed = False
    release = greenfield_programs.proposal_release_selector(proposal, release_selector)
    state_object = completion_text.state_object(proposal)
    action = completion_text.action_phrase(proposal)
    outcome = completion_text.outcome_phrase(proposal)
    if _validation_strategy_needs_repair(proposal):
        changed |= _repair_validation_strategy(proposal, release_selector=release_selector)
    for row in dict_rows(proposal.get("backlog")):
        title = _clean(row.get("title")) or completion_text.project_title(proposal)
        changed |= _repair_bad_scalar(
            row,
            "problem",
            fallback=f"{title} matters because users need {outcome} to be correct, understandable, and recoverable when information is missing.",
        )
        changed |= _repair_bad_scalar(row, "customer", fallback=completion_text.actor_summary(proposal))
        changed |= _repair_bad_scalar(
            row,
            "opportunity",
            fallback=f"{title} gives the team a small release slice where a representative user can {action} before broader variants are added.",
        )
        changed |= _repair_bad_scalar(
            row,
            "product_view",
            fallback=f"{title} is useful when users can {action}, see {outcome}, and recover from bad or incomplete input.",
        )
        changed |= _repair_bad_scalar(
            row,
            "domain_risk",
            fallback=f"Domain risk: {title} can mislead users if {state_object} changes without a clear result explanation and recovery path.",
        )
        changed |= _repair_bad_scalar(
            row,
            "security_posture",
            fallback=f"Security posture: {title} states who can see or change the product state, what sensitive information is involved, and how recovery stays visible before release.",
        )
        if _sequence_has_text_repair(row.get("success_metrics")):
            outcome_action = completion_text.outcome_action_phrase(outcome)
            metrics = [
                f"{title} proves the first path in release {release}: a representative user can {action} and {outcome_action}.",
                f"{title} explains missing or invalid information before the product shows a result.",
                f"{title} preserves enough {state_object} context to explain the actor, status, result, and recovery path.",
                f"{title} stays inside the first-release promise without borrowing deferred outcomes.",
            ]
            changed |= _set_list(
                row,
                "success_metrics",
                metrics,
            )
            changed |= _repair_domain_intelligence_metrics(row, title=title, action=action, outcome=outcome, state_object=state_object)
        if _sequence_has_text_repair(row.get("validation")):
            changed |= _set_list(
                row,
                "validation",
                [
                    f"Validate a successful {title} path, a blocked path, replay, role access, privacy handling, and evidence visibility.",
                    f"Reject release readiness when {title} cannot explain its result, changed state, access posture, or recovery path.",
                ],
            )
        changed |= _repair_domain_intelligence_metrics(row, title=title, action=action, outcome=outcome, state_object=state_object)
        if _sequence_has_text_repair(row.get("rationale_lines")):
            changed |= _set_list(
                row,
                "rationale_lines",
                [
                    f"- why now: {title} belongs in release {release} because it helps produce the first user-visible outcome.",
                    f"- expected outcome: {title} produces a visible result with blocked and recovery paths.",
                    f"- tradeoff: {title} keeps the first slice narrow while deferring broader variants until their own outcome is proven.",
                    f"- deferred for now: {title} does not expand into adjacent workflows outside the first-release promise.",
                    f"- ranking basis: {title} ranks ahead of optional work because it protects the result, recovery path, and user trust.",
                ],
            )
    changed |= repair_component_sentence_lists(proposal)
    for index, row in enumerate(dict_rows(proposal.get("diagrams")), start=1):
        changed |= _repair_bad_scalar(row, "title", fallback=completion_text.diagram_title(row, proposal=proposal, index=index))
        changed |= _repair_bad_scalar(
            row,
            "summary",
            fallback=f"Shows how {completion_text.project_title(proposal)} preserves first-path state, evidence, and proof.",
        )
    return changed


def _repair_domain_intelligence_metrics(
    row: dict[str, Any],
    *,
    title: str,
    action: str,
    outcome: str,
    state_object: str,
) -> bool:
    intelligence = row.get("domain_intelligence")
    if not isinstance(intelligence, dict):
        return False
    if not _sequence_has_text_repair(intelligence.get("metrics")):
        return False
    outcome_action = completion_text.outcome_action_phrase(outcome)
    return _set_list(
        intelligence,
        "metrics",
        [
            f"{title} proves users can {action} and {outcome_action}.",
            f"Every readiness assertion for {title} has state, explanation, validation, release-review, and non-goal references.",
            f"{title} keeps {state_object} clear when the result is blocked, corrected, or replayed.",
        ],
    )


def _ensure_text(row: dict[str, Any], key: str, default: str, *, repair_bad_text: bool = False) -> bool:
    if _clean(row.get(key)) and not (repair_bad_text and _text_needs_repair(row.get(key))):
        return False
    row[key] = default
    return True


def _repair_bad_scalar(row: dict[str, Any], key: str, *, fallback: str = "") -> bool:
    if not _text_needs_repair(row.get(key)):
        return False
    value = fallback or _clean(row.get(key))
    return _set_text(row, key, value)


__all__ = ["complete_confirmed_proposal", "greenfield_repair_until_clean"]
