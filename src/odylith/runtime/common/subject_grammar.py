"""Small presentation-only grammatical-number helpers."""

from __future__ import annotations


def present_verb(value: str, *, singular: str, plural: str) -> str:
    """Choose display copy by the visible grammatical subject, never product meaning."""

    text = " ".join(str(value or "").split()).casefold()
    words = _words(text)
    if not words:
        return singular
    head = next(
        (word for word in reversed(words) if word not in {"context", "detail", "evidence", "state"}),
        words[-1],
    )
    if " and " in f" {text} ":
        return plural
    if head.endswith("s") and head not in {"status", "process"}:
        return plural
    return singular


def _words(value: str) -> list[str]:
    words: list[str] = []
    current: list[str] = []
    for char in value:
        if char.isalpha() or (current and char in "'-"):
            current.append(char)
            continue
        if current:
            words.append("".join(current).strip("'-"))
            current = []
    if current:
        words.append("".join(current).strip("'-"))
    return [word for word in words if word]


__all__ = ["present_verb"]
