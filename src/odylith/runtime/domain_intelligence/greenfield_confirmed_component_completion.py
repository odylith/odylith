"""Component-row completion for confirmed greenfield proposals."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from odylith.runtime.domain_intelligence import greenfield_confirmed_completion_text_model as completion_text
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
from odylith.runtime.domain_intelligence.greenfield_confirmed_completion_quality import (
    sequence_has_text_repair as _sequence_has_text_repair,
)
from odylith.runtime.domain_intelligence.greenfield_confirmed_completion_quality import (
    text_needs_repair as _text_needs_repair,
)
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import clean_generated_text as _clean
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import sentence_text as _sentence
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import set_sentence_list as _set_list
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import set_sentence_text as _set_text
from odylith.runtime.domain_intelligence.greenfield_rows import dict_rows
from odylith.runtime.domain_intelligence.greenfield_text import text_values
from odylith.runtime.domain_intelligence.greenfield_text import unique_text


def complete_component_rows(proposal: dict[str, Any]) -> bool:
    rows = proposal.get("components")
    if not isinstance(rows, list):
        return False
    changed = False
    for index, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            continue
        label = completion_text.component_label(row, index)
        previous_label = (
            completion_text.component_label(rows[index - 2], index - 1)
            if index > 1 and isinstance(rows[index - 2], Mapping)
            else ""
        )
        next_label = (
            completion_text.component_label(rows[index], index + 1)
            if index < len(rows) and isinstance(rows[index], Mapping)
            else ""
        )
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
            changed |= _ensure_component_list(row, "interfaces", interfaces_from_contract(contract))
        if _component_sequence_is_weak(row.get("dependencies")):
            row["dependencies"] = dependencies_from_contract(contract)
            changed = True
        else:
            changed |= _ensure_component_list(row, "dependencies", dependencies_from_contract(contract))
        if _component_sequence_is_weak(row.get("validation")):
            row["validation"] = validation_from_contract(contract)
            changed = True
        else:
            changed |= _ensure_component_list(row, "validation", validation_from_contract(contract))
        if _component_sequence_is_weak(row.get("risks")):
            row["risks"] = risks_from_contract(label, contract)
            changed = True
        else:
            changed |= _ensure_component_list(row, "risks", _component_risks(row, label, proposal, contract))
        changed |= _ensure_component_text(row, "status", "planned")
        changed |= _ensure_component_text(row, "qualification", "candidate")
        changed |= _ensure_component_text(row, "evidence_tier", "user_intent")
    return changed


def repair_component_sentence_lists(proposal: Mapping[str, Any]) -> bool:
    changed = False
    for row in dict_rows(proposal.get("components")):
        contract = row.get("component_contract") if isinstance(row.get("component_contract"), Mapping) else {}
        label = completion_text.component_label(row, 0)
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
    return changed


def _component_risks(
    row: Mapping[str, Any],
    label: str,
    proposal: Mapping[str, Any],
    contract: Mapping[str, Any],
) -> list[str]:
    values = risks_from_contract(label, contract)
    action = completion_text.action_phrase(proposal)
    outcome = completion_text.outcome_phrase(proposal)
    state_object = completion_text.state_object(proposal)
    context = _best_context_line(row=row, proposal=proposal)
    values.append(
        f"Operational mitigation: {label} must show blocked and recovery behavior before people rely on {state_object}; the first path must prove {action} leads to {outcome}."
    )
    if context:
        values.append(f"Accepted-intent constraint: {label} must preserve this risk or policy condition: {context}")
    return list(unique_text(values))


def _best_context_line(*, row: Mapping[str, Any], proposal: Mapping[str, Any]) -> str:
    component_words = completion_text.keywords([row.get("label", ""), row.get("responsibility", ""), row.get("boundary", "")])
    candidates = _context_candidates(proposal)
    scored: list[tuple[int, str]] = []
    for candidate in candidates:
        words = completion_text.keywords([candidate])
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
    starts = [(_clean(row).split(" ", 1)[0] or "").casefold() for row in rows]
    if any(starts.count(prefix) > 1 for prefix in ("accepts", "produces", "renders")):
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


def _ensure_component_list(row: dict[str, Any], key: str, defaults: Sequence[str]) -> bool:
    existing = list(text_values(row.get(key)))
    merged = list(unique_text([*existing, *defaults]))
    if existing == merged and existing:
        return False
    row[key] = merged
    return True


def _ensure_component_text(row: dict[str, Any], key: str, default: str) -> bool:
    if _clean(row.get(key)):
        return False
    row[key] = default
    return True


__all__ = ["complete_component_rows", "repair_component_sentence_lists"]
