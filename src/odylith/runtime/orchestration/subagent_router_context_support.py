"""Shared context-signal helpers for subagent router assessment and policy code."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from odylith.runtime.common.value_coercion import int_value as _int_value
from odylith.runtime.common.value_coercion import normalize_string as _normalize_string
from odylith.runtime.common.value_coercion import normalize_token as _normalize_token
from odylith.runtime.context_engine import governance_signal_codec
from odylith.runtime.orchestration import subagent_router_runtime_policy

_SCORE_MIN = 0
_SCORE_MAX = 4


def _normalize_list(value: Any) -> list[str]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_normalize_string(item) for item in value if _normalize_string(item)]
    token = _normalize_string(value)
    return [token] if token else []


def _count_or_list_len(payload: Mapping[str, Any], *, list_key: str, count_key: str) -> int:
    value = _mapping_value(payload, list_key)
    return max(
        len(value) if isinstance(value, list) else len(_normalize_list(value)),
        _int_value(_mapping_value(payload, count_key)),
    )


def _normalize_context_signals(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    return {_normalize_string(key): raw for key, raw in value.items() if _normalize_string(key)}


def _embedded_governance_signal(context_packet: Mapping[str, Any]) -> dict[str, Any]:
    route = _mapping_value(context_packet, "route")
    if not isinstance(route, Mapping):
        return {}
    governance = _mapping_value(route, "governance")
    if not isinstance(governance, Mapping):
        return {}
    return {
        _normalize_string(key): raw
        for key, raw in governance_signal_codec.expand_governance_signal(governance).items()
        if _normalize_string(key) and raw not in ("", [], {}, None, False)
    }


def _validation_bundle_from_context(
    context_signals: Mapping[str, Any],
    *,
    context_packet: Mapping[str, Any],
) -> dict[str, Any]:
    validation_bundle = _mapping_value(context_signals, "validation_bundle")
    if isinstance(validation_bundle, Mapping):
        return dict(validation_bundle)
    governance = _embedded_governance_signal(context_packet)
    compact: dict[str, Any] = {}
    for key in (
        "recommended_command_count",
        "strict_gate_command_count",
        "plan_binding_required",
        "governed_surface_sync_required",
    ):
        value = _mapping_value(governance, key)
        if value not in ("", [], {}, None, False):
            compact[key] = value
    return compact


def _governance_obligations_from_context(
    context_signals: Mapping[str, Any],
    *,
    context_packet: Mapping[str, Any],
) -> dict[str, Any]:
    governance_obligations = _mapping_value(context_signals, "governance_obligations")
    if isinstance(governance_obligations, Mapping):
        return dict(governance_obligations)
    governance = _embedded_governance_signal(context_packet)
    compact: dict[str, Any] = {}
    for key in (
        "touched_workstream_count",
        "primary_workstream_id",
        "touched_component_count",
        "primary_component_id",
        "required_diagram_count",
        "linked_bug_count",
        "closeout_doc_count",
        "workstream_state_action_count",
    ):
        value = _mapping_value(governance, key)
        if value not in ("", [], {}, None, False):
            compact[key] = value
    return compact


def _surface_refs_from_context(
    context_signals: Mapping[str, Any],
    *,
    context_packet: Mapping[str, Any],
) -> dict[str, Any]:
    surface_refs = _mapping_value(context_signals, "surface_refs")
    if isinstance(surface_refs, Mapping):
        return dict(surface_refs)
    governance = _embedded_governance_signal(context_packet)
    compact: dict[str, Any] = {}
    for key in ("surface_count", "reason_group_count"):
        value = _mapping_value(governance, key)
        if value not in ("", [], {}, None, False):
            compact[key] = value
    return compact


def _mapping_value(payload: Mapping[str, Any], key: str) -> Any:
    wanted = _normalize_token(key)
    for raw_key, raw_value in payload.items():
        if _normalize_token(raw_key) == wanted:
            return raw_value
    alias = {
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
    }.get(wanted, "")
    if alias:
        for raw_key, raw_value in payload.items():
            if _normalize_token(raw_key) == alias:
                return raw_value
    return None


def _context_signal_root(context_signals: Mapping[str, Any]) -> Mapping[str, Any]:
    nested = _mapping_value(context_signals, "routing_handoff")
    return nested if isinstance(nested, Mapping) else context_signals


def _context_lookup(payload: Mapping[str, Any], *path: str) -> Any:
    current: Any = payload
    for key in path:
        if not isinstance(current, Mapping):
            return None
        current = _mapping_value(current, key)
    return current


def _context_signal_score(value: Any) -> int:
    if isinstance(value, bool):
        return _SCORE_MAX if value else _SCORE_MIN
    if isinstance(value, (int, float)):
        return _clamp_score(value)
    if isinstance(value, Mapping):
        for key in ("score", "level", "confidence", "rating", "value"):
            nested = _mapping_value(value, key)
            if nested is not None:
                return _context_signal_score(nested)
        return _SCORE_MIN
    token = _normalize_token(value)
    if token in {"none", "unknown", "false", "unready", "blocked"}:
        return 0
    if token in {"low", "weak", "light", "minimal"}:
        return 1
    if token in {"medium", "moderate", "partial"}:
        return 2
    if token in {"high", "strong", "grounded", "actionable", "ready"}:
        return 3
    if token in {"very_high", "max", "maximum", "full"}:
        return 4
    return 0


def _dedupe_strings(values: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    rows: list[str] = []
    for value in values:
        token = str(value or "").strip()
        if not token or token in seen:
            continue
        seen.add(token)
        rows.append(token)
    return rows


def _context_signal_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return float(value) > 0
    if isinstance(value, Mapping):
        for key in ("enabled", "ready", "supported", "allowed", "active", "value"):
            nested = _mapping_value(value, key)
            if nested is not None:
                return _context_signal_bool(nested)
    token = _normalize_token(value)
    return token in {"1", "true", "yes", "y", "on", "ready", "supported", "primary", "support"}


def _context_signal_level(score: int) -> str:
    value = _clamp_score(score)
    if value >= 4:
        return "high"
    if value >= 2:
        return "medium"
    if value >= 1:
        return "low"
    return "none"


def _scaled_numeric_signal(value: Any) -> int:
    if isinstance(value, (int, float)):
        numeric = float(value)
        if 0.0 <= numeric <= 1.0:
            return _clamp_score(round(numeric * _SCORE_MAX))
        if numeric > _SCORE_MAX:
            return _clamp_score(round(numeric / 25.0))
        return _clamp_score(numeric)
    return _context_signal_score(value)


def _normalized_rate(value: Any) -> float:
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    try:
        numeric = float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0
    if numeric > 1.0:
        numeric = numeric / 100.0 if numeric <= 100.0 else 1.0
    return max(0.0, min(1.0, numeric))


def _latency_pressure_signal(value: Any) -> int:
    try:
        numeric = float(value or 0.0)
    except (TypeError, ValueError):
        return 0
    if numeric >= 12000.0:
        return 4
    if numeric >= 6000.0:
        return 3
    if numeric >= 2500.0:
        return 2
    if numeric >= 1000.0:
        return 1
    return 0


def _execution_profile_mapping(
    *,
    root: Mapping[str, Any],
    context_packet: Mapping[str, Any],
    evidence_pack: Mapping[str, Any],
    optimization_snapshot: Mapping[str, Any],
) -> dict[str, Any]:
    return subagent_router_runtime_policy._execution_profile_mapping(
        root=root,
        context_packet=context_packet,
        evidence_pack=evidence_pack,
        optimization_snapshot=optimization_snapshot,
    )


def _preferred_router_profile_from_execution_profile(profile: Mapping[str, Any]) -> Any | None:
    return subagent_router_runtime_policy._preferred_router_profile_from_execution_profile(profile=profile)


def _clamp_score(value: int | float) -> int:
    return max(_SCORE_MIN, min(_SCORE_MAX, int(round(float(value)))))
