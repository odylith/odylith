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
    "scheduler",
    "specialist",
    "staff",
    "supervisor",
    "support",
    "team",
}

CONFIRMED_ACTOR_ROLE_TERMS = frozenset(
    {
        "admin",
        "analyst",
        "auditor",
        "applicant",
        "beneficiary",
        "chief",
        "client",
        "contact",
        "coordinator",
        "crew",
        "customer",
        "director",
        "engineer",
        "expert",
        "guardian",
        "inspector",
        "lead",
        "manager",
        "member",
        "operator",
        "owner",
        "planner",
        "reviewer",
        "requester",
        "staff",
        "submitter",
        "supervisor",
        "support",
        "sufferer",
        "team",
        "trainee",
        "user",
        "volunteer",
    }
)

GENERIC_ACTOR_LABELS = (
    "implementation owner",
    "project release owner",
    "end-user advocate",
    "project operator",
    "workflow operator",
    "domain reviewer",
    "evidence owner",
    "proof reviewer",
    "release owner",
    "risk reviewer",
    "primary user",
    "build owner",
    "maintainer",
    "operator",
    "reviewer",
)

_GENERIC_ACTOR_LABEL_DELIMITER_RE = re.compile(r"^(?:\s|:|[-\u2013\u2014])")


def looks_actor_term(value: str) -> bool:
    token = str(value or "").casefold()
    return bool(token in ACTOR_LEAD_TERMS or re.search(r"(?:er|or|ist|ian|ant|ee)$", token))


def word_has_actor_role_signal(value: str) -> bool:
    token = str(value or "").casefold().strip(".,;:()[]{}")
    return bool(token in CONFIRMED_ACTOR_ROLE_TERMS or (token.endswith("s") and token[:-1] in CONFIRMED_ACTOR_ROLE_TERMS))


def generic_actor_label_prefix(value: str) -> str:
    text = " ".join(str(value or "").split()).strip(" .")
    lowered = text.casefold()
    for label in GENERIC_ACTOR_LABELS:
        if lowered == label:
            return label
        if lowered.startswith(label) and _GENERIC_ACTOR_LABEL_DELIMITER_RE.match(lowered[len(label) :]):
            return label
    return ""


def starts_with_generic_actor_label(value: str) -> bool:
    return bool(generic_actor_label_prefix(value))


def localize_generic_actor_label(value: str) -> str:
    text = " ".join(str(value or "").split()).strip()
    if not text or not starts_with_generic_actor_label(text):
        return text
    return f"local {text[:1].lower()}{text[1:]}"


__all__ = [
    "ACTOR_LEAD_TERMS",
    "CONFIRMED_ACTOR_ROLE_TERMS",
    "GENERIC_ACTOR_LABELS",
    "ROLEISH_TERMS",
    "generic_actor_label_prefix",
    "localize_generic_actor_label",
    "looks_actor_term",
    "starts_with_generic_actor_label",
    "word_has_actor_role_signal",
]
