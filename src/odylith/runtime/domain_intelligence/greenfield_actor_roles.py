"""Shared actor-role terms for first-path grammar decisions."""

from __future__ import annotations

from odylith.runtime.common.prose_grammar import looks_like_base_action_token
from odylith.runtime.common.prose_grammar import looks_like_finite_action_token
from odylith.runtime.domain_intelligence.greenfield_actor_terms import has_human_actor_signal
from odylith.runtime.domain_intelligence.greenfield_first_path_common import clean_first_path_text

ACTOR_ROLE_NOUNS = frozenset(
    {
        "actor",
        "actors",
        "analyst",
        "analysts",
        "architect",
        "architects",
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
# ``ent`` is deliberately absent: domain nouns such as "entanglement" are not
# product participants. Keep this export for callers that need the stable set,
# but route the behavioral decision through the shared actor-term primitive.
ACTOR_ROLE_SUFFIXES = ("ant", "er", "ian", "ist", "or", "ee", "owner")


def looks_like_actor_role_term(value: str | object) -> bool:
    term = str(value or "").casefold().strip(".,:;")
    if not term:
        return False
    if term in ACTOR_ROLE_NOUNS:
        return True
    singular = term[:-1] if term.endswith("s") else term
    if looks_like_finite_action_token(term) or looks_like_base_action_token(singular):
        return False
    return has_human_actor_signal(term)


def has_actor_role_word(value: str | object) -> bool:
    words = [
        word.casefold().strip(".,:;")
        for word in clean_first_path_text(value).replace("-", " ").split()
        if word.strip(".,:;")
    ]
    return any(looks_like_actor_role_term(word) for word in words)


__all__ = ["ACTOR_ROLE_NOUNS", "ACTOR_ROLE_SUFFIXES", "has_actor_role_word", "looks_like_actor_role_term"]
