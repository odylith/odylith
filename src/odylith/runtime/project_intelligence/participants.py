"""Participant narration helpers for greenfield Project dashboards."""

from __future__ import annotations

import re
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_confirmed_text import (
    capitalize_sentence_start_preserving_source_terms,
)
from odylith.runtime.project_intelligence.utils import display_text, sentence, short


_ACTIVITY_MARKERS = (
    " approving ",
    " completing ",
    " configuring ",
    " entering ",
    " filling ",
    " following up",
    " logging ",
    " managing ",
    " opening ",
    " reading ",
    " receiving ",
    " recording ",
    " reviewing ",
    " selecting ",
    " submitting ",
    " uploading ",
    " using ",
    " who ",
)

_WORKFLOW_BODY_RE = re.compile(
    r"\b(?:accepted[- ]path|accepted\s+first\s+path|first\s+path|first\s+release|"
    r"opens?\s+[^,.;]+,\s+selects?|handles\s+the\s+accepted|starts?\s+the\s+accepted|"
    r"supplies\s+required\s+input|receives\s+the\s+visible|complete\s+the\s+accepted)\b"
    r"|\bmoves\s+the\s+work\s+through\b",
    re.IGNORECASE,
)


def participant_title_and_body(value: Any, *, context: str = "") -> tuple[str, str]:
    """Return a stable participant title and responsibility-focused body."""

    text = display_text(value)
    if not text:
        return "", ""
    head, explicit_body = _split_role_body(text)
    title, activity_tail = _stable_title(head)
    body = explicit_body or _activity_body(activity_tail=activity_tail, title=title)
    body = _participant_body(title=title, body=body, context=context)
    return title, body


def participant_title(value: Any) -> str:
    """Return only the stable participant identity for a raw actor phrase."""

    title, _body = participant_title_and_body(value)
    return title


def participant_body(*, title: str, body: Any = "", context: str = "") -> str:
    """Return a readable role description without first-path or workflow fragments."""

    return _participant_body(title=title, body=display_text(body), context=context)


def participant_key(value: Any) -> str:
    """Return a stable dedupe key for participant titles."""

    title, _tail = _stable_title(display_text(value))
    key = title.casefold()
    key = re.sub(r"\([^)]*\)", "", key)
    key = re.sub(r"[^a-z0-9]+", " ", key)
    return " ".join(key.split())


def _split_role_body(value: str) -> tuple[str, str]:
    for separator in (" — ", " – ", " - ", ":"):
        head, sep, body = value.partition(separator)
        if sep and head.strip() and body.strip():
            return head.strip(" ."), body.strip(" .")
    return value.strip(" ."), ""


def _stable_title(value: str) -> tuple[str, str]:
    text = display_text(value).strip(" .")
    text = re.sub(r"^(?:the|a|an)\s+", "", text, flags=re.IGNORECASE)
    best_index = -1
    best_marker = ""
    lowered = f" {text.casefold()} "
    for marker in _ACTIVITY_MARKERS:
        index = lowered.find(marker)
        if index > 0 and (best_index < 0 or index < best_index):
            best_index = index
            best_marker = marker
    if best_index >= 0:
        head = text[:best_index].strip(" .,:;-")
        tail_start = best_index + len(best_marker.strip())
        tail = text[tail_start:].strip(" .,:;-")
        if best_marker.strip() == "who":
            tail = text[best_index:].strip(" .,:;-")
        title = _title_text(head)
        return title, tail
    return _title_text(text), ""


def _title_text(value: str) -> str:
    text = display_text(value).strip(" .,:;-")
    words = text.split()
    if len(words) > 8:
        text = " ".join(words[:8])
    return _sentence_case_role_title(capitalize_sentence_start_preserving_source_terms(text))


def _sentence_case_role_title(value: str) -> str:
    words = value.split()
    if len(words) < 2:
        return value
    first = words[0].strip(".,;:!?()[]{}")
    if first[:1].islower() and any(character.isupper() for character in first[1:]):
        return value
    return " ".join([words[0], *[_lower_role_title_word(word) for word in words[1:]]])


def _lower_role_title_word(value: str) -> str:
    token = value.strip(".,;:!?()[]{}")
    preserve_source_case = bool(
        token
        and (
            (len(token) > 1 and token.isupper())
            or any(character.isdigit() for character in token)
            or any(character.isupper() for character in token[1:])
        )
    )
    return value if preserve_source_case else value.lower()


