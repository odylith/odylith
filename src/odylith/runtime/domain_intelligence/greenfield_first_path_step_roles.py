"""Shared role predicates for confirmed greenfield first-path steps."""

from __future__ import annotations

from collections.abc import Sequence
import re

from odylith.runtime.domain_intelligence.greenfield_actor_roles import has_actor_role_word


def drop_release_proof_control_steps(values: Sequence[str]) -> list[str]:
    """Remove release/proof-control narration while preserving real path behavior."""

    rows = [_compact_text(value).strip(" .") for value in values if _compact_text(value).strip(" .")]
    if len(rows) <= 1:
        return rows
    cleaned = [row for row in rows if not is_release_proof_control_step(row)]
    return cleaned or rows


def is_release_proof_control_step(value: str) -> bool:
    """Return whether a row is release proof narration instead of path behavior."""

    words = _semantic_words(value)
    if not words:
        return False
    if _is_release_readiness_product_phrase(words):
        return False
    word_set = set(words)
    if "release" not in word_set and "proof" not in word_set:
        return False
    if not (word_set & {"complete", "prove", "proof", "readiness", "succeed", "validate"}):
        return False
    if words[:2] == ["first", "release"]:
        return True
    if words[0] in {"release", "proof", "readiness", "validation"}:
        return True
    return words[:3] == ["the", "first", "release"]


def is_supporting_setup_step(value: str) -> bool:
    """Return whether a first-path step describes structure, not user-owned action."""

    text = _compact_text(value).strip(" .")
    if not text:
        return False
    match = re.match(
        r"^(?:(?:a|an|the|one|this|that|each|another)\s+)?"
        r"(?P<subject>[A-Za-z][A-Za-z0-9'/-]*(?:\s+[A-Za-z][A-Za-z0-9'/-]*){0,6})\s+"
        r"(?P<verb>uses?|contains?|includes?|has|have|consists?|comprises?)\b"
        r"(?P<object>.+)$",
        text,
        flags=re.IGNORECASE,
    )
    if not match:
        return False
    subject = match.group("subject").strip(" .")
    if has_actor_role_word(subject):
        return False
    object_text = _compact_text(match.group("object")).strip(" .")
    return bool(object_text)


def _is_release_readiness_product_phrase(words: Sequence[str]) -> bool:
    if len(words) < 3 or words[:2] != ["release", "readiness"] or "for" not in words:
        return False
    return not bool(set(words) & {"complete", "prove", "proof", "succeed", "validate"})


def _semantic_words(value: str) -> list[str]:
    aliases = {
        "completed": "complete",
        "completes": "complete",
        "proven": "prove",
        "proves": "prove",
        "succeeds": "succeed",
        "validated": "validate",
        "validates": "validate",
    }
    words: list[str] = []
    for raw in _compact_text(value).replace("-", " ").split():
        word = raw.strip(".,:;()[]{}").casefold()
        if word:
            words.append(aliases.get(word, word))
    return words


def _compact_text(value: str) -> str:
    return " ".join(str(value or "").split())


__all__ = [
    "drop_release_proof_control_steps",
    "is_release_proof_control_step",
    "is_supporting_setup_step",
]
