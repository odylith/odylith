"""Shared actor-role token detection for greenfield artifact phrasing."""

from __future__ import annotations

import re

from odylith.runtime.common.prose_grammar import looks_like_base_action_token
from odylith.runtime.common.prose_grammar import looks_like_finite_action_token

ROLEISH_TERMS = {
    "actor",
    "admin",
    "administrator",
    "applicant",
    "client",
    "clerk",
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
        "advisor",
        "analyst",
        "auditor",
        "applicant",
        "beneficiary",
        "chief",
        "client",
        "clerk",
        "contact",
        "coordinator",
        "counselor",
        "crew",
        "curator",
        "customer",
        "director",
        "engineer",
        "evaluator",
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
        "provider",
        "publisher",
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
    {
        ("end", "user"),
        ("individual",),
        ("new", "user"),
        ("person",),
        ("requester",),
        ("somebody",),
        ("someone",),
        ("user",),
    }
)
_NON_HUMAN_ACTOR_CONTEXT_TERMS = frozenset(
    {
        "api",
        "app",
        "application",
        "broker",
        "calculator",
        "controller",
        "dashboard",
        "database",
        "engine",
        "model",
        "pipeline",
        "platform",
        "portal",
        "product",
        "record",
        "report",
        "router",
        "service",
        "system",
        "tool",
        "tracker",
        "workspace",
    }
)
_ACTOR_ARTICLES = frozenset({"a", "an", "the", "one"})
_ACTOR_CONTEXT_BOUNDARY_TERMS = frozenset(
    {"after", "before", "during", "for", "from", "then", "that", "to", "when", "where", "while", "with", "without"}
)


def looks_actor_term(value: str) -> bool:
    token = str(value or "").casefold()
    return bool(token in ACTOR_LEAD_TERMS or re.search(r"(?:er|or|ist|ian|ant|ee)$", token))


def word_has_actor_role_signal(value: str) -> bool:
    token = str(value or "").casefold().strip(".,;:()[]{}")
    return bool(token in CONFIRMED_ACTOR_ROLE_TERMS or (token.endswith("s") and token[:-1] in CONFIRMED_ACTOR_ROLE_TERMS))


def has_human_actor_signal(value: str) -> bool:
    """Return whether a label names a person-like product participant.

    A shared classifier cannot carry the benchmark's product-domain vocabulary.
    It accepts either a stable, domain-neutral role word or a full explicit
    actor-action clause. The latter lets evidence such as ``A participant enters
    details`` retain its human subject without treating a bare technical noun as
    a person.
    """

    tokens = tuple(re.findall(r"[a-z]+", str(value or "").casefold()))
    if not tokens or is_automated_actor(value):
        return False
    return has_human_actor_role_signal(value) or _has_explicit_actor_action_context(tokens)


def has_human_actor_role_signal(value: str) -> bool:
    """Return whether a label contains a known, domain-neutral human role."""

    tokens = tuple(re.findall(r"[a-z]+", str(value or "").casefold()))
    if not tokens or is_automated_actor(value) or set(tokens) & _ACTOR_CONTEXT_BOUNDARY_TERMS:
        return False
    terminal = tokens[-1][:-1] if tokens[-1].endswith("s") else tokens[-1]
    if terminal in CONFIRMED_ACTOR_ROLE_TERMS or terminal in _HUMAN_PROFESSIONAL_ROLE_TERMS:
        return True
    if set(tokens) & _NON_HUMAN_ACTOR_CONTEXT_TERMS:
        return False
    for token in tokens:
        singular = token[:-1] if token.endswith("s") else token
        if singular in CONFIRMED_ACTOR_ROLE_TERMS or singular in _HUMAN_PROFESSIONAL_ROLE_TERMS:
            return True
    for index, token in enumerate(tokens[1:], start=1):
        if token == "assistant" and tokens[index - 1] not in _AUTOMATED_ASSISTANT_MODIFIERS:
            return True
    return False


def has_human_actor_action_context(actor: str, action: str) -> bool:
    """Validate one proposed actor/action split without inferring from its tail."""

    actor_tokens = tuple(re.findall(r"[a-z]+", str(actor or "").casefold()))
    action_tokens = tuple(re.findall(r"[a-z]+", str(action or "").casefold()))
    if (
        not actor_tokens
        or not action_tokens
        or is_automated_actor(actor)
        or set(actor_tokens) & _ACTOR_CONTEXT_BOUNDARY_TERMS
    ):
        return False
    actor_start = 1 if actor_tokens[0] in _ACTOR_ARTICLES else 0
    if any(
        looks_like_finite_action_token(token) or looks_like_base_action_token(token)
        for token in actor_tokens[actor_start:]
    ):
        return False
    if has_human_actor_role_signal(actor):
        return bool(looks_like_finite_action_token(action_tokens[0]) or looks_like_base_action_token(action_tokens[0]))
    return _subject_has_human_action(
        actor_tokens[actor_start:],
        action_tokens,
        article_led=actor_start == 1,
        modal_tokens={"can", "could", "may", "might", "must", "should", "will", "would"},
    )


def _has_explicit_actor_action_context(tokens: tuple[str, ...]) -> bool:
    """Accept unfamiliar actors only when grammar supplies the missing meaning."""

    if len(tokens) < 2:
        return False
    for start in _actor_context_starts(tokens):
        if _actor_context_has_human_action(tokens[start:]):
            return True
    return False


