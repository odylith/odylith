"""Text normalization helpers for confirmed greenfield proposal records."""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_domain_term_index import label_terms, ordered_terms
from odylith.runtime.domain_intelligence.greenfield_text import clean_markdown_text
from odylith.runtime.domain_intelligence.greenfield_text import clip_text_at_word_boundary
from odylith.runtime.domain_intelligence.greenfield_text import text_values
from odylith.runtime.domain_intelligence.greenfield_text import unique_text
from odylith.runtime.domain_intelligence.greenfield_text import word_count as _generic_word_count
from odylith.runtime.domain_intelligence.greenfield_text import word_occurrences as _generic_word_occurrences


GENERIC_TITLE_WORDS = {
    "app",
    "application",
    "helper",
    "platform",
    "product",
    "service",
    "system",
    "tool",
    "tracker",
    "workspace",
}

CONFIRMED_SEMANTIC_STOPWORDS = {
    "and",
    "are",
    "before",
    "can",
    "for",
    "from",
    "has",
    "have",
    "into",
    "that",
    "the",
    "this",
    "with",
    "without",
}

CONFIRMED_INTENT_VALIDATION_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "can",
    "cost",
    "for",
    "from",
    "has",
    "have",
    "in",
    "into",
    "is",
    "it",
    "low",
    "of",
    "on",
    "or",
    "product",
    "project",
    "release",
    "should",
    "small",
    "system",
    "systems",
    "that",
    "the",
    "then",
    "this",
    "through",
    "to",
    "with",
    "without",
}

CONFIRMED_DANGLING_WORDS = {
    "a",
    "an",
    "and",
    "as",
    "at",
    "because",
    "by",
    "for",
    "from",
    "if",
    "in",
    "into",
    "of",
    "on",
    "or",
    "required",
    "the",
    "to",
    "when",
    "while",
    "with",
    "without",
}


def compact_text(value: str) -> str:
    return clean_markdown_text(value)


def clean_confirmed_text(value: Any) -> str:
    return clean_markdown_text(value)


def confirmed_text_values(value: object) -> list[str]:
    """Return cleaned scalar rows from confirmed-intent list fields."""

    if isinstance(value, str):
        cleaned = clean_confirmed_text(value)
        return [cleaned] if cleaned else []
    if not isinstance(value, Sequence) or isinstance(value, (bytes, bytearray)):
        return []
    return [cleaned for item in value if (cleaned := clean_confirmed_text(item))]


def sentence_confirmed_text(value: str) -> str:
    text = clean_confirmed_text(value).strip()
    if text and text[-1] not in ".!?":
        text += "."
    return text


def short_confirmed_text(value: str, *, fallback: str = "", limit: int = 220) -> str:
    text = clean_confirmed_text(value) or fallback
    if len(text) <= limit:
        return text.rstrip(".")
    return clip_text_at_word_boundary(
        text,
        limit=limit,
        dangling_words=CONFIRMED_DANGLING_WORDS,
        rstrip_chars=" ,;:.",
    )


def join_confirmed_items(values: Sequence[str]) -> str:
    cleaned = [clean_confirmed_text(value).rstrip(".") for value in values if clean_confirmed_text(value)]
    if len(cleaned) <= 1:
        return cleaned[0] if cleaned else ""
    if len(cleaned) == 2:
        return f"{cleaned[0]} and {cleaned[1]}"
    return ", ".join(cleaned[:-1]) + f", and {cleaned[-1]}"


def semantic_terms(text: str, *, stopwords: Iterable[str] | None = None) -> set[str]:
    stop = CONFIRMED_SEMANTIC_STOPWORDS if stopwords is None else set(stopwords)
    return set(
        ordered_terms(
            clean_confirmed_text(text),
            stopwords=stop,
            minimum=3,
            stem_ing=True,
            stem_ing_minimum_length=5,
        )
    )


def semantic_overlap(left: str, right: str) -> int:
    return len(semantic_terms(left) & semantic_terms(right))


def title_case_text(value: str) -> str:
    words: list[str] = []
    connectors = {"a", "an", "and", "as", "at", "by", "for", "from", "in", "of", "on", "or", "the", "to", "with"}
    for index, word in enumerate(clean_confirmed_text(value).split()):
        lower = word.casefold()
        if lower in {"ai", "api", "crm", "gis", "iot", "llm", "ml", "ui", "ux"}:
            words.append(lower.upper())
        elif index > 0 and lower in connectors:
            words.append(lower)
        else:
            words.append(word[:1].upper() + word[1:])
    return " ".join(words)


