"""Shared text coercion for greenfield proposal runtime paths."""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from typing import Any

_LIST_SPLIT_RE = re.compile(r"(?:\r?\n|;)+")
_COMMA_LIST_SPLIT_RE = re.compile(r"(?:\r?\n|;|,)+")
_LIST_BULLET_RE = re.compile(r"^\s*(?:[-*]|\d+[.)])\s*")


def clean_text(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def word_count(value: Any) -> int:
    return len(visible_words(value))


def word_occurrences(value: Any, word: Any) -> int:
    token = clean_text(word)
    if not token:
        return 0
    return len(
        re.findall(
            rf"\b{re.escape(token)}\b",
            clean_text(value),
            re.IGNORECASE,
        )
    )


def normalize_visible_result_language(value: Any) -> str:
    text = clean_text(value)
    text = re.sub(r"\bvisible[- ]result\s+event\b", "visible result", text, flags=re.IGNORECASE)
    text = re.sub(r"\breadout\s+plus\b", "readout and", text, flags=re.IGNORECASE)
    text = re.sub(r"\bon\s+screen,\s+alongside\b", "on screen with", text, flags=re.IGNORECASE)
    text = re.sub(r"\balongside\b", "with", text, flags=re.IGNORECASE)
    return clean_text(text)


def normalize_proof_boundary_language(value: Any) -> str:
    text = clean_text(value).strip(" .:")
    if not text:
        return ""
    replacements = (
        (r"^what\s+would\s+count\s+as\s+evidence[^:]*:\s*", ""),
        (r"^(?:accepted\s+first\s+path|visible\s+outcome)\s+proof\s*:\s*", ""),
        (r"^done\s+means\s*:?\s*", ""),
        (r"^the\s+first\s+proof\s+is\s+", ""),
        (r"^(?:the\s+)?first\s+version\s+is\s+proven\s+when\s+", ""),
        (r"^(?:release\s+[A-Za-z0-9_.-]+\s+)?(?:is\s+)?proven\s+when\s+", ""),
        (r"^(?:release\s+[A-Za-z0-9_.-]+\s+|the\s+release\s+)?(?:is\s+)?trusted\s+only\s+when\s+", ""),
        (r"^(?:the\s+)?first\s+release\s+works\s+when\s+", ""),
        (r"^release\s+[A-Za-z0-9_.-]+\s+succeeds\s+when\s+", ""),
        (r"^the\s+release\s+succeeds\s+when\s+", ""),
        (r"^(?:the\s+)?accepted\s+path\s+can\s+be\s+replayed\s+from\s+", "replay "),
    )
    for pattern, replacement in replacements:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        text = clean_text(text).strip(" .:")
    text = re.split(r"\bwhat\s+must\s+not\s+be\s+claimed\s+yet\b", text, maxsplit=1, flags=re.IGNORECASE)[0]
    return clean_text(text).strip(" .:")


def clip_text_at_word_boundary(
    value: Any,
    *,
    limit: int,
    dangling_words: Iterable[str] = (),
    strip_edges: str = "",
    rstrip_chars: str = " ,;:",
) -> str:
    text = clean_text(value)
    if strip_edges:
        text = text.strip(strip_edges)
    if len(text) <= limit:
        return text
    clipped = text[: max(0, limit)].rstrip(rstrip_chars)
    if " " in clipped:
        clipped = clipped.rsplit(" ", 1)[0].rstrip(rstrip_chars)
    return strip_dangling_word_tail(clipped, dangling_words=dangling_words, rstrip_chars=rstrip_chars)


def strip_dangling_word_tail(
    value: Any,
    *,
    dangling_words: Iterable[str],
    rstrip_chars: str = " ,;:.",
) -> str:
    words = clean_text(value).rstrip(rstrip_chars).split()
    dangling = {clean_text(word).casefold().strip(".,;:") for word in dangling_words}
    dangling.discard("")
    while words and words[-1].casefold().strip(".,;:") in dangling:
        words.pop()
    return " ".join(words).rstrip(rstrip_chars)


def visible_words(value: Any) -> tuple[str, ...]:
    return tuple(re.findall(r"[A-Za-z0-9]+", clean_text(value)))


def progression_marker_count(
    value: Any,
    *,
    connectors: Iterable[str] = (),
    punctuation: str = "",
) -> int:
    text = clean_text(value)
    connector_set: set[str] = set()
    for connector in connectors:
        cleaned = clean_text(connector).casefold()
        if cleaned:
            connector_set.add(cleaned)
    count = sum(1 for word in visible_words(text) if word.casefold() in connector_set)
    return count + sum(text.count(mark) for mark in punctuation)


def normalize_domain_token(value: Any, *, minimum: int = 4, stopwords: Iterable[str] = ()) -> str:
    """Normalize one extracted product term without corrupting common nouns.

    Greenfield renderers use these tokens to derive artifact nouns from the
    accepted intent. The normalization must stay conservative because a bad
    stem leaks directly into human-visible governance text.
    """

    token = str(value or "").strip("-_").casefold()
    if len(token) < minimum or token.isdigit() or any(char.isdigit() for char in token):
        return ""
    stop = {str(item or "").casefold() for item in stopwords}
    if token in stop:
        return ""
    if token.endswith("ies") and len(token) > 5:
        token = f"{token[:-3]}y"
    elif token == "statuses":
        token = "status"
    elif token.endswith(("ches", "shes", "xes", "zes", "sses")) and len(token) > 5:
        token = token[:-2]
    elif token.endswith("s") and len(token) > 4 and not token.endswith(("ss", "us", "is")):
        token = token[:-1]
    return token if len(token) >= minimum and token not in stop else ""


def text_values(
    value: Any,
    *,
    split_scalar: bool = False,
    split_commas: bool = False,
    strip_bullets: bool = False,
) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, Mapping):
        values: list[str] = []
        for nested in value.values():
            values.extend(
                text_values(
                    nested,
                    split_scalar=split_scalar,
                    split_commas=split_commas,
                    strip_bullets=strip_bullets,
                )
            )
        return unique_text(values)
    if isinstance(value, (list, tuple, set)):
        values = []
        for nested in value:
            values.extend(
                text_values(
                    nested,
                    split_scalar=split_scalar,
                    split_commas=split_commas,
                    strip_bullets=strip_bullets,
                )
            )
        return unique_text(values)
    if not split_scalar:
        token = clean_text(value)
        return (token,) if token else ()
    splitter = _COMMA_LIST_SPLIT_RE if split_commas else _LIST_SPLIT_RE
    values = []
    for part in splitter.split(str(value or "").strip()):
        raw = _LIST_BULLET_RE.sub("", part) if strip_bullets else part
        token = clean_text(raw)
        if token:
            values.append(token)
    return unique_text(values)