def _actor_context_starts(tokens: tuple[str, ...]) -> tuple[int, ...]:
    starts = [0]
    for index, token in enumerate(tokens[:-1]):
        if token == "where":
            starts.append(index + 1)
        elif token == "for" and "who" in tokens[index + 1 :]:
            starts.append(index + 1)
    return tuple(dict.fromkeys(starts))


def _actor_context_has_human_action(tokens: tuple[str, ...]) -> bool:
    if not tokens:
        return False
    actor_start = 1 if tokens[0] in _ACTOR_ARTICLES else 0
    if actor_start >= len(tokens):
        return False
    modal_tokens = {"can", "could", "may", "might", "must", "should", "will", "would"}
    relative_index = next((index for index, token in enumerate(tokens) if token == "who"), -1)
    if relative_index > actor_start:
        subject_tokens = tokens[actor_start:relative_index]
        action_tokens = tokens[relative_index + 1 :]
        return _subject_has_human_action(
            subject_tokens,
            action_tokens,
            article_led=actor_start == 1,
            modal_tokens=modal_tokens,
        )
    for index, action in enumerate(tokens[actor_start + 1 :], start=actor_start + 1):
        subject_tokens = tokens[actor_start:index]
        if not subject_tokens or set(subject_tokens) & _NON_HUMAN_ACTOR_CONTEXT_TERMS:
            return False
        if looks_like_finite_action_token(action):
            return True
        if (
            tokens[index - 1] in modal_tokens
            or (subject_tokens[-1].endswith("s") and not subject_tokens[-1].endswith(("ics", "ss", "us")))
        ) and looks_like_base_action_token(action):
            return True
    return False


def _subject_has_human_action(
    subject_tokens: tuple[str, ...],
    action_tokens: tuple[str, ...],
    *,
    article_led: bool,
    modal_tokens: set[str],
) -> bool:
    if not subject_tokens or not action_tokens or set(subject_tokens) & _NON_HUMAN_ACTOR_CONTEXT_TERMS:
        return False
    action = action_tokens[0]
    if looks_like_finite_action_token(action):
        return bool(
            article_led
            or (subject_tokens[-1].endswith("s") and not subject_tokens[-1].endswith(("ics", "ss", "us")))
        )
    if action in modal_tokens and len(action_tokens) > 1 and looks_like_base_action_token(action_tokens[1]):
        return bool(
            article_led
            or (subject_tokens[-1].endswith("s") and not subject_tokens[-1].endswith(("ics", "ss", "us")))
        )
    return bool(
        (article_led or (subject_tokens[-1].endswith("s") and not subject_tokens[-1].endswith(("ics", "ss", "us"))))
        and looks_like_base_action_token(action)
    )


def is_automated_actor(value: str) -> bool:
    """Return whether an actor label denotes automation rather than a person."""

    tokens = tuple(re.findall(r"[a-z]+", str(value or "").casefold()))
    while tokens and tokens[0] in _ACTOR_ARTICLES:
        tokens = tokens[1:]
    if set(tokens) & _HUMAN_PROFESSIONAL_ROLE_TERMS:
        return False
    if set(tokens) & _AUTOMATED_ACTOR_TERMS:
        return True
    for index, role in enumerate(tokens):
        if role not in {"agent", "assistant"}:
            continue
        if index and tokens[index - 1] in _AUTOMATED_ASSISTANT_MODIFIERS:
            # A named profession between an automation modifier and "assistant"
            # is an explicit human role, e.g. "AI research assistant".
            if index == 1:
                return True
        if tuple(tokens[max(0, index - 2) : index]) in {
            ("ai", "powered"),
            ("artificial", "intelligence"),
        }:
            return True
    return bool(set(tokens) & _AUTOMATED_REVIEWER_MARKERS and "reviewer" in tokens)


def has_non_human_actor_signal(value: str) -> bool:
    """Return whether a subject names a product or automated system actor."""

    tokens = set(re.findall(r"[a-z]+", str(value or "").casefold()))
    return bool(tokens & _NON_HUMAN_ACTOR_CONTEXT_TERMS) or is_automated_actor(value)


def is_actor_obligation_noun_phrase(value: str) -> bool:
    """Return whether a review obligation is being mistaken for an actor action."""

    words = re.findall(r"[a-z]+", str(value or "").casefold())
    if len(words) < 3 or words[0] not in {"explicit", "independent", "manual", "required"}:
        return False
    return words[-1] in {"approval", "decision", "judgment", "review", "signoff", "validation"}


def starts_with_automated_actor(value: str) -> bool:
    """Return whether the opening actor phrase is automated, not a later tool mention."""

    tokens = tuple(re.findall(r"[a-z]+", str(value or "").casefold()))
    while tokens and tokens[0] in _ACTOR_ARTICLES:
        tokens = tokens[1:]
    actor_tokens: list[str] = []
    for token in tokens:
        if actor_tokens and (looks_like_finite_action_token(token) or looks_like_base_action_token(token)):
            break
        actor_tokens.append(token)
        if is_automated_actor(" ".join(actor_tokens)):
            return True
    return False


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
    "has_human_actor_action_context",
    "has_human_actor_role_signal",
    "has_human_actor_signal",
    "has_non_human_actor_signal",
    "is_actor_obligation_noun_phrase",
    "is_automated_actor",
    "starts_with_automated_actor",
    "localize_generic_actor_label",
    "looks_actor_term",
    "omit_actor_from_material_action",
    "starts_with_generic_actor_label",
    "word_has_actor_role_signal",
]
