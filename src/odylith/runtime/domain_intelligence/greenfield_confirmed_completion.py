"""Completion gate for confirmed greenfield project artifacts."""

from __future__ import annotations

import copy
import re
from collections.abc import Mapping, Sequence
from typing import Any

from odylith.runtime.analysis_engine.types import slugify
from odylith.runtime.domain_intelligence import greenfield_programs
from odylith.runtime.domain_intelligence.greenfield_component_contract import (
    boundary_from_contract,
    component_contract_issues,
    contract_is_complete,
    dependencies_from_contract,
    ensure_component_contract,
    interfaces_from_contract,
    public_prose_quality_issues,
    responsibility_from_contract,
    risks_from_contract,
    validation_from_contract,
)
from odylith.runtime.domain_intelligence.greenfield_component_contract_differentiation import (
    component_spec_preflight_issues,
    differentiate_component_contracts,
)
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent_completion import complete_confirmed_intent
from odylith.runtime.domain_intelligence.greenfield_confirmed_project_intelligence import complete_project_intelligence
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import clean_generated_text as _clean
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import sentence_text as _sentence
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import set_sentence_list as _set_list
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import set_sentence_text as _set_text
from odylith.runtime.domain_intelligence.greenfield_text import text_values
from odylith.runtime.domain_intelligence.greenfield_text import unique_text
from odylith.runtime.domain_intelligence.proposal_tribunal import run_greenfield_tribunal
from odylith.runtime.domain_intelligence.proposal_validation import collect_host_reasoned_proposal_issues
from odylith.runtime.domain_intelligence.proposal_validation import format_proposal_issue_report
from odylith.runtime.domain_intelligence.project_intelligence_binding import attach_project_intelligence_bindings
from odylith.runtime.governance import artifact_tribunal


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
        changed |= _repair_project_title(payload)
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


def _repair_project_title(proposal: dict[str, Any]) -> bool:
    intent = proposal.get("intent")
    if not isinstance(intent, dict):
        return False
    current = _clean(intent.get("title"))
    if not current:
        return False
    if not _project_title_needs_repair(current):
        return False
    existing_candidate = _existing_project_title_candidate(proposal, current=current)
    seed = {
        "title": existing_candidate or current,
        "product_story": intent.get("product_story") or _project_intelligence_first_row(proposal, "intent"),
        "state_object": _state_object(proposal),
        "first_path": _first_path(proposal),
        "proof_boundary": _proof_boundary(proposal),
        "human_actors": _project_intelligence_rows(proposal, "operators"),
        "internal_systems": _component_system_rows(proposal),
        "assumptions": text_values(proposal.get("assumptions")),
        "ambiguities": text_values(proposal.get("open_questions")),
        "non_goals": text_values(proposal.get("non_goals")),
    }
    repaired = complete_confirmed_intent(seed)
    replacement = _clean(repaired.get("title"))
    if not replacement or replacement == current:
        return False
    _replace_title_text(proposal, current=current, replacement=replacement)
    repaired_intent = proposal.get("intent")
    if isinstance(repaired_intent, dict):
        repaired_intent["title"] = replacement
        repaired_intent["project_slug"] = slugify(replacement)
    rebound = attach_project_intelligence_bindings(proposal)
    proposal.clear()
    proposal.update(rebound)
    return True


def _project_title_needs_repair(value: str) -> bool:
    text = _clean(value)
    words = re.findall(r"[A-Za-z0-9]+", text)
    if not text or not words:
        return True
    if text.casefold() in {"greenfield project", "confirmed project"}:
        return True
    if words[-1].casefold() in {"a", "an", "and", "for", "from", "in", "of", "on", "or", "the", "to", "with"}:
        return True
    return len(words) > 10 and bool(
        re.search(r"\b(?:that|what|so|because|captures?|follows?|makes?|buying|doing|needs?|wants?)\b", text, re.IGNORECASE)
    )


