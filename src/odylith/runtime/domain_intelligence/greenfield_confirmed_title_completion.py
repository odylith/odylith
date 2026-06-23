"""Title derivation for completed greenfield confirmed intents."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_confirmed_system_completion import state_label as _state_label
from odylith.runtime.domain_intelligence.greenfield_confirmed_system_completion import system_labels as _system_labels
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import GENERIC_TITLE_WORDS as _GENERIC_TITLE_WORDS
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import clean_confirmed_text as _clean
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import confirmed_text_values
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import focus_label as _focus_label
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import semantic_overlap as _semantic_overlap
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import title_case_text as _title_case
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import word_count as _word_count
from odylith.runtime.domain_intelligence.greenfield_domain_term_index import label_terms
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import normalize_project_title


def title(intent: Mapping[str, Any]) -> str:
    return _clean(intent.get("title")) or "Greenfield Project"


def title_needs_repair(value: str) -> bool:
    text = _clean(value)
    if normalize_project_title(text).changed:
        return True
    if not text or text.casefold() == "greenfield project":
        return True
    words = label_terms(text)
    if not words:
        return True
    tail = words[-1].casefold()
    if tail in {"a", "an", "and", "for", "from", "in", "of", "on", "or", "the", "to", "with"}:
        return True
    lowered = text.casefold()
    return len(words) > 10 and bool(
        re.search(r"\b(?:that|what|so|because|captures?|follows?|makes?|buying|using|needs?|wants?)\b", lowered)
    )


def derived_title(intent: Mapping[str, Any], *, fallback: str) -> str:
    system_labels = [_clean(label) for label in _system_labels(intent) if _clean(label)]
    context = _title_context(intent)
    noun = _title_noun(context, system_labels)
    qualifier = _title_qualifier(context, system_labels, noun=noun)
    if qualifier and noun:
        return _title_case(f"{qualifier} {noun}")
    for label in system_labels:
        if 2 <= _word_count(label) <= 7:
            return _title_case(label)
    state_label = _state_label(_clean(intent.get("state_object")), title=fallback)
    if 2 <= _word_count(state_label) <= 7:
        return _title_case(state_label)
    return _focus_label(fallback)


def _title_context(intent: Mapping[str, Any]) -> str:
    parts = [
        _clean(intent.get("product_story")),
        _clean(intent.get("state_object")),
        _clean(intent.get("first_path")),
        _clean(intent.get("proof_boundary")),
        " ".join(confirmed_text_values(intent.get("internal_systems"))),
    ]
    return ". ".join(part.strip(" .") for part in parts if part)


def _title_noun(context: str, system_labels: Sequence[str]) -> str:
    nouns = (
        "workbench",
        "workspace",
        "watchlist",
        "journal",
        "dashboard",
        "tracker",
        "registry",
        "ledger",
        "portal",
        "planner",
        "viewer",
        "console",
        "list",
        "profile",
        "record",
        "workflow",
    )
    combined = " ".join([context, *system_labels]).casefold()
    for noun in nouns:
        if re.search(rf"\b{re.escape(noun)}s?\b", combined):
            return noun
    return "workspace"


def _title_qualifier(context: str, system_labels: Sequence[str], *, noun: str) -> str:
    candidates: list[tuple[int, str]] = []
    sources = [*system_labels, context]
    for source in sources:
        text = _clean(source)
        for match in re.finditer(
            r"\b(?P<phrase>[A-Za-z][A-Za-z0-9_'/&-]*(?:\s+[A-Za-z][A-Za-z0-9_'/&-]*){0,2})\s+"
            r"(?P<noun>activity|signal|signals|case|cases|record|records|item|items|request|requests|submission|submissions|evidence|data|profile|profiles)\b",
            text,
        ):
            phrase = _clean(f"{match.group('phrase')} {match.group('noun')}")
            phrase = re.sub(r"^(?:a|an|the)\s+", "", phrase, flags=re.IGNORECASE)
            if _usable_title_phrase(phrase, noun=noun):
                candidates.append((_semantic_overlap(phrase, context), phrase))
    for label in system_labels:
        words = [
            word
            for word in label_terms(label)
            if word.casefold() not in _GENERIC_TITLE_WORDS and word.casefold() != noun.casefold()
        ]
        if 1 <= len(words) <= 3:
            phrase = " ".join(words)
            if _usable_title_phrase(phrase, noun=noun):
                candidates.append((_semantic_overlap(phrase, context), phrase))
    candidates.sort(key=lambda item: (-item[0], len(item[1])))
    return candidates[0][1] if candidates else ""


def _usable_title_phrase(value: str, *, noun: str) -> bool:
    text = _clean(value)
    if not text:
        return False
    lowered = text.casefold()
    banned_words = {
        "can",
        "adds",
        "chooses",
        "compare",
        "compares",
        "could",
        "decide",
        "deserves",
        "doing",
        "each",
        "follow",
        "make",
        "makes",
        "needs",
        "only",
        "records",
        "reviews",
        "sees",
        "selected",
        "should",
        "that",
        "those",
        "whether",
        "what",
        "when",
        "where",
        "which",
        "who",
        "why",
        "will",
        "wants",
    }
    if any(word in banned_words for word in lowered.split()):
        return False
    if noun.casefold() in lowered:
        return False
    if any(word in _GENERIC_TITLE_WORDS for word in lowered.split()):
        return False
    return _word_count(text) <= 4


__all__ = ["derived_title", "title", "title_needs_repair"]
