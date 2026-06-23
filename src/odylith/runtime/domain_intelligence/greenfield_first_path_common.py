"""Shared first-path text cleanup and action-pattern primitives."""

from __future__ import annotations

import re
from typing import Any

from odylith.runtime.common.prose_grammar import action_verb_pattern
from odylith.runtime.domain_intelligence.greenfield_text import clean_markdown_text, clip_text_at_word_boundary
from odylith.runtime.domain_intelligence.greenfield_text import lower_plain_title_subject_fragment

MATERIAL_ACTION_RE = re.compile(
    rf"(?<![A-Za-z0-9_-])(?:{action_verb_pattern()})(?![A-Za-z0-9_-])",
    re.IGNORECASE,
)


def lowercase_leading_article(value: str) -> str:
    text = re.sub(
        r"^(?:A|An|The|Today|Tomorrow|This|That|With|Without)\b",
        lambda match: match.group(0).casefold(),
        clean_first_path_text(value).strip(" ."),
    )
    match = MATERIAL_ACTION_RE.search(text)
    return lower_plain_title_subject_fragment(text, action_offset=match.start() if match else 0)


def clip_first_path_phrase(value: str, *, limit: int) -> str:
    text = clean_first_path_text(value).strip(" .")
    if len(text) <= limit:
        return text
    return clip_text_at_word_boundary(
        text,
        limit=max(0, limit - 1),
        dangling_words={
            "a",
            "against",
            "alongside",
            "an",
            "and",
            "around",
            "as",
            "at",
            "because",
            "between",
            "by",
            "for",
            "from",
            "if",
            "in",
            "into",
            "of",
            "on",
            "or",
            "plus",
            "required",
            "that",
            "the",
            "this",
            "to",
            "toward",
            "towards",
            "through",
            "until",
            "via",
            "when",
            "while",
            "with",
            "without",
        },
    )


def clean_first_path_text(value: Any) -> str:
    text = clean_markdown_text(value)
    text = re.sub(r"\s+[–—-]\s*,\s+(?=(?:and|then|finally|later)\b)", ", ", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+[–—-]\s+(?=(?:and|then|finally|later)\b)", ", ", text, flags=re.IGNORECASE)
    text = re.sub(
        r"\s+[–—-]\s+one\s+(?:full|complete)\s+(?:loop|path|journey|flow)\b[^.!?]*(?=[.!?]|$)",
        "",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"\s+[–—-]\s*(?=[,.;:])", "", text)
    text = re.sub(r"\s+[–—-]\s*$", "", text)
    text = re.sub(
        r",?\s+and\s+(?:completes?|ends?|finishes?)\s+(?:the\s+)?(?:flow|journey|loop|moment|path|session)\b[^.!?]*(?=[.!?]|$)",
        "",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"(?:^|(?<=[.!?])\s+)that\s+single\s+(?:path|loop|journey|flow)\s+[–—-]\s*.*$",
        "",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"(?:^|(?<=[.!?])\s+)(?:this|that)\s+is\s+(?:one\s+)?(?:full|complete)\s+"
        r"(?:path|loop|journey|flow)\b.*$",
        "",
        text,
        flags=re.IGNORECASE,
    )
    return clean_markdown_text(text)


__all__ = ["MATERIAL_ACTION_RE", "clean_first_path_text", "clip_first_path_phrase", "lowercase_leading_article"]
