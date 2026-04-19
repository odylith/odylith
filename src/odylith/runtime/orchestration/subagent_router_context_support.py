"""Shared context-signal helpers for subagent router assessment and policy code."""

from __future__ import annotations

import re
from typing import Any, Mapping, Sequence

from odylith.runtime.common.value_coercion import int_value as _int_value
from odylith.runtime.common.value_coercion import normalize_string as _normalize_string
from odylith.runtime.common.value_coercion import normalize_token as _normalize_token
from odylith.runtime.common import agent_runtime_contract
from odylith.runtime.common import host_runtime as host_runtime_contract
from odylith.runtime.common.value_coercion import bool_value as _normalize_bool
from odylith.runtime.context_engine import governance_signal_codec
from odylith.runtime.context_engine import packet_quality_codec
from odylith.runtime.memory import tooling_memory_contracts
from odylith.runtime.orchestration import subagent_router_profile_support

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
    latest_packet = _mapping_value(optimization_snapshot, "latest_packet")
    optimization_latest_profile = {
        key: value
        for key, value in {
            "profile": str(_context_lookup(latest_packet, "odylith_execution_profile") or "").strip(),
            "model": str(_context_lookup(latest_packet, "odylith_execution_model") or "").strip(),
            "reasoning_effort": str(_context_lookup(latest_packet, "odylith_execution_reasoning_effort") or "").strip(),
            "agent_role": str(_context_lookup(latest_packet, "odylith_execution_agent_role") or "").strip(),
            "selection_mode": str(_context_lookup(latest_packet, "odylith_execution_selection_mode") or "").strip(),
            "delegate_preference": str(_context_lookup(latest_packet, "odylith_execution_delegate_preference") or "").strip(),
            "source": (
                str(_context_lookup(latest_packet, "odylith_execution_source") or "optimization_snapshot_latest_packet").strip()
                if latest_packet
                else ""
            ),
            "confidence": {
                "score": int(_context_lookup(latest_packet, "odylith_execution_confidence_score") or 0),
                "level": str(_context_lookup(latest_packet, "odylith_execution_confidence_level") or "").strip(),
            },
            "constraints": {
                "route_ready": _context_signal_bool(_context_lookup(latest_packet, "odylith_execution_route_ready")),
                "narrowing_required": _context_signal_bool(
                    _context_lookup(latest_packet, "odylith_execution_narrowing_required")
                ),
                "spawn_worthiness": int(_context_lookup(latest_packet, "odylith_execution_spawn_worthiness") or 0),
                "merge_burden": int(_context_lookup(latest_packet, "odylith_execution_merge_burden") or 0),
                "reasoning_mode": str(_context_lookup(latest_packet, "odylith_execution_reasoning_mode") or "").strip(),
            }
            if latest_packet
            else {},
        }.items()
        if (
            value not in ("", [], {}, None)
            and (
                key not in {"confidence", "constraints"}
                or (
                    key == "confidence"
                    and (int(value.get("score", 0) or 0) > 0 or str(value.get("level", "")).strip())
                )
                or (
                    key == "constraints"
                    and any(subvalue not in ("", [], {}, None, 0, False) for subvalue in value.values())
                )
            )
        )
    }
    candidates = (
        _execution_profile_candidate(root.get("odylith_execution_profile")),
        _execution_profile_candidate(root.get("execution_profile")),
        _execution_profile_candidate(context_packet.get("execution_profile")),
        _execution_profile_candidate(_context_lookup(evidence_pack, "routing_handoff", "odylith_execution_profile")),
        _execution_profile_candidate(_context_lookup(evidence_pack, "routing_handoff", "execution_profile")),
        _execution_profile_candidate(optimization_snapshot.get("execution_profile")),
        _execution_profile_candidate(_context_lookup(optimization_snapshot, "latest_packet", "odylith_execution_profile")),
        optimization_latest_profile,
    )
    scored_candidates: list[tuple[int, int, dict[str, Any]]] = []
    for index, candidate in enumerate(candidates):
        if not candidate:
            continue
        confidence = dict(candidate.get("confidence", {})) if isinstance(candidate.get("confidence"), Mapping) else {}
        constraints = dict(candidate.get("constraints", {})) if isinstance(candidate.get("constraints"), Mapping) else {}
        richness = sum(
            1
            for key in ("profile", "model", "reasoning_effort", "agent_role", "selection_mode", "delegate_preference", "source")
            if str(candidate.get(key, "")).strip()
        )
        if confidence:
            richness += sum(
                1 for key in ("score", "level") if str(confidence.get(key, "")).strip() or int(confidence.get(key, 0) or 0) > 0
            )
        if constraints:
            richness += sum(1 for value in constraints.values() if value not in ("", [], {}, None, False))
        scored_candidates.append((richness, index, candidate))
    if not scored_candidates:
        return _synthesized_execution_profile_candidate(context_packet=context_packet)
    merged: dict[str, Any] = {}
    for _, _, candidate in sorted(scored_candidates, key=lambda item: (item[0], item[1])):
        for key, value in candidate.items():
            if value in ("", [], {}, None, False):
                continue
            if isinstance(value, Mapping):
                existing = dict(merged.get(key, {})) if isinstance(merged.get(key), Mapping) else {}
                merged[key] = {
                    **existing,
                    **{subkey: subvalue for subkey, subvalue in value.items() if subvalue not in ("", [], {}, None, False)},
                }
                continue
            merged[key] = value
    host_runtime = host_runtime_contract.resolve_host_runtime(
        _context_lookup(root, "host_runtime"),
        _context_lookup(context_packet, "host_runtime"),
        _context_lookup(evidence_pack, "routing_handoff", "host_runtime"),
        _context_lookup(evidence_pack, "routing_handoff", "odylith_execution_host_runtime"),
        _context_lookup(optimization_snapshot, "latest_packet", "host_runtime"),
        _context_lookup(optimization_snapshot, "latest_packet", "odylith_execution_host_runtime"),
        merged.get("host_runtime"),
    )
    profile = subagent_router_profile_support.router_profile_from_token(merged.get("profile"))
    if profile is None:
        profile = subagent_router_profile_support.router_profile_from_runtime(
            merged.get("model"),
            merged.get("reasoning_effort"),
        )
        if profile is not None:
            merged["profile"] = profile.value
    if profile is not None:
        model, reasoning_effort = agent_runtime_contract.execution_profile_runtime_fields(
            profile.value,
            host_runtime=host_runtime,
        )
        merged["model"] = model
        merged["reasoning_effort"] = reasoning_effort or profile.reasoning_effort
    if host_runtime:
        merged["host_runtime"] = host_runtime
    if not str(merged.get("profile", "")).strip():
        synthesized = _synthesized_execution_profile_candidate(context_packet=context_packet)
        if synthesized:
            merged = {**synthesized, **merged}
    return merged


