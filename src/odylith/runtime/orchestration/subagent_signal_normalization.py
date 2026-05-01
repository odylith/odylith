"""Shared normalization helpers for subagent routing and orchestration signals."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Mapping

from odylith.runtime.common.value_coercion import float_value
from odylith.runtime.common.value_coercion import int_value
from odylith.runtime.common.value_coercion import normalize_string
from odylith.runtime.common.value_coercion import normalize_token

_COMPACT_SIGNAL_ALIASES: dict[str, str] = {
    "parallelism_hint": "p",
    "reasoning_bias": "b",
    "routing_confidence": "rc",
    "intent_family": "i",
    "intent_mode": "m",
    "intent_critical_path": "cp",
    "intent_confidence": "ic",
    "intent_explicit": "ix",
    "context_richness": "cr",
    "accuracy_posture": "ap",
    "utility_score": "us",
    "context_density_level": "cd",
    "reasoning_readiness_level": "rr",
}

__all__ = (
    "context_lookup",
    "count_or_list_len",
    "mapping_value",
    "nested_mapping",
    "normalize_context_signals",
    "normalize_list",
    "normalized_rate",
)


def normalize_list(value: Any) -> list[str]:
    """Normalize scalar-or-sequence signal inputs into a cleaned string list."""

    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        normalized: list[str] = []
        for item in value:
            token = normalize_string(item)
            if token:
                normalized.append(token)
        return normalized
    token = normalize_string(value)
    return [token] if token else []


def normalize_context_signals(value: Any) -> dict[str, Any]:
    """Normalize context-signal mappings to stable string keys without dropping values."""

    if not isinstance(value, Mapping):
        return {}
    normalized: dict[str, Any] = {}
    for key, raw in value.items():
        token = normalize_string(key)
        if token:
            normalized[token] = raw
    return normalized


def mapping_value(payload: Mapping[str, Any], key: str) -> Any:
    """Read a mapping key with support for compact packet-quality aliases."""

    wanted = normalize_token(key)
    for raw_key, raw_value in payload.items():
        if normalize_token(raw_key) == wanted:
            return raw_value
    alias = _COMPACT_SIGNAL_ALIASES.get(wanted, "")
    if alias:
        for raw_key, raw_value in payload.items():
            if normalize_token(raw_key) == alias:
                return raw_value
    return None


def nested_mapping(payload: Mapping[str, Any], *path: str) -> dict[str, Any]:
    """Traverse nested mappings using alias-aware lookup at each step."""

    current: Any = payload
    for key in path:
        if not isinstance(current, Mapping):
            return {}
        current = mapping_value(current, key)
    return dict(current) if isinstance(current, Mapping) else {}


def context_lookup(payload: Mapping[str, Any], *path: str) -> Any:
    """Traverse a normalized path through nested signal mappings."""

    current: Any = payload
    for key in path:
        if not isinstance(current, Mapping):
            return None
        current = mapping_value(current, key)
    return current


def normalized_rate(value: Any) -> float:
    """Normalize a ratio or percentage-like value onto the inclusive 0.0-1.0 range."""

    if isinstance(value, bool):
        return 1.0 if value else 0.0
    numeric = float_value(value)
    if numeric > 1.0:
        numeric = numeric / 100.0 if numeric <= 100.0 else 1.0
    return max(0.0, min(1.0, numeric))


def count_or_list_len(payload: Mapping[str, Any], *, list_key: str, count_key: str) -> int:
    """Prefer explicit counts but fall back to the length of a list-shaped field."""

    value = mapping_value(payload, list_key)
    return max(
        len(value) if isinstance(value, list) else len(normalize_list(value)),
        int_value(mapping_value(payload, count_key)),
    )
