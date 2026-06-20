"""Text normalization helpers for confirmed greenfield proposal records."""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from typing import Any

from odylith.runtime.common.prose_grammar import looks_like_finite_action
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
    "final",
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

_TITLE_CONNECTOR_WORDS = {
    "a",
    "an",
    "and",
    "as",
    "at",
    "by",
    "for",
    "from",
    "her",
    "his",
    "in",
    "its",
    "of",
    "on",
    "or",
    "our",
    "the",
    "their",
    "to",
    "with",
    "your",
}
_TITLE_ACRONYMS = {"ai", "api", "crm", "gis", "iot", "llm", "ml", "pwa", "ui", "ux"}
_TITLE_HYPHEN_MODIFIERS = {
    "back",
    "cross",
    "end",
    "first",
    "front",
    "grown",
    "high",
    "last",
    "long",
    "low",
    "medium",
    "multi",
    "near",
    "read",
    "real",
    "self",
    "short",
    "single",
    "source",
    "user",
    "write",
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
    connectors = {"a", "an", *_TITLE_CONNECTOR_WORDS}
    for index, word in enumerate(clean_confirmed_text(value).split()):
        lower = word.casefold()
        label_word = _title_label_word(word)
        if _append_slash_conjunction_title_word(words, raw_word=word, label_word=label_word):
            continue
        if index > 0 and lower in connectors:
            words.append(lower)
        else:
            words.append(label_word)
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
        r"\b(?:the\s+)?(?:unit\s+of\s+truth|source\s+of\s+truth|central\s+object|core\s+unit|core\s+record|main\s+record)\s+is\s+"
        r"(?:(?:the|an|a|one)\s+)?(?P<label>[^.;:]+)(?=$|[:;])",
        r"^(?:the\s+)?(?:core|main|primary)\s+(?:thing|object|record|item)\s+"
        r"(?:the\s+system\s+)?(?:tracks|records|stores|captures|keeps)\s+is\s+"
        r"(?:(?:the|an|a)\s+)?(?P<label>[^.;:]+)(?=$|[:;])",
        r"^(?:the\s+)?(?:central|core|main|primary)\s+(?:thing|object|record|item|state)\s+"
        r"(?:the\s+product\s+|the\s+system\s+)?(?:tracks|records|stores|captures|keeps)\s+is\s+"
        r"(?:(?:the|an|a)\s+)?(?P<label>[^.;:]+)(?=$|[:;])",
        r"^(?:the\s+)?(?:durable\s+thing|durable\s+object|durable\s+record)\s+"
        r"(?:the\s+product\s+|the\s+system\s+)?(?:holds|tracks|records|stores|captures|keeps)\s+is\s+"
        r"(?:(?:the|an|a)\s+)?(?P<label>[^.;:]+)(?=$|[:;])",
        r"\b(?:the\s+)?(?:primary\s+)?state\s+object\s+is\s+(?:(?:the|an|a)\s+)?(?P<label>[^.;:]+)(?=$|[:;])",
        r"\b(?:the\s+)?(?:domain\s+)?object\s+is\s+(?:(?:the|an|a)\s+)?(?P<label>[^.;:]+)(?=$|[:;])",
        r"\b(?:the\s+)?proof\s+record\s+is\s+(?:(?:the|an|a)\s+)?(?P<label>[^.;:]+)(?=$|[:;])",
        r"^(?:the|an|a|one)\s+(?P<label>[A-Za-z][A-Za-z0-9 _'’/-]{1,80}?)\s*:",
        r"^(?:the\s+)?product\s+(?:captures?|keeps?|records?|stores?|tracks?)\s+"
        r"(?:(?:the|an|a)\s+)?(?P<label>[A-Za-z][A-Za-z0-9 _'’/-]{1,80}?)\s+"
        r"(?:with|containing|including|that|for)\b",
        r"^(?:the\s+)?(?:product|system|app|application|workspace|service|platform|tool)\s+"
        r"(?:manages?|maintains?|coordinates?|orchestrates?)\s+"
        r"(?:(?:the|an|a)\s+)?(?P<label>[A-Za-z][A-Za-z0-9 _'’/-]{1,80}?)\s*"
        r"(?:,\s*)?(?:with|containing|including|that|for)\b",
        r"^(?:the|an|a|one)\s+(?P<label>[A-Za-z][A-Za-z0-9 _'’/-]{1,80}?)\s+"
        r"(?:with|containing|that|for)\b",
        r"^(?:the|an|a|one)\s+(?P<label>[A-Za-z][A-Za-z0-9 _'’/-]{1,80}?)\s+"
        r"(?:holding|carrying|containing)\b",
        r"^(?:the|an|a)\s+(?P<label>[A-Za-z][A-Za-z0-9 _'’/-]{1,80}?)\s+"
        r"(?:tracks|records|stores|captures|moves|starts|changes)\b",
        r"^(?P<label>[A-Za-z][A-Za-z0-9 _'’/-]{1,80}?)\s+"
        r"(?:tracks|records|stores|captures|keeps|holds|manages|maintains|coordinates|orchestrates)\b",
    )
    for pattern in patterns:
        match = re.search(pattern, dash_head, flags=re.IGNORECASE)
        if match:
            candidate = match.group("label").strip(" :.-")
            return _domain_label(candidate) or fallback
    if dash_head and not re.search(
        r"\b(is|are|starts?|moves?|changes?|tracks?|records?|captures?|produces?|manages?|maintains?|coordinates?|orchestrates?|holding|carrying|containing)\b",
        dash_head,
        re.IGNORECASE,
    ):
        return title_label(dash_head) or fallback
    words = text.split()
    if len(words) <= 7:
        return title_label(text) or fallback
    return fallback


