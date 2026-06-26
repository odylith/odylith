"""Shared risk projection for greenfield workstream artifacts."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from odylith.runtime.common.value_coercion import dedupe_strings
from odylith.runtime.domain_intelligence import greenfield_confirmed_completion_text_model as completion_text
from odylith.runtime.domain_intelligence.greenfield_domain_term_index import ordered_terms
from odylith.runtime.domain_intelligence.greenfield_text import text_values


def domain_risk_for_row(row: Mapping[str, Any], proposal: Mapping[str, Any]) -> str:
    """Return the workstream-owned risk text without repeating global risk on children."""

    local = _row_text_tuple(row, "domain_risk", "risk_posture", "risks")
    if local:
        if not is_parent_backlog_row(row, proposal) and _all_claims_repeat_parent(local, proposal):
            return derived_child_workstream_risk(row=row, proposal=proposal)
        return " ".join(local).strip()
    proposal_risk = proposal_posture_text(proposal, "risks", "security_compliance")
    if not proposal_risk:
        return ""
    if is_parent_backlog_row(row, proposal):
        return proposal_risk
    return derived_child_workstream_risk(row=row, proposal=proposal)


def workstream_risk_lines(
    *,
    row: Mapping[str, Any],
    proposal: Mapping[str, Any],
    proposal_risks: Sequence[str],
    local_risks: Sequence[str] | None = None,
) -> list[str]:
    """Return Radar risk bullets for one workstream without cloning parent risk."""

    local = [str(item).strip() for item in (local_risks if local_risks is not None else text_values(row.get("risks"))) if str(item).strip()]
    if local:
        if is_parent_backlog_row(row, proposal):
            return local
        derived = derived_child_workstream_risk(row=row, proposal=proposal)
        filtered = [item for item in local if not _claim_repeats_any_parent(item, proposal_risks)]
        if len(filtered) != len(local):
            return dedupe_strings([derived, *filtered])
        return local
    if is_parent_backlog_row(row, proposal):
        return list(proposal_risks[:3])
    if proposal_risks:
        return [derived_child_workstream_risk(row=row, proposal=proposal)]
    return []


def proposal_posture_text(proposal: Mapping[str, Any], *keys: str) -> str:
    rows: list[str] = []
    for key in keys:
        rows.extend(text_values(proposal.get(key)))
    return " ".join(dedupe_strings(rows)).strip()


def _row_text_tuple(row: Mapping[str, Any], *keys: str) -> tuple[str, ...]:
    for key in keys:
        values = text_values(row.get(key))
        if values:
            return tuple(values)
    return ()


def is_parent_backlog_row(row: Mapping[str, Any], proposal: Mapping[str, Any]) -> bool:
    rows = [item for item in proposal.get("backlog", []) if isinstance(item, Mapping)]
    if not rows:
        return True
    first = rows[0]
    if row is first:
        return True
    title = str(row.get("title", "")).strip()
    first_title = str(first.get("title", "")).strip()
    return bool(title and first_title and title == first_title)


def derived_child_workstream_risk(*, row: Mapping[str, Any], proposal: Mapping[str, Any]) -> str:
    components = [item for item in proposal.get("components", []) if isinstance(item, Mapping)]
    title = str(row.get("title", "")).strip()
    label = completion_text.workstream_subject(row, fallback=title or "This workstream", components=components)
    risk = completion_text.workstream_risk(
        label=label,
        outcome=completion_text.outcome_phrase(proposal),
        state=completion_text.state_reference(proposal),
    ).strip()
    if risk.casefold().startswith("risk: "):
        return risk[6:].strip()
    return risk


def _all_claims_repeat_parent(values: Sequence[str], proposal: Mapping[str, Any]) -> bool:
    proposal_risks = text_values(proposal.get("risks"))
    if not proposal_risks:
        return False
    local = [str(item).strip() for item in values if str(item).strip()]
    return bool(local) and all(_claim_repeats_any_parent(item, proposal_risks) for item in local)


def _claim_repeats_any_parent(value: str, proposal_risks: Sequence[str]) -> bool:
    return any(_same_semantic_claim(value, candidate) for candidate in proposal_risks)


def _same_semantic_claim(left: str, right: str) -> bool:
    left_terms = _claim_terms(left)
    right_terms = _claim_terms(right)
    if not left_terms or not right_terms:
        return False
    if left_terms == right_terms:
        return True
    overlap = len(left_terms & right_terms)
    return overlap >= 5 and (overlap / max(len(left_terms), len(right_terms))) >= 0.86


def _claim_terms(value: str) -> set[str]:
    return set(ordered_terms(value, minimum=3, stopwords=_CLAIM_STOPWORDS))


_CLAIM_STOPWORDS = frozenset(
    {
        "and",
        "are",
        "before",
        "for",
        "from",
        "into",
        "risk",
        "risks",
        "that",
        "the",
        "this",
        "with",
        "would",
    }
)


__all__ = [
    "derived_child_workstream_risk",
    "domain_risk_for_row",
    "is_parent_backlog_row",
    "proposal_posture_text",
    "workstream_risk_lines",
]