def unique_text(values: Iterable[Any]) -> tuple[str, ...]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        for token in text_values(value):
            key = token.casefold()
            if key in seen:
                continue
            seen.add(key)
            result.append(token)
    return tuple(result)


def collect_text_values(
    row: Mapping[str, Any],
    fields: Iterable[str],
    *,
    split_scalar: bool = False,
    split_commas: bool = False,
) -> tuple[str, ...]:
    values: list[str] = []
    for field in fields:
        values.extend(text_values(row.get(field), split_scalar=split_scalar, split_commas=split_commas))
    return tuple(values)


def delimited_text_values(value: Any) -> tuple[str, ...]:
    return text_values(value, split_scalar=True, split_commas=True, strip_bullets=True)


def collect_delimited_text_values(row: Mapping[str, Any], fields: Iterable[str]) -> tuple[str, ...]:
    values: list[str] = []
    for field in fields:
        values.extend(delimited_text_values(row.get(field)))
    return tuple(values)


def join_sentence_text(value: Any) -> str:
    result = ""
    for token in text_values(value):
        if not result:
            result = token
            continue
        separator = " " if result[-1:] in {".", "!", "?"} else "; "
        result = f"{result}{separator}{token}"
    return result.strip()


def normalize_text_list(value: Any, *, split_commas: bool = False) -> list[str]:
    return list(
        text_values(
            value,
            split_scalar=True,
            split_commas=split_commas,
            strip_bullets=True,
        )
    )