def _domain_label(value: str) -> str:
    text = clean_confirmed_text(value).strip(" :.-")
    text = re.sub(r"^(?:a|an|one|the)\s+", "", text, flags=re.IGNORECASE).strip(" :.-")
    text = re.sub(
        r"\s+for\s+(?:a|an|the)\s+(?:single\s+)?"
        r"(?:site|home|household|user|customer|account|team|tenant|organization|project|workspace|case)\b.*$",
        "",
        text,
        flags=re.IGNORECASE,
    ).strip(" :.-")
    return title_label(text)


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
    label_ref = sentence_label(label)
    if story and path:
        return (
            f"Without a clear first path, users cannot trust whether {label_ref} solves the accepted problem: "
            f"{story} The proof path is {path}."
        )
    if story:
        return (
            f"Without source-backed proof, users cannot trust whether {label_ref} solves the accepted problem: {story}."
        )
    return (
        f"Without an explicit problem, first path, and proof boundary, {label_ref} cannot be trusted as "
        "implementation-ready."
    )


def state_detail_summary(value: str, *, state_label: str, limit: int = 280) -> str:
    summary = short_summary(value, limit=limit)
    if not summary:
        return ""
    summary = _strip_state_object_predicate(summary)
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


def state_detail_restates_label_with_finite_action(detail: str, *, state_label: str) -> bool:
    label = clean_confirmed_text(state_label).strip(" .")
    if not label:
        return False
    label_pattern = re.escape(label).replace(r"\ ", r"\s+")
    match = re.match(
        rf"^(?:(?:the|an|a|one)\s+)?{label_pattern}\s+(?P<tail>[A-Za-z][^.;]*)$",
        clean_confirmed_text(detail).strip(" ."),
        flags=re.IGNORECASE,
    )
    if match is None:
        return False
    return looks_like_finite_action(match.group("tail"))


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
    head = _terminal_relative_item_label(head)
    head = re.split(r"\s+that\s+", head, maxsplit=1, flags=re.IGNORECASE)[0].strip(" .:-")
    split = re.search(
        r"\s+(?=(?:owned\s+by|captures?|capturing|validates?|validating|computes?|computing|converts?|converting|"
        r"evaluates?|evaluating|produces?|producing|returns?|returning|routes?|routing|records?|recording|stores?|storing|"
        r"shows?|showing|renders?|rendering|generates?|generating|calculates?|calculating|"
        r"configures?|configuring|groups?|grouping|aligns?|aligning|tracks?|tracking|manages?|managing)\b\s+\S)",
        head,
        flags=re.IGNORECASE,
    )
    if split:
        candidate = head[: split.start()].strip(" .:-")
        tail = head[split.start() :].strip(" .:-")
        if not _system_label_split_clips_noun_phrase(candidate, tail):
            head = candidate
    label = domain_object_label(head, fallback=head)
    if [word.casefold() for word in label.split()[-1:]] in (["and"], ["or"]):
        titled = title_label(head)
        if word_count(titled) > word_count(label):
            return titled
    return label


def _system_label_split_clips_noun_phrase(candidate: str, tail: str) -> bool:
    if candidate.casefold().strip(".,;:").split()[-1:] in (["and"], ["or"]):
        return True
    tail_words = [word.casefold().strip(".,;:") for word in tail.split()[:5]]
    if not tail_words:
        return False
    if len(tail_words) > 1 and tail_words[1] in _SYSTEM_LABEL_NOUNS:
        return True
    if tail_words[0] in {
        "capture",
        "captures",
        "capturing",
        "check",
        "checks",
        "checking",
        "log",
        "logs",
        "logging",
        "record",
        "records",
        "recording",
        "review",
        "reviews",
        "reviewing",
        "track",
        "tracks",
        "tracking",
        "view",
        "views",
        "viewing",
    }:
        return True
    if word_count(candidate) >= 2:
        return False
    return bool(
        set(tail_words)
        & _SYSTEM_LABEL_NOUNS
    )


