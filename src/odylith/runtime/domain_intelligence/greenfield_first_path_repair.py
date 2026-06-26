"""Repair non-action first-path facts before semantic projection."""

from __future__ import annotations

import re
from collections.abc import Sequence
from typing import Any

from odylith.runtime.common.prose_grammar import contains_finite_action
from odylith.runtime.common.prose_grammar import looks_like_base_action_token
from odylith.runtime.common.prose_grammar import looks_like_action_clause
from odylith.runtime.domain_intelligence.greenfield_domain_term_index import label_terms
from odylith.runtime.domain_intelligence.greenfield_text import clean_text
from odylith.runtime.domain_intelligence.greenfield_text import text_values

_PRODUCT_CONTAINER_TERMS = frozenset(
    {
        "app",
        "application",
        "board",
        "console",
        "dashboard",
        "desk",
        "engine",
        "hub",
        "journal",
        "lab",
        "ledger",
        "logbook",
        "notebook",
        "platform",
        "planner",
        "portal",
        "product",
        "queue",
        "service",
        "studio",
        "system",
        "tool",
        "tracker",
        "workbench",
        "workspace",
    }
)
_ACTOR_TERMS = frozenset(
    {
        "admin",
        "analyst",
        "approver",
        "coordinator",
        "customer",
        "designer",
        "employee",
        "guest",
        "manager",
        "member",
        "operator",
        "owner",
        "participant",
        "person",
        "planner",
        "reviewer",
        "staff",
        "supervisor",
        "team",
        "teams",
        "user",
        "worker",
    }
)
_ACTOR_SUFFIXES = ("ant", "ent", "er", "ian", "ist", "or", "ee", "owner")
_CONSTRAINT_LEADING_ACTIONS = frozenset(
    {
        "avoid",
        "avoids",
        "exclude",
        "excludes",
        "limit",
        "limits",
        "prevent",
        "prevents",
    }
)


def first_path_has_action_signal(value: Any) -> bool:
    text = clean_text(value).strip(" .")
    if _starts_with_constraint_action(text):
        return False
    return bool(
        text
        and (
            contains_finite_action(text)
            or looks_like_action_clause(text)
            or _contains_base_action_after_subject(text)
        )
    )


def semantic_first_path_from_context(
    *,
    title: str,
    source: str = "",
    actor_rows: Sequence[Any] = (),
) -> str:
    """Build a bounded first path when the accepted source is a noun phrase."""

    focus = _focus_from_source(source) or _focus_from_title(title)
    actor = _actor_from_source(source) or _actor_from_rows(actor_rows) or "A representative user"
    plural = _plural_subject(actor)
    verb = "review" if plural else "reviews"
    record = "record" if plural else "records"
    see = "see" if plural else "sees"
    article = _indefinite_article(focus)
    return (
        f"{_sentence_start(actor)} {verb} {focus} details, {record} the current status, "
        f"and {see} {article} {focus} result with blockers and evidence for review."
    )


def repair_proposal_first_path(proposal: dict[str, Any]) -> bool:
    intent = proposal.get("intent") if isinstance(proposal.get("intent"), dict) else proposal
    if not isinstance(intent, dict):
        return False
    current = clean_text(intent.get("first_path"))
    if first_path_has_action_signal(current):
        return False
    title = clean_text(intent.get("title") or proposal.get("title")) or "accepted product"
    repaired = semantic_first_path_from_context(
        title=title,
        source=current or clean_text(intent.get("prompt")),
        actor_rows=text_values(intent.get("human_actors")),
    )
    if clean_text(repaired) == current:
        return False
    intent["first_path"] = repaired
    proposal.pop("semantic_model", None)
    return True


def _focus_from_title(value: str) -> str:
    text = re.split(r"\s+for\s+", clean_text(value), maxsplit=1, flags=re.IGNORECASE)[0]
    return _focus_from_text(text or value)


def _focus_from_source(value: str) -> str:
    if _starts_with_constraint_action(value):
        return ""
    text = re.split(r"\s+for\s+", clean_text(value), maxsplit=1, flags=re.IGNORECASE)[0]
    return _focus_from_text(text)


def _focus_from_text(value: str) -> str:
    terms = [
        term.casefold()
        for term in label_terms(value)
        if term.casefold() not in _PRODUCT_CONTAINER_TERMS and term.casefold() not in {"a", "an", "the"}
    ]
    focus = " ".join(terms).strip(" .")
    return focus or clean_text(value).strip(" .").casefold() or "accepted product"


def _actor_from_rows(values: Sequence[Any]) -> str:
    for value in values:
        label = clean_text(value).split(":", 1)[0].split("—", 1)[0].strip(" .")
        if label and len(label.split()) <= 7:
            return label
    return ""


def _actor_from_source(value: str) -> str:
    text = clean_text(value).strip(" .")
    match = re.search(r"\bfor\s+(?P<actor>[^.;:,]{2,120})$", text, flags=re.IGNORECASE)
    if not match:
        return ""
    actor = clean_text(match.group("actor")).strip(" .")
    words = actor.split()
    if not (2 <= len(words) <= 8):
        return ""
    if not _looks_like_actor_phrase(words):
        return ""
    return actor


def _contains_base_action_after_subject(value: str) -> bool:
    words = re.findall(r"[A-Za-z0-9][A-Za-z0-9'-]*", clean_text(value))
    for index in range(1, max(1, len(words) - 1)):
        token = words[index].casefold().strip(".,:;")
        if not looks_like_base_action_token(token):
            continue
        next_token = words[index + 1].casefold().strip(".,:;")
        if next_token in _PRODUCT_CONTAINER_TERMS:
            continue
        return True
    return False


def _starts_with_constraint_action(value: str) -> bool:
    first = clean_text(value).split(maxsplit=1)[0].casefold().strip(".,:;") if clean_text(value) else ""
    return first in _CONSTRAINT_LEADING_ACTIONS


def _looks_like_actor_phrase(words: Sequence[str]) -> bool:
    last = words[-1].casefold().strip(".,:;")
    singular = last[:-1] if last.endswith("s") else last
    return bool(
        last in _ACTOR_TERMS
        or singular in _ACTOR_TERMS
        or any(last.endswith(suffix) or singular.endswith(suffix) for suffix in _ACTOR_SUFFIXES)
    )


def _plural_subject(value: str) -> bool:
    text = clean_text(value).strip(" .")
    if not text:
        return False
    last = text.split()[-1].casefold().strip(".,:;")
    return last.endswith("s") and last not in {"status"}


def _sentence_start(value: str) -> str:
    text = clean_text(value).strip(" .")
    return f"{text[:1].upper()}{text[1:]}" if text else ""


def _indefinite_article(value: str) -> str:
    first = clean_text(value).strip(" .").split(maxsplit=1)[0].casefold() if clean_text(value) else ""
    return "an" if first[:1] in {"a", "e", "i", "o", "u"} else "a"


__all__ = [
    "first_path_has_action_signal",
    "repair_proposal_first_path",
    "semantic_first_path_from_context",
]
