from __future__ import annotations

from typing import Any, Mapping

_CANONICAL_TO_COMPACT = {
    "routing_confidence": "rc",
    "intent_family": "i",
    "intent_mode": "m",
    "intent_critical_path": "cp",
    "intent_confidence": "ic",
    "intent_explicit": "ix",
    "reasoning_bias": "rb",
    "parallelism_hint": "ph",
    "context_richness": "cr",
    "accuracy_posture": "ap",
    "utility_score": "us",
    "context_density_level": "cd",
    "reasoning_readiness_level": "rr",
}
_COMPACT_TO_CANONICAL = {value: key for key, value in _CANONICAL_TO_COMPACT.items()}


def expand_packet_quality(packet_quality: Mapping[str, Any] | None) -> dict[str, Any]:
    if not isinstance(packet_quality, Mapping):
        return {}
    expanded: dict[str, Any] = {}
    for raw_key, raw_value in packet_quality.items():
        key = _COMPACT_TO_CANONICAL.get(str(raw_key).strip(), str(raw_key).strip())
        if not key or raw_value in ("", [], {}, None, False):
            continue
        expanded[key] = raw_value
    return expanded


def compact_packet_quality(packet_quality: Mapping[str, Any] | None) -> dict[str, Any]:
    if not isinstance(packet_quality, Mapping):
        return {}
    compact: dict[str, Any] = {}
    for raw_key, raw_value in expand_packet_quality(packet_quality).items():
        key = _CANONICAL_TO_COMPACT.get(str(raw_key).strip(), str(raw_key).strip())
        if not key or raw_value in ("", [], {}, None, False):
            continue
        compact[key] = raw_value
    return compact


def packet_quality_value(packet_quality: Mapping[str, Any] | None, key: str, default: Any = None) -> Any:
    expanded = expand_packet_quality(packet_quality)
    token = str(key or "").strip()
    return expanded.get(token, default) if token else default


__all__ = [
    "compact_packet_quality",
    "expand_packet_quality",
    "packet_quality_value",
]