def _existing_project_title_candidate(proposal: Mapping[str, Any], *, current: str) -> str:
    candidates: list[str] = []
    release_plan = proposal.get("release_plan")
    if isinstance(release_plan, Mapping):
        candidates.extend(_title_candidates_from_text(release_plan.get("label")))
        candidates.extend(_title_candidates_from_text(release_plan.get("strategy")))
    program = proposal.get("program")
    if isinstance(program, Mapping):
        candidates.extend(_title_candidates_from_text(program.get("recommended_first_wave")))
        blueprint = program.get("blueprint")
        if isinstance(blueprint, Mapping):
            candidates.extend(_title_candidates_from_text(blueprint.get("parent_workstream")))
            candidates.extend(_title_candidates_from_text(blueprint.get("child_workstream_strategy")))
    project_brief = proposal.get("project_brief")
    if isinstance(project_brief, Mapping):
        candidates.extend(_title_candidates_from_text(project_brief.get("purpose")))
        candidates.extend(_title_candidates_from_text(project_brief.get("project_outcome")))
    intelligence = proposal.get("project_intelligence")
    if isinstance(intelligence, Mapping):
        candidates.extend(_title_candidates_from_text(intelligence.get("purpose")))
        candidates.extend(_title_candidates_from_text(intelligence.get("coding_posture")))
    for candidate in candidates:
        if _title_candidate_is_better(candidate, current=current):
            return candidate
    return ""


def _title_candidates_from_text(value: Any) -> list[str]:
    text = _clean(value).strip(" .")
    if not text:
        return []
    rows: list[str] = []
    patterns = (
        r"^Ship\s+(?P<title>.+?)\s+First\s+Release$",
        r"^(?P<title>.+?)\s+\d+(?:\.\d+){1,2}\s+first\s+path\b",
        r"^(?P<title>.+?)\s+first[-\s]path\s+proof\b",
        r"^(?P<title>.+?)\s+state\s+and\s+evidence\s+boundary\b",
        r"^(?P<title>.+?)\s+release\s+review\b",
        r"^(?P<title>.+?)\s+translates\s+the\s+accepted\b",
        r"^Promote\s+(?P<title>.+?)\s+only\s+after\b",
    )
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            rows.append(_clean(match.group("title")))
    return rows


def _title_candidate_is_better(value: str, *, current: str) -> bool:
    candidate = _clean(value).strip(" .")
    if not candidate or candidate == current:
        return False
    words = re.findall(r"[A-Za-z0-9]+", candidate)
    if not 2 <= len(words) <= 8:
        return False
    if words[-1].casefold() in {"a", "an", "and", "for", "from", "in", "of", "on", "or", "the", "to", "with"}:
        return False
    lowered = candidate.casefold()
    if lowered in {"greenfield project", "confirmed project"}:
        return False
    if re.search(r"\b(?:that|what|so that|because|captures?|follows?|make money)\b", lowered):
        return False
    return True


def _project_intelligence_rows(proposal: Mapping[str, Any], key: str) -> tuple[str, ...]:
    intelligence = proposal.get("project_intelligence")
    if not isinstance(intelligence, Mapping):
        return ()
    return text_values(intelligence.get(key))


def _project_intelligence_first_row(proposal: Mapping[str, Any], key: str) -> str:
    rows = _project_intelligence_rows(proposal, key)
    return rows[0] if rows else ""


def _component_system_rows(proposal: Mapping[str, Any]) -> tuple[str, ...]:
    rows: list[str] = []
    for component in _mapping_rows(proposal.get("components")):
        label = _clean(component.get("label"))
        description = _clean(component.get("source_system_description")) or _clean(component.get("responsibility"))
        if label and description:
            rows.append(f"{label} — {description}")
        elif label:
            rows.append(label)
    return tuple(rows)


def _replace_title_text(value: Any, *, current: str, replacement: str) -> None:
    if isinstance(value, dict):
        for key, nested in list(value.items()):
            if isinstance(nested, str):
                value[key] = nested.replace(current, replacement)
            else:
                _replace_title_text(nested, current=current, replacement=replacement)
    elif isinstance(value, list):
        for index, nested in enumerate(list(value)):
            if isinstance(nested, str):
                value[index] = nested.replace(current, replacement)
            else:
                _replace_title_text(nested, current=current, replacement=replacement)


