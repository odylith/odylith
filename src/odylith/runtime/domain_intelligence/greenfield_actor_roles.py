"""Shared actor-role terms for first-path grammar decisions."""

from __future__ import annotations

from odylith.runtime.domain_intelligence.greenfield_first_path_common import clean_first_path_text

ACTOR_ROLE_NOUNS = frozenset(
    {
        "actor",
        "actors",
        "applicant",
        "applicants",
        "coordinator",
        "coordinators",
        "customer",
        "customers",
        "inspector",
        "inspectors",
        "lead",
        "leads",
        "liaison",
        "liaisons",
        "maker",
        "makers",
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
        "preparer",
        "preparers",
        "recipient",
        "recipients",
        "requester",
        "requesters",
        "reviewer",
        "reviewers",
        "staff",
        "supervisor",
        "supervisors",
        "team",
        "teams",
        "traveler",
        "travelers",
        "user",
        "users",
    }
)


def has_actor_role_word(value: str | object) -> bool:
    words = [
        word.casefold().strip(".,:;")
        for word in clean_first_path_text(value).replace("-", " ").split()
        if word.strip(".,:;")
    ]
    return bool(set(words) & ACTOR_ROLE_NOUNS)


__all__ = ["ACTOR_ROLE_NOUNS", "has_actor_role_word"]
