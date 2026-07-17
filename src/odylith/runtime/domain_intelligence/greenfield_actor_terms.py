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
    "curator",
    "editor",
    "evaluator",
    "expert",
    "inspector",
    "lead",
    "liaison",
    "member",
    "officer",
    "registrar",
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
        "curator",
        "customer",
        "director",
        "engineer",
        "expert",
        "guardian",
        "inspector",
        "lead",
        "liaison",
        "manager",
        "member",
        "operator",
        "officer",
        "owner",
        "planner",
        "registrar",
        "reviewer",
        "requester",
        "staff",
        "submitter",
        "supervisor",
        "support",
        "steward",
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
_AUTOMATED_ACTOR_TERMS = frozenset({"automated", "autonomous", "bot"})
_AUTOMATED_ASSISTANT_MODIFIERS = frozenset(
    {"ai", "automated", "autonomous", "digital", "llm", "virtual", "workflow"}
)
_HUMAN_PROFESSIONAL_ROLE_TERMS = frozenset(
    {"analyst", "architect", "designer", "developer", "director", "engineer", "manager", "operator", "researcher", "scientist"}
)
_AUTOMATED_REVIEWER_MARKERS = frozenset({"ai", "llm"})
_ABSTRACT_MATERIAL_ACTION_ACTORS = frozenset(
    {("end", "user"), ("individual",), ("person",), ("somebody",), ("someone",), ("user",)}
)


def looks_actor_term(value: str) -> bool:
    token = str(value or "").casefold()
    return bool(token in ACTOR_LEAD_TERMS or re.search(r"(?:er|or|ist|ian|ant|ee)$", token))


def word_has_actor_role_signal(value: str) -> bool:
    token = str(value or "").casefold().strip(".,;:()[]{}")
    return bool(token in CONFIRMED_ACTOR_ROLE_TERMS or (token.endswith("s") and token[:-1] in CONFIRMED_ACTOR_ROLE_TERMS))


def is_automated_actor(value: str) -> bool:
    """Return whether an actor label denotes automation rather than a person."""

    tokens = tuple(re.findall(r"[a-z]+", str(value or "").casefold()))
    if set(tokens) & _HUMAN_PROFESSIONAL_ROLE_TERMS:
        return False
    if set(tokens) & _AUTOMATED_ACTOR_TERMS:
        return True
    for index, role in enumerate(tokens):
        if role not in {"agent", "assistant"}:
            continue
        if index and tokens[index - 1] in _AUTOMATED_ASSISTANT_MODIFIERS:
            return True
        if tuple(tokens[max(0, index - 2) : index]) in {
            ("ai", "powered"),
            ("artificial", "intelligence"),
        }:
            return True
    return bool(set(tokens) & _AUTOMATED_REVIEWER_MARKERS and "reviewer" in tokens)


def omit_actor_from_material_action(value: str) -> bool:
    """Return whether an actor adds no product-specific meaning to a user action."""

    if is_automated_actor(value):
        return True
    tokens = tuple(re.findall(r"[a-z]+", str(value or "").casefold()))
    while tokens and tokens[0] in {"a", "an", "the"}:
        tokens = tokens[1:]
    return tokens in _ABSTRACT_MATERIAL_ACTION_ACTORS


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
    "is_automated_actor",
    "localize_generic_actor_label",
    "looks_actor_term",
    "omit_actor_from_material_action",
    "starts_with_generic_actor_label",
    "word_has_actor_role_signal",
]
