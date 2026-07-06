"""Shared first-path text cleanup and action-pattern primitives."""

from __future__ import annotations

import re
from typing import Any

from odylith.runtime.common.prose_grammar import action_verb_pattern
from odylith.runtime.common.prose_grammar import strip_clipped_terminal_fragment
from odylith.runtime.common.prose_grammar import third_person_action_verb
from odylith.runtime.domain_intelligence.greenfield_text import clean_markdown_text, clip_text_at_word_boundary
from odylith.runtime.domain_intelligence.greenfield_text import dedupe_adjacent_words
from odylith.runtime.domain_intelligence.greenfield_text import lower_plain_title_subject_fragment
from odylith.runtime.domain_intelligence.greenfield_text import strip_dangling_word_tail

MATERIAL_ACTION_RE = re.compile(
    rf"(?<![A-Za-z0-9_-])(?:{action_verb_pattern()})(?![A-Za-z0-9_-])",
    re.IGNORECASE,
)
_FIRST_PATH_DANGLING_WORDS = frozenset(
    {
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
    }
)


def lowercase_leading_article(value: str) -> str:
    text = re.sub(
        r"^(?:A|An|The|Today|Tomorrow|This|That|With|Without)\b",
        lambda match: match.group(0).casefold(),
        clean_first_path_text(value).strip(" ."),
    )
    match = MATERIAL_ACTION_RE.search(text)
    return lower_plain_title_subject_fragment(text, action_offset=match.start() if match else 0)


def inline_first_path_scope_fragment(value: str) -> str:
    """Return a first-path fragment safe to embed inside a sentence."""

    text = clean_first_path_text(value).strip(" .")
    if not text:
        return ""
    compact = _compact_first_path_scope_fragment(text)
    if compact:
        text = compact
    text = re.sub(r",\s*(?:shows?|surfaces?)\s+progress,\s+and\s+", ", ", text, flags=re.IGNORECASE)
    text = _lower_initial_fragment(text)
    finite_action = action_verb_pattern(include_base=False, include_finite=True)
    return re.sub(
        rf"\b(?P<head>[a-z][a-z0-9'-]+)\s+(?P<title>[A-Z][a-z][A-Za-z0-9'-]*)\s+(?={finite_action}\b)",
        lambda match: f"{match.group('head')} {match.group('title').casefold()} ",
        text,
    ).strip()


def _compact_first_path_scope_fragment(value: str) -> str:
    """Project scope boundaries from first-path behavior instead of raw source prose."""

    try:
        from odylith.runtime.domain_intelligence.greenfield_first_path_clauses import readable_action_chain_phrase
        from odylith.runtime.domain_intelligence.greenfield_first_path_clauses import first_path_outcome_phrase
        from odylith.runtime.domain_intelligence.greenfield_first_path_semantics import first_path_model
    except ImportError:
        return ""
    compact = readable_action_chain_phrase(
        value,
        fallback="",
        limit=320,
        max_steps=6,
        include_visible_results=True,
    ).strip(" .")
    model = first_path_model(value)
    outcome = (model.visible_outcome or first_path_outcome_phrase(value, fallback="", limit=160)).strip(" .")
    if outcome and compact and _scope_missing_terminal_outcome(compact, outcome):
        candidate = f"{compact}; outcome: {outcome}"
        if len(candidate) <= 420:
            return candidate
    return compact


def _scope_missing_terminal_outcome(scope: str, outcome: str) -> bool:
    scope_terms = {
        word.casefold().strip(".,:;")
        for word in clean_first_path_text(scope).replace("-", " ").split()
        if len(word.strip(".,:;")) >= 4
    }
    outcome_terms = {
        word.casefold().strip(".,:;")
        for word in clean_first_path_text(outcome).replace("-", " ").split()
        if len(word.strip(".,:;")) >= 4
    }
    return bool(outcome_terms and not outcome_terms <= scope_terms)


def _lower_initial_fragment(value: str) -> str:
    text = clean_first_path_text(value).strip(" .")
    if not text:
        return ""
    first = text.split(maxsplit=1)[0]
    if first.isupper() and len(first) > 1:
        return text
    return f"{text[:1].lower()}{text[1:]}"


def clip_first_path_phrase(value: str, *, limit: int) -> str:
    text = clean_first_path_text(value).strip(" .")
    if len(text) <= limit:
        return text
    clipped = clip_text_at_word_boundary(
        text,
        limit=max(0, limit - 1),
        dangling_words=_FIRST_PATH_DANGLING_WORDS,
    )
    return _strip_incomplete_terminal_fragment(clipped)


def clean_first_path_text(value: Any) -> str:
    text = clean_markdown_text(value)
    text = re.sub(
        r"(^|(?<=[.!?])\s+)(?:a|the)\s+release\s+candidate\s+is\s+valid\s+when\s+(?:this\s+)?path\s+completes?\s*:\s*",
        lambda match: match.group(1),
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"^(?:the\s+)?job\s+is\s+to\s+complete\s+(?:this\s+)?release\s+path\s*:\s*",
        "",
        text,
        flags=re.IGNORECASE,
    )
    text = _strip_first_release_let_prefix(text)
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
    return _dedupe_repeated_first_path_sentences(dedupe_adjacent_words(clean_markdown_text(text)))


def _dedupe_repeated_first_path_sentences(value: str) -> str:
    sentences = [sentence.strip() for sentence in re.split(r"(?<=[.!?])\s+", str(value or "")) if sentence.strip()]
    if len(sentences) < 2:
        return str(value or "")
    seen: set[str] = set()
    rows: list[str] = []
    for sentence in sentences:
        key = re.sub(r"\W+", " ", sentence).casefold().strip()
        if key in seen:
            continue
        seen.add(key)
        rows.append(sentence)
    return " ".join(rows)


def _strip_first_release_let_prefix(value: str) -> str:
    base_verb_pattern = action_verb_pattern(include_base=True, include_finite=False)

    def replace(match: re.Match[str]) -> str:
        actor = match.group("actor").strip()
        verb = third_person_action_verb(match.group("verb"))
        return f"{actor} {verb}"

    text = re.sub(
        rf"^(?:the|this)\s+first\s+release\s+(?:should|must|will|needs?\s+to)\s+let\s+"
        rf"(?P<actor>(?:a|an|one|the)\s+[A-Za-z][A-Za-z0-9'/-]*(?:\s+[A-Za-z][A-Za-z0-9'/-]*){{0,4}}?)\s+"
        rf"(?P<verb>{base_verb_pattern})\b",
        replace,
        str(value or ""),
        count=1,
        flags=re.IGNORECASE,
    )
    if text != str(value or ""):
        return text
    return re.sub(
        r"^(?:the|this)\s+first\s+release\s+(?:should|must|will|needs?\s+to)\s+let\s+",
        "",
        str(value or ""),
        flags=re.IGNORECASE,
    )


def _strip_incomplete_terminal_fragment(value: str) -> str:
    text = clean_first_path_text(value).rstrip(" ,;:.")
    while True:
        repaired = strip_clipped_terminal_fragment(text)
        if repaired != text:
            text = repaired
            continue
        stripped = strip_dangling_word_tail(text, dangling_words=_FIRST_PATH_DANGLING_WORDS)
        if stripped == text:
            return text
        text = stripped


__all__ = [
    "MATERIAL_ACTION_RE",
    "clean_first_path_text",
    "clip_first_path_phrase",
    "inline_first_path_scope_fragment",
    "lowercase_leading_article",
]