def word_count(value: str) -> int:
    return _generic_word_count(clean_confirmed_text(value))


def word_occurrences(value: str, word: str) -> int:
    return _generic_word_occurrences(clean_confirmed_text(value), clean_confirmed_text(word))


def focus_label(title: str) -> str:
    words = [
        word
        for word in label_terms(title)
        if word.casefold() not in GENERIC_TITLE_WORDS
    ]
    if not words:
        words = label_terms(title)[:3]
    return title_case_text(" ".join(words[:4]) or "Project")


def domain_object_label(value: str, *, fallback: str) -> str:
    text = compact_text(value)
    if not text:
        return fallback
    first_clause = re.split(r"[.;\n]", text, maxsplit=1)[0].strip(" :.-")
    dash_head = re.split(r"\s+[—-]\s+", first_clause, maxsplit=1)[0].strip(" :.-")
    patterns = (
        r"\b(?:the\s+)?(?:primary\s+)?state\s+object\s+is\s+(?:the\s+)?(?P<label>[^.;:]+)$",
        r"\b(?:the\s+)?(?:domain\s+)?object\s+is\s+(?:the\s+)?(?P<label>[^.;:]+)$",
        r"\b(?:the\s+)?proof\s+record\s+is\s+(?:the\s+)?(?P<label>[^.;:]+)$",
        r"^(?:the\s+)?product\s+(?:captures?|keeps?|records?|stores?|tracks?)\s+"
        r"(?:a|an|the)?\s*(?P<label>[A-Za-z][A-Za-z0-9 _-]{1,80}?)\s+"
        r"(?:with|containing|that|for)\b",
        r"^(?:a|an|the)\s+(?P<label>[A-Za-z][A-Za-z0-9 _-]{1,80}?)\s+"
        r"(?:tracks|records|stores|captures|moves|starts|changes)\b",
    )
    for pattern in patterns:
        match = re.search(pattern, dash_head, flags=re.IGNORECASE)
        if match:
            candidate = match.group("label").strip(" :.-")
            return title_label(candidate) or fallback
    if dash_head and not re.search(
        r"\b(is|are|starts?|moves?|changes?|tracks?|records?|captures?|produces?)\b",
        dash_head,
        re.IGNORECASE,
    ):
        return title_label(dash_head) or fallback
    words = text.split()
    if len(words) <= 7:
        return title_label(text) or fallback
    return fallback


