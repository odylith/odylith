"""Shared vocabulary for request word-sense metadata custody."""

from __future__ import annotations

from collections.abc import Sequence
import re

REQUEST_REPORTING_VERBS = frozenset(
    {
        "adds",
        "clarifies",
        "explains",
        "indicates",
        "notes",
        "says",
        "specifies",
        "states",
        "warns",
    }
)
WORD_SENSE_DESCRIPTOR_TERMS = frozenset(
    {
        "act",
        "acts",
        "action",
        "actions",
        "adjective",
        "adjectives",
        "adverb",
        "adverbs",
        "artifact",
        "artifacts",
        "entity",
        "entities",
        "gerund",
        "gerunds",
        "label",
        "labels",
        "name",
        "names",
        "noun",
        "nouns",
        "object",
        "objects",
        "operation",
        "operations",
        "participle",
        "participles",
        "predicate",
        "predicates",
        "record",
        "records",
        "subject",
        "subjects",
        "term",
        "terms",
        "verb",
        "verbs",
        "word",
        "words",
    }
)
WORD_SENSE_REPORTING_CONTENT_VERBS = frozenset(
    {
        "capture",
        "captures",
        "classifies",
        "classify",
        "contain",
        "contains",
        "demonstrate",
        "demonstrates",
        "display",
        "displays",
        "explain",
        "explains",
        "help",
        "helps",
        "include",
        "includes",
        "label",
        "labels",
        "map",
        "maps",
        "model",
        "models",
        "present",
        "presents",
        "render",
        "renders",
        "review",
        "reviews",
        "show",
        "shows",
        "teach",
        "teaches",
        "track",
        "tracks",
        "treat",
        "treats",
        "turn",
        "turns",
        "use",
        "uses",
    }
)
WORD_SENSE_REPORTING_CONTENT_MODALS = frozenset(
    {"can", "could", "may", "might", "must", "should", "will", "would"}
)
WORD_SENSE_CONTROL_CUSTODY_TERMS = frozenset(
    {
        "ambiguity",
        "ambiguous",
        "custody",
        "explicit",
        "governance",
        "ownership",
        "owned",
    }
)
WORD_SENSE_CONTROL_OBLIGATION_MODALS = frozenset({"has", "have", "must", "need", "needs", "should"})
WORD_SENSE_CONTROL_RESOLUTION_TERMS = frozenset({"explicit", "owned", "resolved"})


def word_sense_tail_starts_content_clause(tokens: Sequence[str]) -> bool:
    """Return whether a reporting tail starts a product clause before metadata."""

    index = 1 if tokens[:1] == ["that"] else 0
    if index < len(tokens) and tokens[index] in {"a", "an", "the", "this", "that"}:
        index += 1
    if index + 1 >= len(tokens):
        return False
    for verb_index in range(index + 1, min(len(tokens), index + 5)):
        token = tokens[verb_index]
        if token in {"as", "both"}:
            return False
        if token not in WORD_SENSE_REPORTING_CONTENT_VERBS and token not in WORD_SENSE_REPORTING_CONTENT_MODALS:
            continue
        subject_tokens = tokens[index:verb_index]
        if not subject_tokens:
            return False
        return True
    return False


def word_sense_tail_describes_comparison(tokens: Sequence[str]) -> bool:
    token_set = set(tokens)
    if not ("both" in token_set or sum(1 for token in tokens if token == "as") >= 2 or ("as" in token_set and "and" in token_set)):
        return False
    descriptor_tokens: Sequence[str]
    if "as" in tokens:
        descriptor_tokens = tokens[tokens.index("as") + 1 :]
    elif "both" in tokens:
        descriptor_tokens = tokens[tokens.index("both") + 1 :]
    else:
        descriptor_tokens = tokens
    return len({token for token in descriptor_tokens if token in WORD_SENSE_DESCRIPTOR_TERMS}) >= 2


def word_sense_content_clause_describes_comparison(tokens: Sequence[str]) -> bool:
    index = 1 if tokens[:1] == ["that"] else 0
    if index < len(tokens) and tokens[index] in {"a", "an", "the", "this", "that"}:
        index += 1
    if index + 1 >= len(tokens):
        return False
    for verb_index in range(index + 1, min(len(tokens), index + 5)):
        token = tokens[verb_index]
        if token in {"as", "both"}:
            return False
        if token not in WORD_SENSE_REPORTING_CONTENT_VERBS and token not in WORD_SENSE_REPORTING_CONTENT_MODALS:
            continue
        subject_tokens = tokens[index:verb_index]
        if not subject_tokens:
            return False
        return word_sense_tail_describes_comparison(tokens[verb_index + 1 :])
    return False


def word_sense_tail_has_control_obligation(tokens: Sequence[str]) -> bool:
    token_set = set(tokens)
    return bool(
        token_set & {"ambiguity", "custody", "governance", "ownership"}
        and token_set & WORD_SENSE_CONTROL_OBLIGATION_MODALS
        and token_set & WORD_SENSE_CONTROL_RESOLUTION_TERMS
    )


def strip_request_reporting_custody_tail(value: str) -> str:
    text = str(value or "").strip(" .")
    match = re.search(
        r"\s*,?\s+(?:so|therefore|thus|meaning|which\s+means)\s+"
        r"[^.]{0,120}\b(?:ambiguity|custody|governance|ownership)\b"
        r"[^.]{0,120}\b(?:has|have|must|needs?|should)\b"
        r"[^.]{0,120}\b(?:explicit|owned|resolved)\b.*$",
        text,
        flags=re.IGNORECASE,
    )
    if not match:
        return text
    return text[: match.start()].strip(" ,.;:")


__all__ = [
    "REQUEST_REPORTING_VERBS",
    "WORD_SENSE_CONTROL_CUSTODY_TERMS",
    "WORD_SENSE_DESCRIPTOR_TERMS",
    "WORD_SENSE_REPORTING_CONTENT_VERBS",
    "strip_request_reporting_custody_tail",
    "word_sense_content_clause_describes_comparison",
    "word_sense_tail_describes_comparison",
    "word_sense_tail_has_control_obligation",
    "word_sense_tail_starts_content_clause",
]
