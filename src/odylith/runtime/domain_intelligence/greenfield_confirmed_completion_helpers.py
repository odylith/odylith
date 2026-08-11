"""Small scalar and sentence helpers for confirmed greenfield completion."""

from __future__ import annotations

from typing import Any

from odylith.runtime.domain_intelligence.greenfield_confirmed_backlog_text_model import inline_actor_subject
from odylith.runtime.domain_intelligence.greenfield_confirmed_completion_quality import text_needs_repair
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import clean_generated_text
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import set_sentence_text


def ensure_text(row: dict[str, Any], key: str, default: str, *, repair_bad_text: bool = False) -> bool:
    """Set a sentence field when it is missing or explicitly repairable."""

    if clean_generated_text(row.get(key)) and not (repair_bad_text and text_needs_repair(row.get(key))):
        return False
    row[key] = default
    return True


def security_posture_text(label: str) -> str:
    """Return a product-local security posture sentence for a generated workstream."""

    owner = clean_generated_text(label) or "This workstream"
    role = _security_posture_role(owner)
    if role == "proof":
        return (
            f"Security proof for {owner}: evidence access must stay auditable. "
            f"Before release, {owner} must show who accessed its proof, what evidence made replay safe, and which safety check passed."
        )
    if role == "review":
        return (
            f"Review security for {owner}: only authorized actors should change the visible outcome. "
            f"{owner} must keep correction history and access decisions tied to each visible outcome without exposing private context."
        )
    if role == "release":
        return (
            f"Release security for {owner}: promotion waits for access and privacy proof. "
            f"{owner} promotion evidence must show accessibility, retention, audit history, and privacy checks together before release."
        )
    return (
        f"Input security for {owner}: accepted facts and recovery history must be protected. "
        f"{owner} must keep accepted facts, access control, recovery history, and audit evidence traceable without exposing private context."
    )


def path_phrase(value: str) -> str:
    """Return a readable validation-path phrase."""

    text = clean_generated_text(value).strip(" .")
    if not text:
        return "path"
    return text if text.split()[-1].casefold().strip(".,;:") == "path" else f"{text} path"


def append_suffix_once(value: str, suffix: str) -> str:
    """Append a suffix word unless the phrase already ends with that word."""

    text = clean_generated_text(value).strip(" .")
    suffix_text = clean_generated_text(suffix).strip(" .")
    if not text:
        return suffix_text
    if not suffix_text:
        return text
    tail = text.split()[-1].casefold().strip(".,;:")
    suffix_key = suffix_text.split()[0].casefold().strip(".,;:")
    return text if tail == suffix_key else f"{text} {suffix_text}"


def actor_phrase_for_sentence(value: str) -> str:
    """Join actor labels into a sentence-ready phrase."""

    parts = [
        inline_actor_subject(clean_generated_text(part).strip(" ."), fallback="")
        for part in clean_generated_text(value).split(";")
        if clean_generated_text(part).strip(" .")
    ]
    if not parts:
        return "representative users"
    if len(parts) == 1:
        return parts[0]
    if len(parts) == 2:
        return f"{parts[0]} and {parts[1]}"
    return f"{', '.join(parts[:-1])}, and {parts[-1]}"


def repair_bad_scalar(row: dict[str, Any], key: str, *, fallback: str = "") -> bool:
    """Repair one sentence field only when the quality owner marks it bad."""

    if not text_needs_repair(row.get(key)):
        return False
    value = fallback or clean_generated_text(row.get(key))
    return set_sentence_text(row, key, value)


def _security_posture_role(label: str) -> str:
    text = clean_generated_text(label).casefold()
    if any(term in text for term in ("review", "clear", "result", "outcome")):
        return "review"
    if any(term in text for term in ("intake", "register", "submit", "enter", "capture", "record")):
        return "input"
    if any(term in text for term in ("release", "complete", "path")):
        return "release"
    if any(term in text for term in ("proof", "trust", "evidence", "ledger")):
        return "proof"
    return "input"


__all__ = [
    "actor_phrase_for_sentence",
    "append_suffix_once",
    "ensure_text",
    "path_phrase",
    "repair_bad_scalar",
    "security_posture_text",
]