def _preferred_router_profile_from_execution_profile(profile: Mapping[str, Any]) -> Any | None:
    explicit = subagent_router_profile_support.router_profile_from_token(profile.get("profile"))
    if explicit is not None:
        return explicit
    return subagent_router_profile_support.router_profile_from_runtime(
        profile.get("model"),
        profile.get("reasoning_effort"),
    )


def _execution_profile_candidate(value: Any) -> dict[str, Any]:
    return tooling_memory_contracts.execution_profile_mapping(value)


def _selected_counts_mapping(value: Any) -> dict[str, int]:
    if isinstance(value, Mapping):
        return {
            str(key).strip(): _int_value(raw)
            for key, raw in value.items()
            if str(key).strip() and _int_value(raw) > 0
        }
    token = _normalize_token(value)
    if not token:
        return {}
    alias_map = {
        "c": "commands",
        "d": "docs",
        "t": "tests",
        "g": "guidance",
    }
    counts: dict[str, int] = {}
    for alias, raw_count in re.findall(r"([cdtg])(\d+)", token):
        key = alias_map.get(alias, "")
        count = _int_value(raw_count)
        if key and count > 0:
            counts[key] = count
    return counts


def _synthesized_execution_profile_candidate(*, context_packet: Mapping[str, Any]) -> dict[str, Any]:
    route = dict(context_packet.get("route", {})) if isinstance(context_packet.get("route"), Mapping) else {}
    if not bool(route.get("route_ready")) or bool(route.get("narrowing_required")):
        return {}
    packet_quality = packet_quality_codec.expand_packet_quality(
        dict(context_packet.get("packet_quality", {}))
        if isinstance(context_packet.get("packet_quality"), Mapping)
        else {}
    )
    retrieval_plan = (
        dict(context_packet.get("retrieval_plan", {}))
        if isinstance(context_packet.get("retrieval_plan"), Mapping)
        else {}
    )
    selected_counts = _selected_counts_mapping(retrieval_plan.get("selected_counts"))
    governance = governance_signal_codec.expand_governance_signal(
        dict(route.get("governance", {})) if isinstance(route.get("governance"), Mapping) else {}
    )
    family = _normalize_token(packet_quality.get("intent_family"))
    confidence = _normalize_token(packet_quality.get("routing_confidence"))
    validation_count = _int_value(selected_counts.get("tests")) + _int_value(selected_counts.get("commands"))
    guidance_count = _int_value(selected_counts.get("guidance"))
    governance_contract = any(
        (
            _int_value(governance.get("closeout_doc_count")) > 0,
            _int_value(governance.get("strict_gate_command_count")) > 0,
            _normalize_bool(governance.get("plan_binding_required")),
            _normalize_bool(governance.get("governed_surface_sync_required")),
        )
    )
    host_runtime = host_runtime_contract.resolve_host_runtime(
        context_packet.get("host_runtime"),
        _context_lookup(context_packet, "execution_profile", "host_runtime"),
    )
    profile = subagent_router_profile_support.RouterProfile.ANALYSIS_MEDIUM.value
    agent_role = "explorer"
    selection_mode = "analysis_scout"
    if family in {"implementation", "write", "bugfix"}:
        if governance_contract and _int_value(governance.get("strict_gate_command_count")) > 0:
            profile = subagent_router_profile_support.RouterProfile.FRONTIER_HIGH.value
            selection_mode = "deep_validation"
        else:
            profile = (
                subagent_router_profile_support.RouterProfile.WRITE_HIGH.value
                if confidence == "high" and (validation_count > 0 or guidance_count >= 2)
                else subagent_router_profile_support.RouterProfile.WRITE_MEDIUM.value
            )
            selection_mode = "bounded_write"
        agent_role = "worker"
    elif family == "validation":
        profile = (
            subagent_router_profile_support.RouterProfile.WRITE_HIGH.value
            if confidence == "high" or validation_count >= 2
            else subagent_router_profile_support.RouterProfile.WRITE_MEDIUM.value
        )
        agent_role = "worker"
        selection_mode = "validation_focused"
    elif family in {"docs", "governance"}:
        profile = (
            subagent_router_profile_support.RouterProfile.FAST_WORKER.value
            if governance_contract
            else subagent_router_profile_support.RouterProfile.ANALYSIS_MEDIUM.value
        )
        agent_role = "worker" if profile == subagent_router_profile_support.RouterProfile.FAST_WORKER.value else "explorer"
        selection_mode = "support_fast_lane" if profile == subagent_router_profile_support.RouterProfile.FAST_WORKER.value else "analysis_scout"
    elif family in {"analysis", "review", "diagnosis"}:
        profile = (
            subagent_router_profile_support.RouterProfile.ANALYSIS_HIGH.value
            if confidence == "high" or governance_contract or validation_count > 0 or guidance_count > 0
            else subagent_router_profile_support.RouterProfile.ANALYSIS_MEDIUM.value
        )
        agent_role = "explorer"
        selection_mode = (
            "analysis_synthesis"
            if profile == subagent_router_profile_support.RouterProfile.ANALYSIS_HIGH.value
            else "analysis_scout"
        )
    model, reasoning_effort = agent_runtime_contract.execution_profile_runtime_fields(
        profile,
        host_runtime=host_runtime,
    )
    return {
        "profile": profile,
        "model": model,
        "reasoning_effort": reasoning_effort,
        "agent_role": agent_role,
        "selection_mode": selection_mode,
        "delegate_preference": "delegate",
        "source": "context_packet_route",
        "host_runtime": host_runtime,
    }


def _clamp_score(value: int | float) -> int:
    return max(_SCORE_MIN, min(_SCORE_MAX, int(round(float(value)))))
