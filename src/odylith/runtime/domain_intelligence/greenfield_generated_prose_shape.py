"""Domain-neutral shape checks for generated greenfield prose."""

from __future__ import annotations

import re

from odylith.runtime.common.prose_grammar import base_gerund_clause
from odylith.runtime.common.prose_grammar import looks_like_finite_action
from odylith.runtime.domain_intelligence.greenfield_actor_led_prefix import looks_like_actor_led_subject_prefix

_ACTOR_ROLE_TERMS = frozenset(
    {
        "actor",
        "actors",
        "applicant",
        "applicants",
        "coordinator",
        "coordinators",
        "customer",
        "customers",
        "lead",
        "leads",
        "manager",
        "managers",
        "officer",
        "officers",
        "operator",
        "operators",
        "owner",
        "owners",
        "participant",
        "participants",
        "person",
        "people",
        "planner",
        "planners",
        "reviewer",
        "reviewers",
        "staff",
        "team",
        "user",
        "users",
    }
)


def actor_led_finite_action_inside_user_can(value: str) -> bool:
    """Return whether a modal user-capability clause swallowed an actor subject."""

    for tokens in _token_segments(value):
        lowered = [token.casefold() for token in tokens]
        for index in range(0, max(0, len(tokens) - 2)):
            if lowered[index] not in {"user", "users"} or lowered[index + 1] != "can":
                continue
            tail = tokens[index + 2 : min(len(tokens), index + 10)]
            if _contains_actor_led_finite_action(tail):
                return True
    return False


def gerund_actor_role_finite_action_splice(value: str) -> bool:
    """Return whether a gerundized action word leaked into an actor-role subject."""

    for tokens in _token_segments(value):
        for index in range(0, max(0, len(tokens) - 2)):
            window = tokens[index : min(len(tokens), index + 10)]
            for split_index in range(1, min(len(window), 6)):
                prefix = " ".join(window[:split_index]).strip(" .")
                normalized_prefix = base_gerund_clause(prefix).strip(" .")
                if not normalized_prefix or normalized_prefix.casefold() == prefix.casefold():
                    continue
                if not _has_actor_role_term(normalized_prefix):
                    continue
                candidate = " ".join(window[split_index:]).strip(" .")
                if _candidate_starts_with_stative_ownership(candidate):
                    continue
                full_text = " ".join([normalized_prefix, candidate]).strip(" .")
                if looks_like_actor_led_subject_prefix(normalized_prefix, full_text) and looks_like_finite_action(candidate):
                    return True
    return False


def _contains_actor_led_finite_action(tokens: list[str]) -> bool:
    tail_text = " ".join(tokens)
    for split_index in range(1, min(len(tokens), 6)):
        prefix = " ".join(tokens[:split_index]).strip(" .")
        candidate = " ".join(tokens[split_index:]).strip(" .")
        if looks_like_actor_led_subject_prefix(prefix, tail_text) and looks_like_finite_action(candidate):
            return True
    return False


def _word_tokens(value: str) -> list[str]:
    return [match.group(0) for match in re.finditer(r"[A-Za-z][A-Za-z0-9'-]*", str(value or ""))]


def _token_segments(value: str) -> list[list[str]]:
    return [tokens for part in re.split(r"[.!?;:]+", str(value or "")) if (tokens := _word_tokens(part))]


def _has_actor_role_term(value: str) -> bool:
    return bool({token.casefold() for token in _word_tokens(value)} & _ACTOR_ROLE_TERMS)


def _candidate_starts_with_stative_ownership(value: str) -> bool:
    first = (_word_tokens(value) or [""])[0].casefold()
    return first in {"are", "has", "have", "is", "need", "needs"}


__all__ = [
    "actor_led_finite_action_inside_user_can",
    "gerund_actor_role_finite_action_splice",
]