def title_label(value: str) -> str:
    words = []
    for index, word in enumerate(compact_text(value).strip(" .").split()):
        lower = word.casefold()
        if index == 0 and lower in {"a", "an", "the"}:
            continue
        label_word = _title_label_word(word)
        if _append_slash_conjunction_title_word(words, raw_word=word, label_word=label_word):
            continue
        if lower in _TITLE_CONNECTOR_WORDS and words:
            words.append(lower)
            continue
        words.append(label_word)
    return " ".join(words).strip()


def _append_slash_conjunction_title_word(words: list[str], *, raw_word: str, label_word: str) -> bool:
    if not words or words[-1].casefold() != "and":
        return False
    if "/" not in raw_word or " and " not in label_word or re.search(r"://|^/", raw_word):
        return False
    parts = [part.strip() for part in label_word.split(" and ") if part.strip()]
    if len(parts) < 2:
        return False
    words.pop()
    if words:
        words[-1] = words[-1].rstrip(",") + ","
    for part in parts[:-1]:
        words.append(part.rstrip(",") + ",")
    words.append("and")
    words.append(parts[-1])
    return True


def _title_label_word(value: str) -> str:
    word = value.strip()
    if not word:
        return ""
    prefix = ""
    while word and word[0] in "([{":
        prefix += word[0]
        word = word[1:]
    suffix = ""
    while word and word[-1] in ")]},.;:!?":
        suffix = word[-1] + suffix
        word = word[:-1]
    if "/" in word and not re.search(r"://|^/", word):
        parts = [part for part in word.split("/") if part]
        if len(parts) > 1 and all(re.search(r"[A-Za-z]", part) for part in parts):
            formatted_parts = [_title_label_word(part) for part in parts]
            if all(part.isupper() and len(part) <= 5 for part in formatted_parts):
                label = "/".join(formatted_parts)
            else:
                label = " and ".join(formatted_parts)
            return prefix + label + suffix
    lower = word.casefold()
    if _looks_like_preserved_acronym_token(word):
        return prefix + word + suffix
    if lower in _TITLE_ACRONYMS:
        return prefix + lower.upper() + suffix
    if _should_split_human_hyphen_label(word):
        return prefix + " ".join(_title_label_word(part) for part in word.split("-") if part) + suffix
    return prefix + word[:1].upper() + word[1:] + suffix


def _looks_like_preserved_acronym_token(value: str) -> bool:
    letters = [char for char in value if char.isalpha()]
    if len(letters) < 2 or not all(char.isupper() for char in letters):
        return False
    return any(not char.isalpha() for char in value)


def sentence_label(value: str) -> str:
    """Return a sentence-safe label without losing source acronym tokens."""

    text = compact_text(value).strip()
    if not text:
        return ""
    return _restore_source_mixed_case_tokens(restore_source_acronym_number_tokens(text.casefold(), text), text)


def object_reference_phrase(value: str) -> str:
    """Return a label as an embedded object phrase."""

    text = sentence_label(value).strip(" .")
    if not text:
        return ""
    if re.match(r"^(?:a|an|her|his|its|one|our|that|the|their|this|your)\b", text, flags=re.IGNORECASE):
        return text
    return f"the {text}"


def restore_source_acronym_number_tokens(label: str, source: str) -> str:
    """Preserve source tokens like AI, API-2, or ISO-27001 after label shaping."""

    return _restore_source_acronym_number_tokens(label, source)


def _restore_source_acronym_number_tokens(label: str, source: str) -> str:
    text = label
    for match in re.finditer(r"\b[A-Z]{2,}(?:[/-][A-Za-z0-9]+)*\b", source):
        token = match.group(0)
        variants = {
            token,
            token.replace("-", " "),
            token.replace("/", " "),
            token.replace("-", " ").replace("/", " "),
        }
        for variant in variants:
            if not variant.strip():
                continue
            text = re.sub(rf"\b{re.escape(variant)}\b", token, text, flags=re.IGNORECASE)
    return text


def _restore_source_mixed_case_tokens(label: str, source: str) -> str:
    text = label
    for match in re.finditer(r"\b[A-Z][A-Za-z0-9_/-]*[A-Z][A-Za-z0-9_/-]*\b", source):
        token = match.group(0)
        text = re.sub(rf"\b{re.escape(token)}\b", token, text, flags=re.IGNORECASE)
    return text


