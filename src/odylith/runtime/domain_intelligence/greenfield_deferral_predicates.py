"""Structural presentation helpers for explicitly deferred scope rows."""

from __future__ import annotations

def _compact_text(value: str) -> str:
    return " ".join(str(value or "").split()).strip()


def _words(value: str) -> list[str]:
    return [word.strip(".,;:!?()[]{}·•") for word in _compact_text(value).split() if word.strip(".,;:!?()[]{}·•")]


def has_terminal_deferral_predicate(value: str) -> bool:
    words = [word.casefold() for word in _words(value)]
    for index, word in enumerate(words):
        if word not in {"are", "be", "is", "remain", "remains", "stay", "stays", "were"}:
            continue
        tail = [token for token in words[index + 1 :] if token not in {"currently", "explicitly", "intentionally"}]
        if not tail:
            continue
        if tail[0] == "deferred" or tail[0] == "outside":
            return True
        if tail[:3] == ["out", "of", "scope"]:
            return True
    return False


def terminal_deferral_subject(value: str) -> str:
    """Return the noun phrase before a terminal deferral predicate."""

    words = _words(str(value or "").replace("·", " ").replace("•", " "))
    for index, word in enumerate(words):
        if word.casefold() not in {"are", "be", "is", "remain", "remains", "stay", "stays", "were"}:
            continue
        subject = " ".join(words[:index]).strip(" .")
        tail = [
            token.casefold()
            for token in words[index + 1 :]
            if token.casefold() not in {"currently", "explicitly", "intentionally"}
        ]
        if not subject or not tail:
            continue
        if tail[0] == "deferred" and len(tail) <= 3:
            return subject
        if tail[0] == "outside" and len(tail) == 1:
            return subject
        if tail[:2] == ["outside", "scope"] and len(tail) <= 2:
            return subject
        if tail[:3] == ["out", "of", "scope"] and len(tail) <= 3:
            return subject
    return ""


__all__ = ["has_terminal_deferral_predicate", "terminal_deferral_subject"]