def short_summary(value: str, *, limit: int = 280) -> str:
    text = compact_text(value).strip(" .")
    if not text:
        return ""
    text = re.sub(r"^(?:state object|first path|proof boundary|product story)\s*:\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^the first complete path to prove should be\s*:?\s+", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^first complete path to prove should be\s*:?\s+", "", text, flags=re.IGNORECASE)
    if len(text) <= limit:
        return text
    sentences = re.split(r"(?<=[.!?])\s+", text)
    selected: list[str] = []
    total = ""
    for sentence in sentences:
        candidate = " ".join([*selected, sentence]).strip()
        if len(candidate) > limit and selected:
            break
        selected.append(sentence)
        total = candidate
        if len(total) >= limit * 0.55:
            break
    if total:
        return total.strip(" .")
    clipped = clip_text_at_word_boundary(text, limit=max(0, limit - 1))
    clipped = strip_dangling_tail(clipped)
    return clipped


def strip_dangling_tail(value: str) -> str:
    text = compact_text(value).rstrip(" ,;:.")
    while True:
        text = re.sub(r"(?:^|(?<=[.!?])\s+)It\s+should$", "", text, flags=re.IGNORECASE).rstrip(" ,;:.")
        cleaned = re.sub(
            r"\b(?:a|an|and|as|at|because|by|for|from|if|in|into|of|on|or|required|the|to|when|while|with|without)$",
            "",
            text,
            flags=re.IGNORECASE,
        ).rstrip(" ,;:.")
        if cleaned == text:
            return cleaned
        text = cleaned


def problem_text(*, label: str, problem: str, product_story: str, first_path: str) -> str:
    explicit = short_summary(problem, limit=360)
    if explicit:
        return explicit
    story = short_summary(product_story, limit=240)
    path = short_summary(first_path, limit=180)
    if story and path:
        return (
            f"Without a clear first path, users cannot trust whether {label.lower()} solves the accepted problem: "
            f"{story} The proof path is {path}."
        )
    if story:
        return (
            f"Without source-backed proof, users cannot trust whether {label.lower()} solves the accepted problem: {story}."
        )
    return (
        f"Without an explicit problem, first path, and proof boundary, {label.lower()} cannot be trusted as "
        "implementation-ready."
    )


def state_detail_summary(value: str, *, state_label: str, limit: int = 280) -> str:
    summary = short_summary(value, limit=limit)
    if not summary:
        return ""
    label_pattern = re.escape(state_label).replace(r"\ ", r"\s+")
    summary = re.sub(
        rf"^(?:the\s+)?(?:primary\s+)?state\s+object\s+is\s+(?:the\s+)?{label_pattern}\.?\s*",
        "",
        summary,
        flags=re.IGNORECASE,
    ).strip(" .")
    if summary.casefold() == state_label.casefold():
        return ""
    return summary


def join_system_labels(items: list[str] | None, *, limit: int = 4) -> str:
    values: list[str] = []
    for item in items or []:
        label = _system_label(item)
        if not label:
            continue
        values.append(label)
    values = [value for value in values if value]
    if not values:
        return ""
    selected = values[:limit]
    return ", ".join(selected)


def _system_label(value: str) -> str:
    text = compact_text(value)
    if not text:
        return ""
    head = re.split(r"\s+[—-]\s+|:\s+", text, maxsplit=1)[0].strip(" .:-")
    split = re.search(
        r"\s+(?=(?:owned\s+by|captures?|capturing|validates?|validating|computes?|computing|evaluates?|evaluating|"
        r"produces?|producing|returns?|returning|routes?|routing|records?|recording|stores?|storing|"
        r"shows?|showing|renders?|rendering|generates?|generating|calculates?|calculating|"
        r"configures?|configuring|groups?|grouping|aligns?|aligning|tracks?|tracking|manages?|managing)\b)",
        head,
        flags=re.IGNORECASE,
    )
    if split:
        head = head[: split.start()].strip(" .:-")
    return domain_object_label(head, fallback=head)


def title_label(value: str) -> str:
    words = []
    for index, word in enumerate(compact_text(value).strip(" .").split()):
        lower = word.casefold()
        if index == 0 and lower in {"a", "an", "the"}:
            continue
        if lower in {"and", "or", "of", "the", "to", "for", "in", "on", "with"} and words:
            words.append(lower)
            continue
        if lower in {"ai", "api", "crm", "gis", "iot", "llm", "ml", "pwa", "ui", "ux"}:
            words.append(lower.upper())
            continue
        words.append(word[:1].upper() + word[1:])
    return " ".join(words).strip()


def join_items(items: list[str] | None, *, limit: int = 4) -> str:
    values = [str(item).strip().rstrip(".") for item in (items or []) if str(item).strip()]
    if not values:
        return ""
    selected = values[:limit]
    return ", ".join(selected)


def join_brief_items(items: list[str] | None, *, limit: int = 3, item_limit: int = 120) -> str:
    values = [
        re.sub(r"\s+[-*]\s+", " ", short_summary(str(item), limit=item_limit)).strip(" ;")
        for item in (items or [])
        if str(item).strip()
    ]
    values = [value for value in values if value]
    if not values:
        return ""
    selected = values[:limit]
    return "; ".join(selected)


def clean_generated_text(value: Any) -> str:
    return compact_text(str(value or ""))


def sentence_text(value: Any, *, fallback: str = "", limit: int = 320) -> str:
    text = clean_generated_text(value) or fallback
    if not text:
        return ""
    if len(text) > limit:
        text = clip_text_at_word_boundary(text, limit=limit)
        text = strip_dangling_tail(text)
        text = text.rstrip(" ,;:")
    if text and text[-1] not in ".!?":
        text += "."
    return text


def set_sentence_text(row: dict[str, Any], key: str, value: str, *, limit: int = 700) -> bool:
    text = sentence_text(value, limit=limit)
    if clean_generated_text(row.get(key)) == text:
        return False
    row[key] = text
    return True


def set_sentence_list(row: dict[str, Any], key: str, values: Sequence[str], *, limit: int = 700) -> bool:
    cleaned = [sentence_text(value, limit=limit) for value in values if clean_generated_text(value)]
    cleaned = list(unique_text(cleaned))
    if text_values(row.get(key)) == tuple(cleaned):
        return False
    row[key] = cleaned
    return True
