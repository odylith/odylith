"""Completion gate for confirmed greenfield project artifacts."""

from __future__ import annotations

import copy
import re
from collections.abc import Mapping, Sequence
from typing import Any

from odylith.runtime.common.prose_grammar import base_action_clause
from odylith.runtime.common.prose_grammar import looks_like_finite_action
from odylith.runtime.domain_intelligence import greenfield_programs
from odylith.runtime.domain_intelligence.greenfield_component_contract import (
    boundary_from_contract,
    contract_is_complete,
    dependencies_from_contract,
    ensure_component_contract,
    interfaces_from_contract,
    responsibility_from_contract,
    risks_from_contract,
    validation_from_contract,
)
from odylith.runtime.domain_intelligence.greenfield_component_contract_quality import normalize_contract
from odylith.runtime.domain_intelligence.greenfield_component_contract_differentiation import (
    differentiate_component_contracts,
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
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import first_path_action_phrase
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import first_path_capability_phrase
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import first_path_outcome_phrase
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
            project_title=_project_title(payload),
            first_path=_first_path(payload),
            state_object=_state_object(payload),
            proof_boundary=_proof_boundary(payload),
            text_needs_repair=_text_needs_repair,
        )
        changed |= _complete_backlog(payload)
        changed |= _complete_components(payload)
        changed |= differentiate_component_contracts(payload)
        changed |= _reconcile_backlog_with_components(payload)
        changed |= _complete_semantic_model(
            payload,
            title=_project_title(payload),
            state_object=_state_object(payload),
            first_path=_first_path(payload),
            proof_boundary=_proof_boundary(payload),
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
        label = _project_title(proposal)
        outcome = _outcome_phrase(proposal)
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
        action = _action_phrase(proposal)
        outcome = _outcome_phrase(proposal)
        proposal["validation_strategy"] = list(
            unique_text(
                [
                    *(validation if isinstance(validation, list) else []),
                    f"A representative user completes the first path by {action}; the product reaches {outcome}.",
                    f"{_state_object(proposal)} can be reconstructed with actor, timestamp, status, and result.",
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
    capability = _capability_phrase(proposal)
    action = _action_phrase(proposal)
    outcome = _outcome_phrase(proposal)
    state = _state_object(proposal)
    actors = _actor_summary(proposal)
    for index, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            continue
        title = _clean(row.get("title")) or f"{_project_title(proposal)} Workstream {index}"
        label = _workstream_subject(row, fallback=title)
        if not _clean(row.get("problem")) or _text_needs_repair(row.get("problem")):
            row["problem"] = _workstream_problem(label=label, action=action, outcome=outcome, state=state)
            changed = True
        if not _clean(row.get("customer")) or _text_needs_repair(row.get("customer")):
            row["customer"] = actors
            changed = True
        if not _clean(row.get("opportunity")) or _text_needs_repair(row.get("opportunity")):
            row["opportunity"] = _workstream_opportunity(label=label, action=action, outcome=outcome)
            changed = True
        if not _clean(row.get("product_view")) or _text_needs_repair(row.get("product_view")):
            row["product_view"] = _workstream_product_view(label=label, action=action, outcome=outcome)
            changed = True
        metrics = list(text_values(row.get("success_metrics")))
        if len(metrics) < 3 or _sequence_has_text_repair(row.get("success_metrics")):
            row["success_metrics"] = list(
                unique_text(
                    [
                        f"A representative user completes the first path by {action}; the product reaches {outcome}.",
                        f"Missing or incorrect input produces a clear correction path instead of a misleading result.",
                        f"The result can be explained from the recorded {state} without relying on memory or hidden assumptions.",
                    ]
                )
            )
            changed = True
        if not _clean(row.get("domain_risk")) or _text_needs_repair(row.get("domain_risk")):
            row["domain_risk"] = _workstream_risk(label=label, outcome=outcome, state=state)
            changed = True
        if not _clean(row.get("security_posture")) or _text_needs_repair(row.get("security_posture")):
            row["security_posture"] = f"Security posture: {label} protects user-entered facts, result history, and recovery details."
            changed = True
        if not text_values(row.get("risks")) or _sequence_has_text_repair(row.get("risks")):
            row["risks"] = [
                row["domain_risk"],
                row["security_posture"],
            ]
            changed = True
    return changed


def _complete_components(proposal: dict[str, Any]) -> bool:
    rows = proposal.get("components")
    if not isinstance(rows, list):
        return False
    changed = False
    for index, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            continue
        label = _component_label(row, index)
        previous_label = _component_label(rows[index - 2], index - 1) if index > 1 and isinstance(rows[index - 2], Mapping) else ""
        next_label = _component_label(rows[index], index + 1) if index < len(rows) and isinstance(rows[index], Mapping) else ""
        existing_contract = row.get("component_contract")
        if isinstance(existing_contract, Mapping) and contract_is_complete(existing_contract):
            contract = normalize_contract(existing_contract)
            if row.get("component_contract") != contract:
                row["component_contract"] = contract
                changed = True
        else:
            contract = ensure_component_contract(
                row,
                proposal=proposal,
                previous_label=previous_label,
                next_label=next_label,
            )
            if row.get("component_contract") != contract:
                row["component_contract"] = contract
                changed = True
        if _component_field_is_weak(row.get("responsibility")):
            row["responsibility"] = responsibility_from_contract(label, contract)
            changed = True
        if _component_field_is_weak(row.get("boundary")):
            row["boundary"] = boundary_from_contract(label, contract)
            changed = True
        if _component_sequence_is_weak(row.get("interfaces")):
            row["interfaces"] = interfaces_from_contract(contract)
            changed = True
        else:
            changed |= _ensure_list(row, "interfaces", _component_interfaces(row, label, contract))
        if _component_sequence_is_weak(row.get("dependencies")):
            row["dependencies"] = dependencies_from_contract(contract)
            changed = True
        else:
            changed |= _ensure_list(row, "dependencies", _component_dependencies(row, label, proposal, contract))
        if _component_sequence_is_weak(row.get("validation")):
            row["validation"] = validation_from_contract(contract)
            changed = True
        else:
            changed |= _ensure_list(row, "validation", _component_validation(row, label, proposal, contract))
        if _component_sequence_is_weak(row.get("risks")):
            row["risks"] = risks_from_contract(label, contract)
            changed = True
        else:
            changed |= _ensure_list(row, "risks", _component_risks(row, label, proposal, contract))
        changed |= _ensure_text(row, "status", "planned")
        changed |= _ensure_text(row, "qualification", "candidate")
        changed |= _ensure_text(row, "evidence_tier", "user_intent")
    return changed


def _reconcile_backlog_with_components(proposal: dict[str, Any]) -> bool:
    rows = _dict_rows(proposal.get("backlog"))
    components = _dict_rows(proposal.get("components"))
    if len(rows) < 2 or not components:
        return False
    by_id = {_clean(component.get("component_id")): component for component in components if _clean(component.get("component_id"))}
    intent = proposal.get("intent") if isinstance(proposal.get("intent"), Mapping) else {}
    non_goal_rows = [row for row in text_values(proposal.get("non_goals") or intent.get("non_goals")) if _clean(row)]
    if not non_goal_rows:
        proof = _proof_boundary(proposal)
        match = re.search(r"\bwithout\s+claiming\s+(?P<scope>[^.;]+)", proof, flags=re.IGNORECASE)
        if match:
            non_goal_rows = [f"No {match.group('scope').strip()}"]
    changed = False
    for row in rows[1:]:
        component = _primary_component_for_backlog(row, components=components, by_id=by_id)
        if not component:
            continue
        contract = component.get("component_contract") if isinstance(component.get("component_contract"), Mapping) else {}
        if not contract:
            continue
        title = _clean(row.get("title")) or _component_label(component, 0)
        label = _component_label(component, 0)
        state_object = _state_object(proposal)
        focus = _component_focus_phrase(label=label, contract=contract, fallback=state_object)
        action = _action_phrase(proposal)
        outcome = _outcome_phrase(proposal)
        outcome_sentence = _lower_first(outcome)
        drifted = _row_drifted_from_component(row, component)
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
                f"{label} proves one complete user path that reaches {outcome_sentence}.",
                f"{label} explains blocked, missing, or invalid information before the product shows a result.",
                f"{label} preserves actor, source, status, result, and recovery context for each {state_object} change.",
            ]
            if _row_is_release_proof(row):
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
        if _sequence_needs_repair(row.get("validation"), required_tokens=("success", "block"), min_items=1) or drifted:
            row["validation"] = [
                f"Validate one successful {label} path, one missing-input path, and one corrected path against the visible product outcome.",
            ]
            changed = True
    return changed


def _capability_phrase(proposal: Mapping[str, Any]) -> str:
    return first_path_capability_phrase(_first_path(proposal), fallback="complete the first product path", limit=220)


def _action_phrase(proposal: Mapping[str, Any]) -> str:
    """Return the material user-side action without folding in the final result."""

    action = first_path_action_phrase(_first_path(proposal), fallback="complete the first product action", max_fragments=1)
    return _base_user_action_phrase(action) or "complete the first product action"


def _base_user_action_phrase(value: str) -> str:
    text = _clean(value).strip(" .")
    if not text:
        return ""
    text = re.sub(r"^(?:a|an|the)\s+", "", text, flags=re.IGNORECASE)
    words = text.split()
    for index in range(1, min(len(words), 6)):
        candidate = " ".join(words[index:]).strip(" .")
        if looks_like_finite_action(candidate):
            return base_action_clause(candidate)
    return base_action_clause(text)


def _outcome_phrase(proposal: Mapping[str, Any]) -> str:
    return first_path_outcome_phrase(
        _first_path(proposal),
        proof_boundary=_proof_boundary(proposal),
        fallback="the promised user-visible result",
    )


def _workstream_subject(row: Mapping[str, Any], *, fallback: str) -> str:
    component = _clean(next(iter(text_values(row.get("component_focus"))), ""))
    title = _clean(row.get("title")) or fallback
    if component:
        return _human_label(component)
    return re.sub(r"^(?:make|build|show|keep|let)\s+", "", title, flags=re.I).strip(" .") or title


def _human_label(value: str) -> str:
    text = _clean(value).strip(" .")
    if not text:
        return ""
    if "-" in text or "_" in text:
        words = [word for word in re.split(r"[-_\s]+", text) if word]
        dropped_prefix: list[str] = []
        while words and len(words) > 4 and words[0].casefold() not in {"owner", "user", "admin", "reviewer", "operator"}:
            dropped_prefix.append(words.pop(0))
            if len(dropped_prefix) >= 3:
                break
        text = " ".join(words or dropped_prefix)
    return " ".join(word[:1].upper() + word[1:] if not word.isupper() else word for word in text.split())


def _workstream_problem(*, label: str, action: str, outcome: str, state: str) -> str:
    return _sentence(
        f"{label} matters because users do not get value from {action} until it produces {outcome} and leaves {state} understandable when something is missing or corrected.",
        limit=520,
    )


def _workstream_opportunity(*, label: str, action: str, outcome: str) -> str:
    return _sentence(
        f"Build the narrow behavior in {label} that lets one representative user {action} and reach {outcome}.",
        limit=420,
    )


def _workstream_product_view(*, label: str, action: str, outcome: str) -> str:
    return _sentence(
        f"{label} is complete when the user can {action}, understand {outcome}, and recover cleanly from a bad or incomplete attempt.",
        limit=520,
    )


def _workstream_risk(*, label: str, outcome: str, state: str) -> str:
    return _sentence(
        f"Risk: {label} can create false confidence if {outcome} is shown while {state} is incomplete, stale, or hard to explain.",
        limit=420,
    )


def _component_focus_phrase(*, label: str, contract: Mapping[str, Any], fallback: str) -> str:
    if label_focus := _label_focus_phrase(label):
        return label_focus
    label_terms = _keywords([label])
    blocked_terms = {
        *label_terms,
        "actor",
        "boundary",
        "blocker",
        "component",
        "downstream",
        "evidence",
        "handoff",
        "input",
        "local",
        "output",
        "proof",
        "release",
        "service",
        "sibling",
        "source",
        "state",
        "upstream",
        "validation",
    }
    candidates: list[str] = []
    for value in text_values(contract.get("owned_state")):
        for part in re.split(r",|;|\band\b", value):
            phrase = _clean(part).strip(" .")
            terms = _keywords([phrase])
            if not phrase or len(phrase.split()) > 5 or not terms or terms <= blocked_terms:
                continue
            candidates.append(phrase)
    if candidates:
        return _sentence("; ".join(candidates[:2]), fallback=fallback, limit=120).rstrip(".")
    return _sentence(fallback, fallback="component state", limit=120).rstrip(".")


def _label_focus_phrase(label: str) -> str:
    words = [
        word
        for word in re.findall(r"[A-Za-z0-9][A-Za-z0-9-]*", _clean(label).casefold())
        if word not in {"adapter", "component", "engine", "service", "surface", "system", "view"}
    ]
    return " ".join(words[:5]).strip()


def _primary_component_for_backlog(
    row: Mapping[str, Any],
    *,
    components: Sequence[dict[str, Any]],
    by_id: Mapping[str, dict[str, Any]],
) -> dict[str, Any] | None:
    for ref in text_values(row.get("component_focus")):
        if component := by_id.get(_clean(ref)):
            return component
    title_terms = _keywords([row.get("title")])
    scored: list[tuple[int, int, dict[str, Any]]] = []
    for index, component in enumerate(components):
        score = len(title_terms & _keywords([component.get("label"), component.get("component_id")]))
        if score:
            scored.append((score, -index, component))
    scored.sort(reverse=True)
    return scored[0][2] if scored else None


def _row_drifted_from_component(row: Mapping[str, Any], component: Mapping[str, Any]) -> bool:
    label_terms = _keywords([component.get("label"), component.get("component_id")])
    row_terms = _keywords([row.get("title"), row.get("product_view"), row.get("recommended_first_slice")])
    if not label_terms:
        return False
    return len(label_terms & row_terms) < min(2, len(label_terms))


def _row_is_release_proof(row: Mapping[str, Any]) -> bool:
    text = " ".join(text_values([row.get("title"), row.get("product_view"), row.get("recommended_first_slice")])).casefold()
    return "proof" in text or "release evidence" in text or "release readiness" in text


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
        slug = _clean(row.get("slug")) or f"{_slug_title(proposal)}-diagram-{index}"
        changed |= _ensure_text(row, "slug", slug)
        changed |= _ensure_text(row, "title", _diagram_title(row, proposal=proposal, index=index), repair_bad_text=True)
        changed |= _ensure_text(row, "kind", "flowchart")
        changed |= _ensure_text(
            row,
            "summary",
            f"Shows how {_project_title(proposal)} preserves first-path state, evidence, and proof.",
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
    label = _project_title(proposal)
    state_object = _state_object(proposal)
    proof_boundary = _proof_boundary(proposal)
    capability = _capability_phrase(proposal)
    action = _action_phrase(proposal)
    outcome = _outcome_phrase(proposal)
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
            _sentence(f"{label} success proof shows a representative user can {action} and reach {outcome}.", limit=520),
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
    label = _project_title(proposal)
    state_object = _state_object(proposal)
    capability = _capability_phrase(proposal)
    action = _action_phrase(proposal)
    outcome = _outcome_phrase(proposal)
    rows = [
        _sentence(f"Success proof: release {release} proves the first path by letting a representative user {action}; the product reaches {outcome}.", limit=700),
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
    label = _project_title(proposal)
    state_object = _state_object(proposal)
    capability = _capability_phrase(proposal)
    action = _action_phrase(proposal)
    outcome = _outcome_phrase(proposal)
    changed = False
    for row in _dict_rows(proposal.get("backlog")):
        title = _clean(row.get("title")) or label
        metrics = [
            _sentence(f"{title} proves the first path in release {release}: a representative user can {action}, and the product reaches {outcome}.", limit=700),
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
    label = _project_title(proposal)
    state_object = _state_object(proposal)
    capability = _capability_phrase(proposal)
    action = _action_phrase(proposal)
    outcome = _outcome_phrase(proposal)
    rows = [
        _sentence(f"Validate that a representative user can {action} and reach {outcome}.", limit=420),
        _sentence(f"Validate a blocked path where missing input, invalid state, failed validation, or missing explanation prevents readiness.", limit=420),
        _sentence(f"Validate replay for {state_object} with actor, timestamp, status, result, and explanation.", limit=420),
        _sentence(f"Validate role-appropriate access, privacy, audit, retention, accessibility, safety, and recovery behavior before release {release}.", limit=420),
        _sentence("Validate that release proof stays inside the accepted product promise without borrowing deferred outcomes.", limit=500),
    ]
    return _set_list(intelligence, "validation_obligations", rows)


def _repair_generated_sentence_lists(proposal: dict[str, Any], *, release_selector: str) -> bool:
    changed = False
    release = greenfield_programs.proposal_release_selector(proposal, release_selector)
    state_object = _state_object(proposal)
    capability = _capability_phrase(proposal)
    action = _action_phrase(proposal)
    outcome = _outcome_phrase(proposal)
    if _validation_strategy_needs_repair(proposal):
        changed |= _repair_validation_strategy(proposal, release_selector=release_selector)
    for row in _dict_rows(proposal.get("backlog")):
        title = _clean(row.get("title")) or _project_title(proposal)
        changed |= _repair_bad_scalar(
            row,
            "problem",
            fallback=f"{title} matters because users need {outcome} to be correct, understandable, and recoverable when information is missing.",
        )
        changed |= _repair_bad_scalar(row, "customer", fallback=_actor_summary(proposal))
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
            metrics = [
                f"{title} proves the first path in release {release}: a representative user can {action}, and the product reaches {outcome}.",
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
    for row in _dict_rows(proposal.get("components")):
        contract = row.get("component_contract") if isinstance(row.get("component_contract"), Mapping) else {}
        label = _component_label(row, 0)
        if _text_needs_repair(row.get("responsibility")):
            changed |= _set_text(row, "responsibility", responsibility_from_contract(label, contract))
        if _text_needs_repair(row.get("boundary")):
            changed |= _set_text(row, "boundary", boundary_from_contract(label, contract))
        if _sequence_has_text_repair(row.get("interfaces")):
            changed |= _set_list(row, "interfaces", interfaces_from_contract(contract))
        if _sequence_has_text_repair(row.get("dependencies")):
            changed |= _set_list(row, "dependencies", dependencies_from_contract(contract))
        if _sequence_has_text_repair(row.get("validation")):
            changed |= _set_list(row, "validation", validation_from_contract(contract))
        if _sequence_has_text_repair(row.get("risks")):
            changed |= _set_list(row, "risks", risks_from_contract(label, contract))
    for index, row in enumerate(_dict_rows(proposal.get("diagrams")), start=1):
        changed |= _repair_bad_scalar(row, "title", fallback=_diagram_title(row, proposal=proposal, index=index))
        changed |= _repair_bad_scalar(
            row,
            "summary",
            fallback=f"Shows how {_project_title(proposal)} preserves first-path state, evidence, and proof.",
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
    return _set_list(
        intelligence,
        "metrics",
        [
            f"{title} proves users can {action} and the product reaches {outcome}.",
            f"Every readiness assertion for {title} has state, explanation, validation, release-review, and non-goal references.",
            f"{title} keeps {state_object} clear when the result is blocked, corrected, or replayed.",
        ],
    )


def _dict_rows(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [row for row in value if isinstance(row, dict)]


def _component_interfaces(row: Mapping[str, Any], label: str, contract: Mapping[str, Any]) -> list[str]:
    return interfaces_from_contract(contract)


def _component_dependencies(
    row: Mapping[str, Any],
    label: str,
    proposal: Mapping[str, Any],
    contract: Mapping[str, Any],
) -> list[str]:
    return dependencies_from_contract(contract)


def _component_validation(
    row: Mapping[str, Any],
    label: str,
    proposal: Mapping[str, Any],
    contract: Mapping[str, Any],
) -> list[str]:
    return validation_from_contract(contract)


def _component_risks(
    row: Mapping[str, Any],
    label: str,
    proposal: Mapping[str, Any],
    contract: Mapping[str, Any],
) -> list[str]:
    values = risks_from_contract(label, contract)
    first_path = _first_path(proposal)
    state_object = _state_object(proposal)
    context = _best_context_line(row=row, proposal=proposal)
    values.append(
        f"Operational mitigation: {label} must show blocked and recovery behavior before people rely on {state_object}: {first_path}"
    )
    if context:
        values.append(f"Accepted-intent constraint: {label} must preserve this risk or policy condition: {context}")
    return list(unique_text(values))


def _best_context_line(*, row: Mapping[str, Any], proposal: Mapping[str, Any]) -> str:
    component_words = _keywords([row.get("label", ""), row.get("responsibility", ""), row.get("boundary", "")])
    candidates = _context_candidates(proposal)
    scored: list[tuple[int, str]] = []
    for candidate in candidates:
        words = _keywords([candidate])
        overlap = len(component_words & words)
        risk_bonus = 3 if _riskish(candidate) else 0
        scored.append((overlap + risk_bonus, candidate))
    scored.sort(key=lambda item: (-item[0], len(item[1])))
    return scored[0][1] if scored and scored[0][0] > 0 else ""


def _context_candidates(proposal: Mapping[str, Any]) -> list[str]:
    values: list[str] = []
    values.extend(text_values(proposal.get("assumptions")))
    values.extend(text_values(proposal.get("open_questions")))
    values.extend(text_values(proposal.get("risks")))
    values.extend(text_values(proposal.get("security_compliance")))
    values.extend(text_values(proposal.get("validation_strategy")))
    intelligence = proposal.get("project_intelligence")
    if isinstance(intelligence, Mapping):
        for key in ("constraints", "risks", "validation_obligations", "change_model", "invalidation_rules"):
            values.extend(text_values(intelligence.get(key)))
    return [_sentence(value, limit=260) for value in unique_text(values) if _clean(value)]


def _riskish(value: str) -> bool:
    text = value.casefold()
    return any(
        token in text
        for token in (
            "risk",
            "privacy",
            "safety",
            "consent",
            "access",
            "retention",
            "audit",
            "confidence",
            "blocked",
            "failure",
            "security",
            "compliance",
            "policy",
            "uncertainty",
            "claim",
        )
    )


def _keywords(values: Sequence[Any]) -> set[str]:
    words: set[str] = set()
    for value in values:
        for raw in str(value or "").replace("_", " ").replace("-", " ").split():
            word = "".join(char for char in raw.casefold() if char.isalnum())
            if len(word) >= 4:
                words.add(word)
    return words


def _component_field_is_weak(value: Any) -> bool:
    text = _clean(value).casefold()
    if not text:
        return True
    if _text_needs_repair(value):
        return True
    generic_markers = (
        "responsibility and keeps it tied",
        "accepted first path",
        "assigned state, command, evidence",
        "records review evidence",
        "this component boundary",
        "first implementation plan must name",
    )
    return any(marker in text for marker in generic_markers) or len(text.split()) < 6


def _component_sequence_is_weak(value: Any) -> bool:
    rows = list(text_values(value))
    if not rows:
        return True
    if _sequence_has_text_repair(rows):
        return True
    text = " ".join(_clean(row).casefold() for row in rows)
    generic_markers = (
        "command, query, event, or visible-state contract",
        "normal path, blocked path",
        "accepted input, produced state",
        "first implementation plan must name",
        "valid transition, invalid input rejection",
        "release proof checks this component",
    )
    return any(marker in text for marker in generic_markers)


def _ensure_list(row: dict[str, Any], key: str, defaults: Sequence[str]) -> bool:
    existing = list(text_values(row.get(key)))
    merged = list(unique_text([*existing, *defaults]))
    if existing == merged and existing:
        return False
    row[key] = merged
    return True


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


def _component_label(row: Mapping[str, Any], index: int) -> str:
    return _clean(row.get("label")) or _clean(row.get("component_id")) or f"Component {index}"


def _title(proposal: Mapping[str, Any], suffix: str) -> str:
    return f"{_project_title(proposal)} {suffix}"


def _project_title(proposal: Mapping[str, Any]) -> str:
    intent = proposal.get("intent") if isinstance(proposal.get("intent"), Mapping) else {}
    return _clean(intent.get("title")) if isinstance(intent, Mapping) else "Confirmed Project"


def _slug_title(proposal: Mapping[str, Any]) -> str:
    return "-".join(word for word in _project_title(proposal).casefold().replace("_", " ").split() if word) or "confirmed-project"


def _diagram_title(row: Mapping[str, Any], *, proposal: Mapping[str, Any], index: int) -> str:
    slug = _clean(row.get("slug"))
    project_slug = _slug_title(proposal)
    suffix = slug
    if slug.startswith(f"{project_slug}-"):
        suffix = slug[len(project_slug) + 1 :]
    words = [word for word in re.split(r"[-_\s]+", suffix) if word]
    if words:
        title = " ".join(word[:1].upper() + word[1:] for word in words)
        lowered = title.casefold()
        if not any(token in lowered for token in ("view", "diagram", "sequence", "context", "proof", "flow")):
            title = f"{title} View"
        return title
    return f"Architecture View {index}"


def _first_path(proposal: Mapping[str, Any]) -> str:
    intent = proposal.get("intent") if isinstance(proposal.get("intent"), Mapping) else {}
    return _sentence(
        intent.get("first_path") if isinstance(intent, Mapping) else "",
        fallback="the accepted first path",
        limit=900,
    )


def _proof_boundary(proposal: Mapping[str, Any]) -> str:
    intent = proposal.get("intent") if isinstance(proposal.get("intent"), Mapping) else {}
    return _sentence(intent.get("proof_boundary") if isinstance(intent, Mapping) else "", fallback="the promised user-visible result")


def _state_object(proposal: Mapping[str, Any]) -> str:
    intent = proposal.get("intent") if isinstance(proposal.get("intent"), Mapping) else {}
    if isinstance(intent, Mapping) and _clean(intent.get("state_object")):
        return _sentence(intent.get("state_object"), fallback="the accepted state")
    intelligence = proposal.get("project_intelligence")
    if isinstance(intelligence, Mapping):
        for value in text_values(intelligence.get("ontology")):
            if "state object:" in value.casefold():
                return _sentence(value.split(":", 1)[1], fallback="the accepted state")
    return "the accepted state"


def _actor_summary(proposal: Mapping[str, Any]) -> str:
    intelligence = proposal.get("project_intelligence")
    if isinstance(intelligence, Mapping):
        actors = [value for value in text_values(intelligence.get("operators")) if not _text_needs_repair(value)][:2]
        if actors:
            return _sentence("; ".join(actors), limit=280)
    return f"{_project_title(proposal)} users, reviewers, owners, and release decision makers"


def _lower_first(value: str) -> str:
    text = _clean(value).strip()
    if not text:
        return ""
    if text[:2].isupper():
        return text
    return text[:1].lower() + text[1:]


__all__ = ["complete_confirmed_proposal", "greenfield_repair_until_clean"]
