"""Shared actor-role token detection for greenfield artifact phrasing."""

from __future__ import annotations

import re

ROLEISH_TERMS = {
    "actor",
    "admin",
    "administrator",
    "applicant",
    "client",
    "coordinator",
    "customer",
    "manager",
    "operator",
    "owner",
    "participant",
    "person",
    "requester",
    "resident",
    "reviewer",
    "submitter",
    "user",
}

ACTOR_LEAD_TERMS = ROLEISH_TERMS | {
    "agent",
    "analyst",
    "approver",
    "auditor",
    "author",
    "editor",
    "evaluator",
    "expert",
    "inspector",
    "lead",
    "member",
    "officer",
    "patient",
    "scheduler",
    "specialist",
    "staff",
    "student",
    "supervisor",
    "support",
    "team",
    "technician",
}


def looks_actor_term(value: str) -> bool:
    token = str(value or "").casefold()
    return bool(token in ACTOR_LEAD_TERMS or re.search(r"(?:er|or|ist|ian|ant|ee)$", token))


__all__ = [
    "ACTOR_LEAD_TERMS",
    "ROLEISH_TERMS",
    "looks_actor_term",
]
