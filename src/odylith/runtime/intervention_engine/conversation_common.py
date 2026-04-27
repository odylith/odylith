"""Shared primitives for intervention conversation rendering."""

from __future__ import annotations

import re
from typing import Any
from typing import Mapping
from typing import Sequence

from odylith.runtime.common.value_coercion import normalize_string as _normalize_string
from odylith.runtime.common.value_coercion import normalize_token as _normalize_token


_MEANINGFUL_TOKEN_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{1,}")
_TOKEN_STOPWORDS = {
    "a",
    "an",
    "and",
    "at",
    "by",
    "for",
    "from",
    "into",
    "its",
    "just",
    "not",
    "now",
    "off",
    "one",
    "only",
    "out",
    "same",
    "so",
    "stay",
    "that",
    "the",
    "then",
    "this",
    "too",
    "use",
    "with",
    "work",
}


def sequence_count(value: Any) -> int:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return len([item for item in value if _normalize_string(item)])
    return 1 if _normalize_string(value) else 0


def field(value: Any, name: str) -> Any:
    if isinstance(value, Mapping):
        return value.get(name)
    return getattr(value, name, None)


def request_context_payload(request: Any) -> dict[str, Any]:
    payload = field(request, "context_signals")
    return dict(payload) if isinstance(payload, Mapping) else {}


def first_present(*values: Any) -> Any:
    for value in values:
        if isinstance(value, str):
            if _normalize_string(value):
                return value
            continue
        if value is not None:
            return value
    return None


def bool_value(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    token = _normalize_token(value)
    if token in {"1", "true", "yes", "on"}:
        return True
    if token in {"", "0", "false", "no", "off"}:
        return False
    return bool(value)


def mapping_lookup(payload: Mapping[str, Any], key: str) -> Any:
    wanted = _normalize_token(key)
    for raw_key, raw_value in payload.items():
        if _normalize_token(raw_key) == wanted:
            return raw_value
    return None


def nested_mapping(payload: Mapping[str, Any], *path: str) -> dict[str, Any]:
    current: Any = payload
    for key in path:
        if not isinstance(current, Mapping):
            return {}
        current = mapping_lookup(current, key)
    return dict(current) if isinstance(current, Mapping) else {}


def count_phrase(count: int, singular: str, plural: str | None = None) -> str:
    noun = singular if count == 1 else (plural or f"{singular}s")
    return f"{count} {noun}"


def join_phrases(parts: Sequence[str]) -> str:
    filtered = [_normalize_string(part) for part in parts if _normalize_string(part)]
    if not filtered:
        return ""
    if len(filtered) == 1:
        return filtered[0]
    if len(filtered) == 2:
        return f"{filtered[0]}, then {filtered[1]}"
    return ", ".join(filtered[:-1]) + f", and {filtered[-1]}"


def join_items(parts: Sequence[str]) -> str:
    filtered = [_normalize_string(part) for part in parts if _normalize_string(part)]
    if not filtered:
        return ""
    if len(filtered) == 1:
        return filtered[0]
    if len(filtered) == 2:
        return f"{filtered[0]} and {filtered[1]}"
    return ", ".join(filtered[:-1]) + f", and {filtered[-1]}"


def lower_sentence_start(value: str) -> str:
    token = _normalize_string(value)
    return token[:1].lower() + token[1:] if len(token) > 1 and token[:1].isalpha() else token


def sentence_with_terminal_punctuation(value: str) -> str:
    token = _normalize_string(value)
    if not token:
        return ""
    return token if token.endswith(("!", "?", ".")) else f"{token}."


def dedupe_strings(values: Sequence[str]) -> list[str]:
    rows: list[str] = []
    seen: set[str] = set()
    for raw in values:
        token = _normalize_string(raw)
        if not token or token in seen:
            continue
        seen.add(token)
        rows.append(token)
    return rows


def recursive_items(value: Any) -> list[tuple[str, Any]]:
    rows: list[tuple[str, Any]] = []
    if isinstance(value, Mapping):
        for key, nested in value.items():
            rows.append((_normalize_token(key), nested))
            rows.extend(recursive_items(nested))
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for nested in value:
            rows.extend(recursive_items(nested))
    return rows


def recursive_strings(value: Any) -> list[str]:
    if isinstance(value, Mapping):
        rows: list[str] = []
        for nested in value.values():
            rows.extend(recursive_strings(nested))
        return rows
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        rows: list[str] = []
        for nested in value:
            rows.extend(recursive_strings(nested))
        return rows
    token = _normalize_string(value)
    return [token] if token else []


def meaningful_tokens(*values: str) -> set[str]:
    tokens: set[str] = set()
    for value in values:
        for match in _MEANINGFUL_TOKEN_RE.findall(_normalize_string(value)):
            token = match.casefold()
            if token in _TOKEN_STOPWORDS:
                continue
            tokens.add(token)
    return tokens


def label(kind: str, *, markdown: bool) -> str:
    title = {
        "assist": "Odylith Assist",
        "insight": "Odylith Insight",
        "history": "Odylith History",
        "risks": "Odylith Risks",
    }[kind]
    return f"**{title}:**" if markdown else f"{title}:"
