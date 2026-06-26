"""Shared grammar predicates for deferred greenfield scope clauses."""

from __future__ import annotations

import re


def _compact_text(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def has_terminal_deferral_predicate(value: str) -> bool:
    words = [word.strip(".,;:!?()[]{}").casefold() for word in _compact_text(value).split()]
    words = [word for word in words if word]
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


__all__ = ["has_terminal_deferral_predicate"]