def _activity_body(*, activity_tail: str, title: str) -> str:
    tail = display_text(activity_tail).strip(" .")
    if not tail:
        return ""
    lower = tail.casefold()
    if "review" in lower or "follow" in lower:
        return "Reviews product results, prioritizes follow-up, and decides which cases need human attention."
    if "configur" in lower or "threshold" in lower or "rule" in lower or "policy" in lower:
        return "Maintains the operating criteria that shape product outcomes and keeps those criteria aligned with current policy."
    if "read" in lower or "receiv" in lower:
        return "Provides the information the product needs, checks the result, and decides whether the outcome is useful."
    if "complet" in lower or "fill" in lower or "submit" in lower or "enter" in lower or "upload" in lower:
        return "Provides the required information and expects a clear result that supports the next decision."
    if "approv" in lower:
        return "Decides whether the product outcome is acceptable and identifies what must change before it can move forward."
    return f"Uses the product to reach a clear outcome and keep {title.lower()} responsibilities visible."


def _participant_body(*, title: str, body: str, context: str) -> str:
    clean_title = _title_text(title) or "Participant"
    candidate = display_text(body).strip(" .")
    if (
        not candidate
        or _WORKFLOW_BODY_RE.search(candidate)
        or _title_leaks_other_roles(clean_title, candidate)
        or _looks_product_story_body(title=clean_title, body=candidate)
    ):
        candidate = _context_body(title=clean_title, context="")
    candidate = _remove_other_role_spillover(title=clean_title, body=candidate)
    candidate = (
        capitalize_sentence_start_preserving_source_terms(candidate)
        if candidate
        else _context_body(title=clean_title, context=context)
    )
    return short(candidate, limit=210)


def _context_body(*, title: str, context: str) -> str:
    lowered = title.casefold()
    context_text = display_text(context).strip(" .")
    if any(
        token in lowered
        for token in (
            "admin",
            "administrator",
            "configur",
            "deadline",
            "permission",
            "policy",
            "template",
        )
    ):
        return "Maintains the rules, settings, and operating limits that keep product outcomes aligned with policy."
    if any(token in lowered for token in ("chair", "editor", "manager", "review", "supervisor", "approver")):
        return "Reviews product outcomes, decides what needs attention, and helps the next responsible person act with confidence."
    if any(
        token in lowered
        for token in ("applicant", "author", "customer", "client", "requester", "submitter", "user", "person")
    ):
        return "Uses the product to provide information, understand the result, and decide what to do next."
    if any(token in lowered for token in ("operator", "coordinator", "steward", "maintainer")):
        return "Coordinates exceptions, resolves gaps, and makes sure the right people have the context they need."
    if any(token in lowered for token in ("auditor", "compliance", "risk", "privacy", "safety")):
        return "Checks whether the product outcome is acceptable, explainable, and safe enough for the intended use."
    if context_text and not _WORKFLOW_BODY_RE.search(context_text):
        return context_text
    return "Has a distinct stake in the product outcome and needs enough context to act responsibly."


def _title_leaks_other_roles(title: str, body: str) -> bool:
    title_key = participant_key(title)
    role_like = re.findall(
        r"\b[A-Z][A-Za-z]*(?:\s+(?:[A-Z][A-Za-z]*|\([^)]+\))){0,4}\b",
        body,
    )
    for role in role_like:
        key = participant_key(role)
        if key and key != title_key and len(key.split()) >= 2:
            return True
    return False


def _looks_product_story_body(*, title: str, body: str) -> bool:
    """Return true when a role card received whole-product narration instead of role narration."""

    lowered = display_text(body).casefold()
    if not lowered:
        return False
    if re.match(r"^(?:a|an|the)\s+.+\b(?:needs?|helps?|enables?|lets?)\b", lowered):
        return True
    if re.search(r"\b(?:product|workspace|platform|application|app)\s+(?:helps?|lets?|enables?|needs?)\b", lowered):
        return True
    title_terms = set(re.findall(r"[a-z][a-z-]{2,}", participant_key(title)))
    role_terms = {
        "admin",
        "administrator",
        "applicant",
        "author",
        "chair",
        "client",
        "coordinator",
        "customer",
        "editor",
        "officer",
        "operator",
        "reviewer",
        "supervisor",
        "team",
        "user",
    }
    mentioned = {term for term in role_terms if re.search(rf"\b{re.escape(term)}s?\b", lowered)}
    foreign = mentioned - title_terms
    return len(foreign) >= 2


def _remove_other_role_spillover(*, title: str, body: str) -> str:
    text = display_text(body).strip(" .")
    title_key = participant_key(title)
    pieces = [piece.strip(" .") for piece in re.split(r";\s+|(?<=[.!?])\s+", text) if piece.strip(" .")]
    kept = []
    for piece in pieces:
        role_head = piece.split(",", 1)[0].strip()
        role_key = participant_key(role_head)
        if role_key and role_key != title_key and len(role_key.split()) >= 2:
            continue
        kept.append(piece)
    return ". ".join(kept) if kept else text


__all__ = [
    "participant_body",
    "participant_key",
    "participant_title",
    "participant_title_and_body",
]