def _strip_state_object_predicate(value: str) -> str:
    text = clean_confirmed_text(value).strip(" .")
    return re.sub(
        r"^(?:the\s+)?(?:product|system|app|application|workspace|service|platform|tool)\s+"
        r"(?:captures?|keeps?|records?|stores?|tracks?|holds?)\s+",
        "",
        text,
        count=1,
        flags=re.IGNORECASE,
    ).strip(" .")


def _should_split_human_hyphen_label(value: str) -> bool:
    if "-" not in value or "/" in value:
        return False
    parts = [part for part in value.split("-") if part]
    if len(parts) < 2 or len(parts) != len(value.split("-")):
        return False
    lowered = [part.casefold() for part in parts]
    if any(part in _TITLE_CONNECTOR_WORDS for part in lowered):
        return False
    if lowered[0] in _TITLE_HYPHEN_MODIFIERS:
        return False
    if any(part.endswith(("ed", "ing")) for part in lowered[1:]):
        return False
    return all(re.fullmatch(r"[A-Za-z0-9]+(?:'[A-Za-z0-9]+)?", part) for part in parts)


def join_items(items: list[str] | None, *, limit: int = 4) -> str:
    values = [
        _embedded_item_text(str(item), limit=180)
        for item in (items or [])
        if str(item).strip()
    ]
    values = [value for value in values if value]
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


def boundary_clause_text(items: list[str] | None, *, limit: int = 4, item_limit: int = 180) -> str:
    values = [
        clause
        for item in (items or [])
        if (clause := boundary_clause_item(str(item), limit=item_limit))
    ]
    return "; ".join(values[:limit])


def boundary_clause_item(value: str, *, limit: int = 180) -> str:
    text = short_summary(value, limit=limit).strip(" .")
    if not text:
        return ""
    if text.startswith("Whether "):
        rest = text[len("Whether ") :].strip(" .")
        lowered = rest.casefold()
        for marker in (" is in scope", " are in scope"):
            marker_index = lowered.find(marker)
            if marker_index > 0:
                subject = rest[:marker_index].strip(" .")
                return f"{_lower_first(subject)} scope remains deferred"
        return f"the question of whether {_lower_first(rest)} remains open"
    if text.endswith("?"):
        question = text.rstrip("?").strip()
        scope = _scope_question_boundary(question)
        if scope:
            return scope
        return f"scope question remains open: {_lower_first(question)}"
    return _embedded_item_text(text, limit=limit)


_SYSTEM_LABEL_NOUNS = {
    "adapter",
    "api",
    "application",
    "catalog",
    "dashboard",
    "database",
    "engine",
    "export",
    "flow",
    "gateway",
    "ledger",
    "library",
    "model",
    "portal",
    "queue",
    "record",
    "records",
    "registry",
    "repository",
    "service",
    "source",
    "store",
    "surface",
    "system",
    "tool",
    "tracker",
    "view",
    "workspace",
}


def _embedded_item_text(value: str, *, limit: int) -> str:
    text = short_summary(value, limit=limit).strip(" .")
    if not text:
        return ""
    return _terminal_relative_item_label(text)


def _terminal_relative_item_label(value: str) -> str:
    text = compact_text(value).strip(" .")
    if not text:
        return ""
    if text.split()[-1].casefold().strip(".,;:") not in CONFIRMED_DANGLING_WORDS:
        return text
    noun_pattern = "|".join(sorted(re.escape(noun) for noun in _SYSTEM_LABEL_NOUNS))
    match = re.match(
        rf"^(?P<label>.+\b(?:{noun_pattern})\b)\s+"
        r"(?:that\s+)?"
        r"(?:(?:a|an|the|this|that|their|its|our|your)\s+)?"
        r"[a-z][a-z0-9'/-]*(?:\s+[a-z][a-z0-9'/-]*){0,5}\s+"
        r"(?:belongs?|connects?|hands?\s+off|links?|maps?|reports?|returns?|sends?|submits?|syncs?|writes?)\s+"
        r"(?:at|by|for|from|in|into|on|to|with)$",
        text,
        flags=re.IGNORECASE,
    )
    if not match:
        return text
    label = match.group("label").strip(" .")
    return label if word_count(label) >= 2 else text


def _scope_question_boundary(value: str) -> str:
    text = value.strip()
    if not text:
        return ""
    match = re.match(
        r"^(?:Is|Are)\s+(?P<subject>.+?)\s+in\s+scope(?:\s+[^?]*)?$",
        text,
        flags=re.IGNORECASE,
    )
    if match:
        subject = re.sub(r"\s+", " ", match.group("subject")).strip(" .")
        if subject:
            return f"{_lower_first(subject)} scope remains deferred"
    return ""


def _lower_first(value: str) -> str:
    text = value.strip()
    if not text:
        return ""
    return text[:1].lower() + text[1:]


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
