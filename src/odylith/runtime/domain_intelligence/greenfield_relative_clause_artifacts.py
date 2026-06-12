"""Normalize relative-clause fragments used as artifact phrases."""

from __future__ import annotations

import re

from odylith.runtime.domain_intelligence.greenfield_text import clean_text


def normalize_relative_clause_artifacts(value: str) -> str:
    text = clean_text(value).casefold().strip(" .,;:")
    if not text:
        return ""
    relative_tail = (
        r"(?:they|that|which)\s+"
        r"(?:(?:are|were|is|was)\s+)?"
        r"(?:meant|intended|expected|needed|required|supposed)"
        r"(?:\s+to\s+[a-z][a-z'-]*(?:\s+[a-z][a-z'-]*){0,4})?"
    )
    text = re.sub(
        rf"(?P<join>\band\s+)(?P<head>[a-z][a-z0-9'-]*(?:\s+[a-z][a-z0-9'-]*){{0,2}})\s+{relative_tail}",
        _joined_related_object,
        text,
        flags=re.I,
    )
    text = re.sub(
        rf"^(?P<head>[a-z][a-z0-9'-]*(?:\s+[a-z][a-z0-9'-]*){{0,2}})\s+{relative_tail}$",
        _standalone_related_object,
        text,
        flags=re.I,
    )
    return re.sub(r"\s+", " ", text).strip(" .,;:")


def _joined_related_object(match: re.Match[str]) -> str:
    head = _relative_clause_head(match.group("head"))
    return f"{match.group('join')}related {head}" if head else match.group(0)


def _standalone_related_object(match: re.Match[str]) -> str:
    head = _relative_clause_head(match.group("head"))
    return f"related {head}" if head else match.group(0)


def _relative_clause_head(value: str) -> str:
    words = [word.casefold().strip(".,;:") for word in clean_text(value).split() if word.strip(".,;:")]
    while words and words[0] in {"a", "an", "the", "their", "this", "that"}:
        words.pop(0)
    while words and words[-1] in {"a", "an", "and", "or", "the", "to", "with"}:
        words.pop()
    return " ".join(words) if 0 < len(words) <= 3 else ""


__all__ = ["normalize_relative_clause_artifacts"]
