"""Validation gate for operator-confirmed greenfield intent records."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_confirmed_system_rows import (
    contains_generic_system_scaffold,
)
from odylith.runtime.domain_intelligence.greenfield_confirmed_system_rows import (
    has_meaningful_system_description,
)
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import clean_confirmed_text
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import CONFIRMED_INTENT_VALIDATION_STOPWORDS
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import confirmed_text_values
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import semantic_terms
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import word_count


FIELD_MIN_WORDS = {
    "product_story": 28,
    "state_object": 12,
    "first_path": 18,
    "proof_boundary": 18,
}
LIST_ROW_MIN_WORDS = 5
SYSTEM_ROW_MIN_WORDS = 5

_META_NARRATION_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\bturn\s+the\s+.+?\s+intent\s+into\s+a\s+clear\s+product\s+narrative\b",
        r"\bmake\s+.+?\s+readable\s+as\s+one\s+product\s+story\b",
        r"\bbefore\s+source\s+work\s+starts\b",
        r"\bbefore\s+implementation\s+begins\b",
        r"\bgenerated\s+from\s+the\s+accepted\s+greenfield\b",
        r"\bstart\s+with\s+the\s+.+?\s+first\s+workflow\b",
        r"(?<![-\w])first\s+workflow\b",
        r"\bworkflow\s+lead\b",
        r"\bworkflow\s+lead\s+and\s+beneficiary\b",
        r"\bperson\s+or\s+team\s+receiving\s+value\b",
        r"\bvisible\s+completion\b",
        r"\bproduct\s+promise\b",
        r"\brelease\s+claim\b",
        r"\bstate\s+record\b",
        r"\bevidence\s+packet\b",
        r"\bfixture-backed\s+inputs\b",
        r"\bdocumented\s+non-goals\b",
    )
]

def validate_confirmed_intent(intent: Mapping[str, Any]) -> None:
    missing: list[str] = []
    for key, minimum in FIELD_MIN_WORDS.items():
        if key == "product_story" and _product_story_is_clear_enough(intent):
            continue
        if word_count(clean_confirmed_text(intent.get(key))) < minimum:
            missing.append(key)
    actor_rows = confirmed_text_values(intent.get("human_actors"))
    if not actor_rows:
        missing.append("human_actors")
    elif any(word_count(row) < LIST_ROW_MIN_WORDS for row in actor_rows):
        missing.append("human_actors")
    system_rows = confirmed_text_values(intent.get("internal_systems"))
    if len(system_rows) < 2:
        missing.append("internal_systems")
    elif any(not has_meaningful_system_description(row, minimum_words=SYSTEM_ROW_MIN_WORDS) for row in system_rows):
        missing.append("internal_systems")
    if contains_meta_narration(intent):
        missing.append("product_narrative")
    if contains_generic_system_scaffold(system_rows):
        missing.append("internal_systems")
    missing.extend(_qualitative_intent_gaps(intent))
    if missing:
        formatted = ", ".join(dict.fromkeys(missing))
        raise ValueError(
            "confirmed greenfield create needs the operator-confirmed Product Intent Confirmation; "
            f"missing or too thin: {formatted}. Write the visible confirmation to a Markdown file "
            "and pass it with --intent-file."
        )


def contains_meta_narration(intent: Mapping[str, Any]) -> bool:
    text = " ".join(
        [
            clean_confirmed_text(intent.get("product_story")),
            clean_confirmed_text(intent.get("first_path")),
            clean_confirmed_text(intent.get("proof_boundary")),
            " ".join(confirmed_text_values(intent.get("human_actors"))),
            " ".join(confirmed_text_values(intent.get("internal_systems"))),
        ]
    )
    return any(pattern.search(text) for pattern in _META_NARRATION_PATTERNS)


def _product_story_is_clear_enough(intent: Mapping[str, Any]) -> bool:
    story = clean_confirmed_text(intent.get("product_story"))
    if word_count(story) < 12:
        return False
    if not _has_meaningful_story_shape(story):
        return False
    context = " ".join(
        part
        for part in (
            " ".join(confirmed_text_values(intent.get("human_actors"))),
            " ".join(confirmed_text_values(intent.get("internal_systems"))),
            clean_confirmed_text(intent.get("state_object")),
            clean_confirmed_text(intent.get("first_path")),
        )
        if part
    )
    return _has_semantic_overlap(story, context, minimum=1)


def _qualitative_intent_gaps(intent: Mapping[str, Any]) -> list[str]:
    gaps: list[str] = []
    story = clean_confirmed_text(intent.get("product_story"))
    state = clean_confirmed_text(intent.get("state_object"))
    path = clean_confirmed_text(intent.get("first_path"))
    proof = clean_confirmed_text(intent.get("proof_boundary"))
    actors = " ".join(confirmed_text_values(intent.get("human_actors")))
    systems = " ".join(confirmed_text_values(intent.get("internal_systems")))
    context = " ".join(part for part in (story, state, actors, systems, proof) if part)

    if story and not (
        _has_meaningful_story_shape(story) and _has_semantic_overlap(story, f"{actors} {systems} {state}", minimum=1)
    ):
        gaps.append("product_story")
    if state and not (_has_meaningful_sentences(state, minimum=1) and has_progression_or_outcome(state)):
        gaps.append("state_object")
    if path and not (has_progression_or_outcome(path) and _has_semantic_overlap(path, context, minimum=2)):
        gaps.append("first_path")
    if proof and not (
        has_progression_or_outcome(proof)
        and _has_semantic_overlap(proof, f"{story} {state} {path} {systems}", minimum=1)
    ):
        gaps.append("proof_boundary")
    if actors and not _has_semantic_overlap(actors, f"{story} {path}", minimum=1):
        gaps.append("human_actors")
    if systems and not _has_semantic_overlap(systems, f"{story} {state} {path} {proof}", minimum=2):
        gaps.append("internal_systems")
    return gaps


def _has_meaningful_sentences(text: str, *, minimum: int) -> bool:
    sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+", clean_confirmed_text(text)) if word_count(part) >= 8]
    return len(sentences) >= minimum or word_count(clean_confirmed_text(text)) >= minimum * 18


def _has_meaningful_story_shape(text: str) -> bool:
    cleaned = clean_confirmed_text(text)
    if _has_meaningful_sentences(cleaned, minimum=2):
        return True
    if not _has_meaningful_sentences(cleaned, minimum=1):
        return False
    if has_progression_or_outcome(cleaned):
        return True
    return bool(
        re.search(
            r"\b(?:need|needs|want|wants|help|helps|manage|manages|track|tracks|record|records|show|shows|"
            r"understand|decide|trust|review|route|collect|reduce|avoid|prevent|resolve|coordinate)\b",
            cleaned,
            re.IGNORECASE,
        )
    )


def has_progression_or_outcome(text: str) -> bool:
    cleaned = clean_confirmed_text(text)
    if (
        len(
            re.findall(
                r"\b(?:starts?|ends?|then|after|before|when|until|from|to|through|with|without)\b",
                cleaned,
                re.IGNORECASE,
            )
        )
        >= 2
    ):
        return True
    if len(re.findall(r"[,;:]", cleaned)) >= 2:
        return True
    return word_count(cleaned) >= 24 and bool(
        re.search(
            r"\b(?:result|outcome|proof|evidence|state|status|decision|completed|blocked|accepted|rejected|safe|unsafe)\b",
            cleaned,
            re.IGNORECASE,
        )
    )


def _has_semantic_overlap(left: str, right: str, *, minimum: int) -> bool:
    left_terms = semantic_terms(left, stopwords=CONFIRMED_INTENT_VALIDATION_STOPWORDS)
    right_terms = semantic_terms(right, stopwords=CONFIRMED_INTENT_VALIDATION_STOPWORDS)
    return len(left_terms & right_terms) >= minimum
