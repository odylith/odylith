"""Domain-intelligence sentence-list repair for confirmed greenfield payloads."""

from __future__ import annotations

from typing import Any

from odylith.runtime.domain_intelligence import greenfield_confirmed_completion_text_model as completion_text
from odylith.runtime.domain_intelligence.greenfield_confirmed_completion_quality import (
    sequence_has_text_repair,
)
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import set_sentence_list


def repair_domain_intelligence_metrics(
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
    if not sequence_has_text_repair(intelligence.get("metrics")):
        return False
    outcome_action = completion_text.outcome_action_phrase(outcome)
    return set_sentence_list(
        intelligence,
        "metrics",
        [
            f"{title} proof shows users can {action}.",
            f"{title} result evidence proves the user can {outcome_action}.",
            f"Every readiness assertion for {title} has state, explanation, validation, release-review, and non-goal references.",
            f"{title} keeps {state_object} clear when the result is blocked, corrected, or replayed.",
        ],
    )


def repair_domain_intelligence_sentence_lists(
    row: dict[str, Any],
    *,
    title: str,
    action: str,
    outcome: str,
    state_object: str,
    proof_boundary: str,
    actor_summary: str,
    primary_actor: str,
) -> bool:
    intelligence = row.get("domain_intelligence")
    if not isinstance(intelligence, dict):
        return False
    outcome_action = completion_text.outcome_action_phrase(outcome)
    actor_ref = (actor_summary or f"{title} users and reviewers").strip(" .")
    changed = False
    if sequence_has_text_repair(intelligence.get("actors")):
        changed |= set_sentence_list(intelligence, "actors", [actor_ref])
    if sequence_has_text_repair(intelligence.get("scope")):
        changed |= set_sentence_list(
            intelligence,
            "scope",
            [
                f"{title} starts with {primary_actor} who can {action}.",
                f"{title} stays inside the first release until the product can {outcome_action} and explain blocked input.",
            ],
        )
    if sequence_has_text_repair(intelligence.get("ontology")):
        changed |= set_sentence_list(
            intelligence,
            "ontology",
            [
                f"Actors include {actor_ref}.",
                f"State object: {state_object}.",
                f"Visible result: {outcome}.",
                f"Proof boundary: {proof_boundary}.",
            ],
        )
    if sequence_has_text_repair(intelligence.get("state")):
        changed |= set_sentence_list(
            intelligence,
            "state",
            [
                f"State focus: {title} records the facts needed to support {action}.",
                f"{state_object} remains trustworthy when the visible result, blocker, and recovery path can be replayed.",
            ],
        )
    if sequence_has_text_repair(intelligence.get("authority")):
        changed |= set_sentence_list(
            intelligence,
            "authority",
            [
                f"{actor_ref} can move first-path state only through the accepted product behavior.",
                f"{title} blocks release readiness when validation, replay, access, or explanation is incomplete.",
            ],
        )
    return changed


__all__ = [
    "repair_domain_intelligence_metrics",
    "repair_domain_intelligence_sentence_lists",
]
