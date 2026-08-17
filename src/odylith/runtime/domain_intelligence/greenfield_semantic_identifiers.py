"""Deterministic filesystem-safe identifiers for typed semantic artifacts."""

from __future__ import annotations

import hashlib
import unicodedata


def semantic_artifact_identifier(
    value: object,
    *,
    fallback: str = "artifact",
    max_length: int = 96,
) -> str:
    """Project presentation text to one ASCII path identity without semantic parsing."""

    text = str(value or "").strip()
    words: list[str] = []
    current: list[str] = []
    for character in unicodedata.normalize("NFKD", text).casefold():
        if unicodedata.combining(character):
            continue
        if character.isascii() and character.isalnum():
            current.append(character)
        elif current:
            words.append("".join(current))
            current = []
    if current:
        words.append("".join(current))
    identifier = "-".join(words)[:max_length].rstrip("-")
    if identifier:
        return identifier
    if not text:
        return fallback
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]
    return f"{fallback}-{digest}"[:max_length].rstrip("-")


__all__ = ["semantic_artifact_identifier"]