def _complete_project_posture(proposal: dict[str, Any]) -> bool:
    changed = False
    risks = proposal.get("risks")
    if not isinstance(risks, list) or not risks or _sequence_has_text_repair(risks):
        proposal["risks"] = [
            _risk_row(
                "RISK-001",
                _title(proposal, "first-path proof can be too weak"),
                (
                    f"If the accepted first path is not proven with visible evidence, {_project_title(proposal)} "
                    f"can produce records that look ready while the product outcome remains untrusted: {_first_path(proposal)}"
                ),
                "Keep release proof tied to the accepted first path, state object, validation output, and reviewer decision.",
            ),
            _risk_row(
                "RISK-002",
                _title(proposal, "safety, privacy, or policy posture can be under-modeled"),
                (
                    f"If access, private data handling, audit, retention, accessibility, safety, and abuse controls "
                    f"are not explicit, {_project_title(proposal)} can cross its accepted proof boundary: {_proof_boundary(proposal)}"
                ),
                "Make domain risk, security posture, and compliance policy visible before any governed record writes.",
            ),
        ]
        changed = True
    posture = proposal.get("security_compliance")
    if not isinstance(posture, Mapping) or not text_values(posture) or _sequence_has_text_repair(posture):
        label = _project_title(proposal)
        proposal["security_compliance"] = {
            "domain": (
                f"{label} carries domain risk around the accepted state object, first path, proof boundary, "
                "failure handling, and user decisions made from incomplete evidence."
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
        proposal["validation_strategy"] = list(
            unique_text(
                [
                    *(validation if isinstance(validation, list) else []),
                    f"The accepted first path passes end to end: {_first_path(proposal)}",
                    f"The state object can be reconstructed with actor, source, timestamp, and evidence references: {_state_object(proposal)}",
                    f"The proof boundary blocks release readiness when validation, replay, access, privacy, safety, or reviewer evidence is missing: {_proof_boundary(proposal)}",
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
    for index, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            continue
        title = _clean(row.get("title")) or f"{_project_title(proposal)} Workstream {index}"
        if not _clean(row.get("problem")) or _text_needs_repair(row.get("problem")):
            row["problem"] = (
                f"{title} is required because the accepted product cannot be trusted unless the first path, "
                f"state object, evidence, and proof boundary stay connected: {_first_path(proposal)}"
            )
            changed = True
        if not _clean(row.get("customer")) or _text_needs_repair(row.get("customer")):
            row["customer"] = _actor_summary(proposal)
            changed = True
        if not _clean(row.get("opportunity")) or _text_needs_repair(row.get("opportunity")):
            row["opportunity"] = (
                f"Build the smallest useful product slice for {title}: {_first_path(proposal)}"
            )
            changed = True
        if not _clean(row.get("product_view")) or _text_needs_repair(row.get("product_view")):
            row["product_view"] = (
                f"{title} is useful when the user can complete the first path and inspect the resulting state, blockers, and evidence."
            )
            changed = True
        metrics = list(text_values(row.get("success_metrics")))
        if len(metrics) < 3 or _sequence_has_text_repair(row.get("success_metrics")):
            row["success_metrics"] = list(
                unique_text(
                    [
                        *metrics,
                        f"The accepted first path can be exercised end to end: {_first_path(proposal)}",
                        f"{_state_object(proposal)} records success, blocked, stale, and review-needed states.",
                        f"Proof evidence blocks promotion unless it matches the accepted boundary: {_proof_boundary(proposal)}",
                    ]
                )
            )
            changed = True
        if not _clean(row.get("domain_risk")) or _text_needs_repair(row.get("domain_risk")):
            row["domain_risk"] = (
                f"Domain risk: {title} can mislead operators if it loses the accepted product context, state object, "
                f"reviewer evidence, or release proof: {_proof_boundary(proposal)}"
            )
            changed = True
        if not _clean(row.get("security_posture")) or _text_needs_repair(row.get("security_posture")):
            row["security_posture"] = (
                f"Security posture: {title} keeps authorization, ownership, access control, private data handling, "
                "audit, privacy, retention, accessibility, and safety obligations explicit before promotion."
            )
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
            contract = existing_contract
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
        owned = _fragment(contract.get("owned_state"), fallback=f"{label} owned state", limit=260)
        inputs = _fragment(contract.get("accepted_inputs"), fallback="accepted local inputs", limit=220)
        outputs = _fragment(contract.get("produced_outputs"), fallback="local output and handoff", limit=220)
        states = _fragment(contract.get("states_or_transitions"), fallback="success, blocked, and handed-off states", limit=180)
        proof = _first_text(contract.get("local_proof")) or f"{label} proves its local inputs, outputs, blockers, and handoff."
        drifted = _row_drifted_from_component(row, component)
        if _text_needs_repair(row.get("product_view")) or drifted:
            proof_tail = (
                " It keeps reviewer decision, release proof, deferred scope, and recovery evidence visible."
                if _row_is_release_proof(row)
                else ""
            )
            row["product_view"] = (
                f"{label} owns {owned}. It accepts {inputs}, produces {outputs}, and keeps {states} visible for {title}.{proof_tail}"
            )
            changed = True
        if _text_needs_repair(row.get("recommended_first_slice")) or drifted:
            row["recommended_first_slice"] = (
                f"Implement {label} around its local inputs, outputs, blocked states, sibling refusals, and downstream handoff."
            )
            changed = True
        if _sequence_needs_repair(row.get("success_metrics"), required_tokens=("success", "block", "evidence"), min_items=3) or drifted:
            metrics = [
                f"{label} accepts its required inputs and produces the expected local output: {outputs}.",
                f"{label} blocks readiness when required input, access, state, validation, or evidence is missing.",
                f"{label} keeps its local proof separate from sibling responsibilities: {proof}",
            ]
            if _row_is_release_proof(row):
                metrics.append(
                    f"{label} keeps the accepted release proof boundary visible: {_fragment(_proof_boundary(proposal), fallback='the accepted release proof boundary', limit=260)}."
                )
            row["success_metrics"] = metrics
            changed = True
        if _sequence_needs_repair(row.get("interfaces"), required_tokens=("input", "output"), min_items=1) or drifted:
            row["interfaces"] = [
                f"{label} input contract: {inputs}.",
                f"{label} output contract: {outputs}.",
            ]
            changed = True
        if _sequence_needs_repair(row.get("validation"), required_tokens=("success", "block"), min_items=1) or drifted:
            row["validation"] = [
                f"Validate {label} success, blocked, invalid-input, access, replay, and handoff behavior against its local proof.",
            ]
            changed = True
    return changed


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


def _first_text(value: Any) -> str:
    values = text_values(value)
    return _sentence(values[0], limit=260) if values else ""


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


def _preflight_issues(proposal: Mapping[str, Any], *, release_selector: str) -> list[str]:
    issues: list[str] = []
    issues.extend(collect_host_reasoned_proposal_issues(proposal))
    issues.extend(component_contract_issues(proposal))
    issues.extend(component_spec_preflight_issues(proposal))
    selector = greenfield_programs.proposal_release_selector(proposal, release_selector)
    tribunal = run_greenfield_tribunal(proposal, release_selector=selector)
    issues.extend(tribunal.issues)
    issues.extend(_artifact_issues(proposal))
    return list(unique_text(issues))


def _artifact_issues(proposal: Mapping[str, Any]) -> list[str]:
    issues: list[str] = []
    for index, row in enumerate(_mapping_rows(proposal.get("backlog")), start=1):
        decision = artifact_tribunal.run_governed_artifact_tribunal(
            artifact_kind="backlog",
            payload={
                "title": row.get("title", ""),
                "problem": row.get("problem", ""),
                "customer": row.get("customer", ""),
                "opportunity": row.get("opportunity", ""),
                "product_view": row.get("product_view", ""),
                "success_metrics": row.get("success_metrics", ""),
                "risks": [row.get("domain_risk", ""), row.get("security_posture", ""), row.get("risks", "")],
                "validation": row.get("validation", ""),
            },
        )
        issues.extend(f"backlog row {index}: {issue}" for issue in decision.issues)
    for index, row in enumerate(_mapping_rows(proposal.get("components")), start=1):
        decision = artifact_tribunal.run_governed_artifact_tribunal(
            artifact_kind="component",
            payload={
                "component_id": row.get("component_id", ""),
                "label": row.get("label", ""),
                "path": row.get("intended_path", "") or row.get("path", ""),
                "kind": row.get("kind", ""),
                "responsibility": row.get("responsibility", ""),
                "boundary": row.get("boundary", ""),
                "interfaces": row.get("interfaces", ""),
                "dependencies": row.get("dependencies", ""),
                "validation": row.get("validation", ""),
                "risks": row.get("risks", ""),
            },
        )
        issues.extend(f"component row {index}: {issue}" for issue in decision.issues)
    for index, row in enumerate(_mapping_rows(proposal.get("diagrams")), start=1):
        decision = artifact_tribunal.run_governed_artifact_tribunal(
            artifact_kind="atlas_diagram",
            payload={
                "diagram_id": row.get("diagram_id", "") or f"DRAFT-{index:03d}",
                "slug": row.get("slug", ""),
                "title": row.get("title", ""),
                "kind": row.get("kind", ""),
                "owner": row.get("owner", "repo"),
                "summary": row.get("summary", ""),
                "components": row.get("components", "") or row.get("related_components", ""),
                "watch_paths": row.get("watch_paths", ""),
                "related_backlog": row.get("related_backlog", "") or row.get("related_diagrams", ""),
                "related_code": row.get("related_code", ""),
            },
        )
        issues.extend(f"diagram row {index}: {issue}" for issue in decision.issues)
    return issues


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
    first_path = _first_path(proposal)
    state_object = _state_object(proposal)
    proof_boundary = _proof_boundary(proposal)
    proof_success = _sentence(
        f"Release {release} succeeds only when {label} completes the accepted first path, records {state_object}, "
        f"shows reviewer-visible evidence, and blocks readiness when the accepted proof boundary is missing: {proof_boundary}",
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
            _sentence(f"{label} success proof exercises the accepted first path end to end: {first_path}", limit=520),
            _sentence(f"{label} replay proof reconstructs {state_object} with actor, source, timestamp, status, and evidence references.", limit=520),
            _sentence(f"{label} blocked-path proof prevents release readiness when required input, validation, access, privacy, or evidence is missing.", limit=520),
            _sentence(f"{label} release proof matches the accepted proof boundary and keeps deferred scope visible: {proof_boundary}", limit=520),
        ]
        changed |= _set_list(release_plan, "promotion_criteria", criteria)
        stages = release_plan.get("release_stages")
        if isinstance(stages, list) and stages and isinstance(stages[0], dict):
            changed |= _set_text(stages[0], "release_gate", proof_success)
    return changed


def _repair_validation_strategy(proposal: dict[str, Any], *, release_selector: str) -> bool:
    release = greenfield_programs.proposal_release_selector(proposal, release_selector)
    label = _project_title(proposal)
    first_path = _first_path(proposal)
    state_object = _state_object(proposal)
    proof_boundary = _proof_boundary(proposal)
    rows = [
        _sentence(f"Success proof: release {release} completes the accepted first path and produces a reviewer-visible result: {first_path}", limit=520),
        _sentence(f"Blocked-path proof: missing input, invalid state, failed validation, absent evidence, or unresolved review blocks readiness for {state_object}.", limit=520),
        _sentence(f"Replay proof: {state_object} can be reconstructed with actor, source, timestamp, prior state, current state, evidence reference, and outcome.", limit=520),
        _sentence(f"Access and privacy proof: only authorized actors can view or mutate protected state, and audit, retention, privacy, accessibility, and safety obligations stay visible.", limit=520),
        _sentence(f"Component proof: every generated component proves its own inputs, outputs, transitions, sibling refusals, unique failure, upstream truth, and downstream handoff.", limit=520),
        _sentence(f"Release proof: {label} cannot promote unless validation output satisfies the accepted proof boundary: {proof_boundary}", limit=520),
    ]
    return _set_list(proposal, "validation_strategy", rows)


def _repair_backlog_success_language(proposal: dict[str, Any], *, release_selector: str) -> bool:
    release = greenfield_programs.proposal_release_selector(proposal, release_selector)
    label = _project_title(proposal)
    first_path = _first_path(proposal)
    state_object = _state_object(proposal)
    proof_boundary = _proof_boundary(proposal)
    changed = False
    for row in _dict_rows(proposal.get("backlog")):
        title = _clean(row.get("title")) or label
        metrics = [
            _sentence(f"{title} proves the accepted success path for release {release}: {first_path}", limit=500),
            _sentence(f"{title} blocks readiness when required input, state, access, privacy, validation, or evidence is missing.", limit=500),
            _sentence(f"{title} keeps {state_object} replayable with actor, source, timestamp, status, and evidence references.", limit=500),
            _sentence(f"{title} release evidence matches the accepted proof boundary: {proof_boundary}", limit=500),
        ]
        if _sequence_needs_repair(row.get("success_metrics"), required_tokens=("success", "block", "replay", "evidence")):
            changed |= _set_list(row, "success_metrics", metrics)
        validation = [
            _sentence(f"Validate success, blocked, replay, access, privacy, and evidence paths for {title}.", limit=360),
            _sentence(f"Reject release readiness when {title} cannot explain its state change, source evidence, reviewer decision, or recovery path.", limit=420),
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
    proof_boundary = _proof_boundary(proposal)
    rows = [
        _sentence(f"Validate the {label} success path from first input to reviewer-visible outcome.", limit=360),
        _sentence(f"Validate a blocked path where missing input, invalid state, failed validation, or missing evidence prevents release readiness.", limit=420),
        _sentence(f"Validate replay for {state_object} with actor, source, timestamp, status, evidence reference, and outcome.", limit=420),
        _sentence(f"Validate role-appropriate access, privacy, audit, retention, accessibility, safety, and recovery behavior before release {release}.", limit=420),
        _sentence(f"Validate that release proof satisfies the accepted proof boundary: {proof_boundary}", limit=500),
    ]
    return _set_list(intelligence, "validation_obligations", rows)


def _repair_generated_sentence_lists(proposal: dict[str, Any], *, release_selector: str) -> bool:
    changed = False
    release = greenfield_programs.proposal_release_selector(proposal, release_selector)
    first_path = _first_path(proposal)
    state_object = _state_object(proposal)
    proof_boundary = _proof_boundary(proposal)
    if _validation_strategy_needs_repair(proposal):
        changed |= _repair_validation_strategy(proposal, release_selector=release_selector)
    for row in _dict_rows(proposal.get("backlog")):
        title = _clean(row.get("title")) or _project_title(proposal)
        changed |= _repair_bad_scalar(
            row,
            "problem",
            fallback=f"{title} keeps the accepted product state, user action, and proof evidence connected for the first path: {first_path}",
        )
        changed |= _repair_bad_scalar(row, "customer", fallback=_actor_summary(proposal))
        changed |= _repair_bad_scalar(
            row,
            "opportunity",
            fallback=f"{title} gives the team a small release slice that proves the accepted path before broader variants are added: {first_path}",
        )
        changed |= _repair_bad_scalar(
            row,
            "product_view",
            fallback=f"{title} is useful when users can complete the first path and see the resulting state, blockers, and evidence.",
        )
        changed |= _repair_bad_scalar(
            row,
            "domain_risk",
            fallback=f"Domain risk: {title} can mislead users if {state_object} changes without clear source evidence, reviewer decision, and recovery path.",
        )
        changed |= _repair_bad_scalar(
            row,
            "security_posture",
            fallback=f"Security posture: {title} keeps authorization, private data handling, audit, retention, privacy, and recovery controls visible before release.",
        )
        if _sequence_has_text_repair(row.get("success_metrics")):
            changed |= _set_list(
                row,
                "success_metrics",
                [
                    f"{title} proves the accepted success path for release {release}: {first_path}",
                    f"{title} blocks readiness when required input, state, access, privacy, validation, or evidence is missing.",
                    f"{title} keeps {state_object} replayable with actor, source, timestamp, status, and evidence references.",
                    f"{title} release evidence matches the accepted proof boundary: {proof_boundary}",
                ],
            )
        if _sequence_has_text_repair(row.get("validation")):
            changed |= _set_list(
                row,
                "validation",
                [
                    f"Validate success, blocked, replay, access, privacy, and evidence paths for {title}.",
                    f"Reject release readiness when {title} cannot explain its state change, source evidence, decision, or recovery path.",
                ],
            )
        if _sequence_has_text_repair(row.get("rationale_lines")):
            changed |= _set_list(
                row,
                "rationale_lines",
                [
                    f"- why now: {title} belongs in release {release} because it proves part of the accepted first path.",
                    f"- expected outcome: {title} produces visible state, evidence, blockers, and recovery information for review.",
                    f"- tradeoff: {title} keeps the first slice narrow while deferring broader variants until their proof exists.",
                    f"- deferred for now: {title} does not expand into adjacent workflows that are outside the accepted proof boundary.",
                    f"- ranking basis: {title} ranks ahead of optional work because it protects state ownership, risk clarity, and release evidence.",
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


def _validation_strategy_needs_repair(proposal: Mapping[str, Any]) -> bool:
    return _sequence_needs_repair(
        proposal.get("validation_strategy"),
        required_tokens=("success", "block", "replay", "access", "privacy", "evidence"),
        min_items=6,
    )


def _sequence_needs_repair(value: Any, *, required_tokens: Sequence[str], min_items: int = 2) -> bool:
    values = text_values(value)
    if len(values) < min_items:
        return True
    joined = " ".join(values).casefold()
    if any(token not in joined for token in required_tokens):
        return True
    return any(_text_needs_repair(item) for item in values)


def _sequence_has_text_repair(value: Any) -> bool:
    return any(_text_needs_repair(item) for item in text_values(value))


def _text_needs_repair(value: Any) -> bool:
    text = _clean(value)
    if not text:
        return False
    if public_prose_quality_issues(text):
        return True
    if _sentence_needs_repair(text):
        return True
    lowered = text.casefold()
    return any(
        marker in lowered
        for marker in (
            "responsibility and keeps it tied",
            "with clear ownership, protected access, required",
        )
    )


def _sentence_needs_repair(value: Any) -> bool:
    text = _clean(value)
    if not text:
        return True
    if _has_bad_tail(text):
        return True
    if re.search(r"\.\s+(?:and|or)\b", text, flags=re.IGNORECASE):
        return True
    if re.search(
        r"\b(?:inspect\s+The|verifies\s+that\s+The|shows\s+whether\s+The|Human\s+actors\s*:|plus\s+\d+\s+more|preserves\s+handles|maintains\s+defines|accepting\s+eligible)",
        text,
        flags=re.IGNORECASE,
    ):
        return True
    if re.search(r"\brefuses\b[^.]{0,140}\brefuses\b", text, flags=re.IGNORECASE):
        return True
    if re.search(r"\bscor\b", text, flags=re.IGNORECASE):
        return True
    return False


def _proof_boundary_is_weak(value: str) -> bool:
    text = _clean(value).casefold()
    if len(text.split()) < 14:
        return True
    return not ("success" in text or "succeeds" in text or "proof" in text) or not (
        "evidence" in text or "trace" in text or "review" in text
    )


def _has_bad_tail(value: str) -> bool:
    words = _clean(value).rstrip(".;:, ").split()
    if len(words) < 6:
        return False
    return words[-1].casefold().strip(".,;:") in {"a", "an", "and", "for", "from", "of", "or", "the", "to", "with"}


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
    proof = _proof_boundary(proposal)
    first_path = _first_path(proposal)
    state_object = _state_object(proposal)
    context = _best_context_line(row=row, proposal=proposal)
    values.append(
        f"Operational mitigation: {label} must expose local blockers and recovery evidence before release readiness can trust {state_object}: {first_path}"
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


def _mapping_rows(value: Any) -> list[Mapping[str, Any]]:
    if not isinstance(value, list):
        return []
    return [row for row in value if isinstance(row, Mapping)]


def _risk_row(identifier: str, title: str, statement: str, mitigation: str) -> dict[str, str]:
    return {
        "id": identifier,
        "title": title,
        "statement": statement,
        "severity": "high",
        "mitigation": mitigation,
    }


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
    return _sentence(intent.get("first_path") if isinstance(intent, Mapping) else "", fallback="the accepted first path")


def _proof_boundary(proposal: Mapping[str, Any]) -> str:
    intent = proposal.get("intent") if isinstance(proposal.get("intent"), Mapping) else {}
    return _sentence(intent.get("proof_boundary") if isinstance(intent, Mapping) else "", fallback="the accepted proof boundary")


def _state_object(proposal: Mapping[str, Any]) -> str:
    intelligence = proposal.get("project_intelligence")
    if isinstance(intelligence, Mapping):
        for value in text_values(intelligence.get("ontology")):
            if "state object:" in value.casefold():
                return _sentence(value.split(":", 1)[1], fallback="the accepted state object")
    return "the accepted state object"


def _actor_summary(proposal: Mapping[str, Any]) -> str:
    intelligence = proposal.get("project_intelligence")
    if isinstance(intelligence, Mapping):
        actors = [value for value in text_values(intelligence.get("operators")) if not _text_needs_repair(value)][:2]
        if actors:
            return _sentence("; ".join(actors), limit=280)
    return f"{_project_title(proposal)} users, reviewers, owners, and release decision makers"


def _fragment(value: Any, *, fallback: str, limit: int = 180) -> str:
    return _sentence(value, fallback=fallback, limit=limit).rstrip(".")


__all__ = ["complete_confirmed_proposal", "greenfield_repair_until_clean"]
