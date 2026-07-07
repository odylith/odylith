"""Domain-neutral shape checks for generated greenfield prose."""

from __future__ import annotations

from functools import lru_cache
import re

from collections.abc import Collection

from odylith.runtime.common.prose_grammar import base_gerund_clause
from odylith.runtime.common.prose_grammar import looks_like_finite_action
from odylith.runtime.domain_intelligence.greenfield_actor_led_prefix import looks_like_actor_led_subject_prefix
from odylith.runtime.domain_intelligence.greenfield_actor_roles import ACTOR_ROLE_NOUNS


def actor_led_finite_action_inside_user_can(value: str) -> bool:
    """Return whether a modal user-capability clause swallowed an actor subject."""

    for tokens in _token_segments(value):
        lowered = [token.casefold() for token in tokens]
        for index in range(0, max(0, len(tokens) - 2)):
            if lowered[index] not in {"user", "users"} or lowered[index + 1] != "can":
                continue
            tail = _modal_action_tail(tokens[index + 2 : min(len(tokens), index + 10)])
            if _contains_actor_led_finite_action(tail):
                return True
    return False


def _modal_action_tail(tokens: list[str]) -> list[str]:
    for index, token in enumerate(tokens):
        if index > 0 and token.casefold() in {"before", "until", "when", "while", "without"}:
            return tokens[:index]
    return tokens


def gerund_actor_role_finite_action_splice(value: str, *, actor_labels: Collection[str] = ()) -> bool:
    """Return whether a gerundized action word leaked into an actor-role subject."""

    text = str(value or "")
    allowed_actor_labels = tuple(sorted({_actor_label_key(label) for label in actor_labels if _actor_label_key(label)}))
    return _gerund_actor_role_finite_action_splice_cached(text, allowed_actor_labels)


@lru_cache(maxsize=16384)
def _gerund_actor_role_finite_action_splice_cached(value: str, allowed_actor_labels: tuple[str, ...]) -> bool:
    allowed_actor_label_set = set(allowed_actor_labels)
    for tokens in _token_segments(value):
        for index in range(0, max(0, len(tokens) - 2)):
            window = tokens[index : min(len(tokens), index + 10)]
            for split_index in range(1, min(len(window), 6)):
                prefix = " ".join(window[:split_index]).strip(" .")
                normalized_prefix = base_gerund_clause(prefix).strip(" .")
                if not normalized_prefix or normalized_prefix.casefold() == prefix.casefold():
                    continue
                if _is_source_owned_actor_label(prefix, allowed_actor_label_set) or _is_source_owned_actor_label_prefix(
                    window,
                    split_index=split_index,
                    allowed_actor_labels=allowed_actor_label_set,
                ) or _is_source_owned_actor_label_suffix(prefix, allowed_actor_label_set):
                    continue
                if _looks_like_title_compound_actor(prefix, normalized_prefix):
                    continue
                if not _has_actor_role_head(normalized_prefix):
                    continue
                candidate = " ".join(window[split_index:]).strip(" .")
                if _candidate_starts_with_stative_ownership(candidate):
                    continue
                full_text = " ".join([normalized_prefix, candidate]).strip(" .")
                if looks_like_actor_led_subject_prefix(normalized_prefix, full_text) and looks_like_finite_action(candidate):
                    return True
    return False


def _contains_actor_led_finite_action(tokens: list[str]) -> bool:
    tail_text = " ".join(tokens)
    for split_index in range(1, min(len(tokens), 6)):
        prefix = " ".join(tokens[:split_index]).strip(" .")
        candidate = " ".join(tokens[split_index:]).strip(" .")
        if looks_like_actor_led_subject_prefix(prefix, tail_text) and looks_like_finite_action(candidate):
            return True
    return False


def _word_tokens(value: str) -> list[str]:
    return [match.group(0) for match in re.finditer(r"[A-Za-z][A-Za-z0-9'-]*", str(value or ""))]


def _actor_label_key(value: str) -> str:
    return " ".join(token.casefold() for token in _word_tokens(value))


def _is_source_owned_actor_label(prefix: str, allowed_actor_labels: set[str]) -> bool:
    return bool(allowed_actor_labels and _actor_label_key(prefix) in allowed_actor_labels)


def _is_source_owned_actor_label_prefix(
    window: list[str],
    *,
    split_index: int,
    allowed_actor_labels: set[str],
) -> bool:
    if not allowed_actor_labels:
        return False
    prefix_key = _actor_label_key(" ".join(window[:split_index]))
    if not prefix_key:
        return False
    for label_key in allowed_actor_labels:
        label_tokens = label_key.split()
        if len(label_tokens) <= split_index or len(label_tokens) > len(window):
            continue
        window_key = _actor_label_key(" ".join(window[: len(label_tokens)]))
        if window_key == label_key and label_key.startswith(prefix_key + " "):
            return True
    return False


def _is_source_owned_actor_label_suffix(prefix: str, allowed_actor_labels: set[str]) -> bool:
    prefix_key = _actor_label_key(prefix)
    return bool(prefix_key and any(label_key.endswith(" " + prefix_key) for label_key in allowed_actor_labels))


def _token_segments(value: str) -> list[list[str]]:
    return [tokens for part in re.split(r"[.!?;:,]+", str(value or "")) if (tokens := _word_tokens(part))]


def _has_actor_role_head(value: str) -> bool:
    tokens = [token.casefold() for token in _word_tokens(value)]
    return bool(tokens and tokens[-1] in ACTOR_ROLE_NOUNS)


def _looks_like_title_compound_actor(prefix: str, normalized_prefix: str) -> bool:
    """Distinguish product-title compounds from direct gerund-role splices."""

    original = _word_tokens(prefix)
    normalized = _word_tokens(normalized_prefix)
    if len(original) != len(normalized) or len(original) < 3:
        return False
    changed = [
        index
        for index, (raw, repaired) in enumerate(zip(original, normalized))
        if raw.casefold() != repaired.casefold()
    ]
    if changed != [0]:
        return False
    return normalized[-1].casefold() in {"user", "users"} and len(normalized) >= 3


def _candidate_starts_with_stative_ownership(value: str) -> bool:
    first = (_word_tokens(value) or [""])[0].casefold()
    return first in {"are", "has", "have", "is", "need", "needs"}


__all__ = [
    "actor_led_finite_action_inside_user_can",
    "gerund_actor_role_finite_action_splice",
]
