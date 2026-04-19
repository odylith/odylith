"""Execution Engine summary normalization for the subagent router."""

from __future__ import annotations

from typing import Any
from typing import Mapping

from odylith.runtime.common.value_coercion import bool_value
from odylith.runtime.common.value_coercion import int_value
from odylith.runtime.common.value_coercion import normalize_string
from odylith.runtime.common.value_coercion import normalize_string_list
from odylith.runtime.common.value_coercion import normalize_token
from odylith.runtime.context_engine import execution_engine_handshake
from odylith.runtime.execution_engine import runtime_surface_governance


def execution_engine_summary_from_context_sources(
    *,
    context_signals: Mapping[str, Any],
    root: Mapping[str, Any],
    context_packet: Mapping[str, Any],
    execution_engine_payload: Mapping[str, Any],
) -> dict[str, Any]:
    """Return router-ready summary fields from a Context-to-Execution snapshot."""

    if not execution_engine_payload:
        return {}
    execution_payload = dict(root) if isinstance(root, Mapping) else dict(context_signals)
    execution_payload["execution_engine"] = dict(execution_engine_payload)
    if context_packet:
        execution_payload.setdefault("context_packet", dict(context_packet))
    compact = execution_engine_handshake.compact_execution_engine_snapshot_for_packet(
        payload=execution_payload,
        context_packet=context_packet,
    )
    return runtime_surface_governance.summary_fields_from_execution_engine(compact)


def _context_lookup(payload: Mapping[str, Any], *path: str) -> Any:
    current: Any = payload
    for key in path:
        if not isinstance(current, Mapping):
            return None
        current = current.get(key)
    return current


def _preferred_value(summary: Mapping[str, Any], key: str, *fallbacks: Any) -> Any:
    if key in summary:
        return summary.get(key)
    for fallback in fallbacks:
        if fallback not in ("", [], {}, None):
            return fallback
    return None


def _summary_signal_value(
    *,
    execution_engine_summary: Mapping[str, Any],
    root: Mapping[str, Any],
    context_signals: Mapping[str, Any],
    key: str,
) -> Any:
    return _preferred_value(
        execution_engine_summary,
        key,
        _context_lookup(root, key),
        _context_lookup(context_signals, key),
        _context_lookup(context_signals, f"latest_{key}"),
    )


def router_execution_engine_fields(
    *,
    context_signals: Mapping[str, Any],
    root: Mapping[str, Any],
    execution_engine_summary: Mapping[str, Any],
) -> dict[str, Any]:
    """Resolve router-facing execution-engine fields with stable fallback order."""

    def signal(key: str) -> Any:
        return _summary_signal_value(
            execution_engine_summary=execution_engine_summary,
            root=root,
            context_signals=context_signals,
            key=key,
        )

    return {
        "execution_engine_present": bool_value(signal("execution_engine_present"), default=False),
        "execution_engine_outcome": normalize_token(signal("execution_engine_outcome")),
        "execution_engine_requires_reanchor": bool_value(
            signal("execution_engine_requires_reanchor"),
            default=False,
        ),
        "execution_engine_mode": normalize_token(signal("execution_engine_mode")),
        "execution_engine_next_move": normalize_string(signal("execution_engine_next_move")),
        "execution_engine_current_phase": normalize_string(signal("execution_engine_current_phase")),
        "execution_engine_last_successful_phase": normalize_string(
            signal("execution_engine_last_successful_phase")
        ),
        "execution_engine_blocker": normalize_string(signal("execution_engine_blocker")),
        "execution_engine_closure": normalize_token(signal("execution_engine_closure")),
        "execution_engine_wait_status": normalize_token(signal("execution_engine_wait_status")),
        "execution_engine_wait_detail": normalize_string(signal("execution_engine_wait_detail")),
        "execution_engine_resume_token": normalize_string(signal("execution_engine_resume_token")),
        "execution_engine_validation_archetype": normalize_token(
            signal("execution_engine_validation_archetype")
        ),
        "execution_engine_validation_minimum_pass_count": int_value(
            signal("execution_engine_validation_minimum_pass_count")
        ),
        "execution_engine_contradiction_count": int_value(
            signal("execution_engine_contradiction_count")
        ),
        "execution_engine_history_rule_count": int_value(
            signal("execution_engine_history_rule_count")
        ),
        "execution_engine_event_count": int_value(signal("execution_engine_event_count")),
        "execution_engine_authoritative_lane": normalize_string(
            signal("execution_engine_authoritative_lane")
        ),
        "execution_engine_host_family": normalize_token(signal("execution_engine_host_family")),
        "execution_engine_model_family": normalize_token(signal("execution_engine_model_family")),
        "execution_engine_host_supports_native_spawn": bool_value(
            signal("execution_engine_host_supports_native_spawn"),
            default=False,
        ),
        "execution_engine_component_id": normalize_string(signal("execution_engine_component_id")),
        "execution_engine_canonical_component_id": normalize_string(
            signal("execution_engine_canonical_component_id")
        ),
        "execution_engine_identity_status": normalize_token(
            signal("execution_engine_identity_status")
        ),
        "execution_engine_target_component_id": normalize_string(
            signal("execution_engine_target_component_id")
        ),
        "execution_engine_target_component_ids": normalize_string_list(
            signal("execution_engine_target_component_ids"),
            limit=4,
        ),
        "execution_engine_target_component_status": normalize_token(
            signal("execution_engine_target_component_status")
        ),
        "execution_engine_snapshot_reuse_status": normalize_token(
            signal("execution_engine_snapshot_reuse_status")
        ),
        "execution_engine_target_lane": normalize_token(signal("execution_engine_target_lane")),
        "execution_engine_has_writable_targets": bool_value(
            signal("execution_engine_has_writable_targets"),
            default=False,
        ),
        "execution_engine_requires_more_consumer_context": bool_value(
            signal("execution_engine_requires_more_consumer_context"),
            default=False,
        ),
        "execution_engine_consumer_failover": normalize_string(
            signal("execution_engine_consumer_failover")
        ),
        "execution_engine_commentary_mode": normalize_token(
            signal("execution_engine_commentary_mode")
        ),
        "execution_engine_suppress_routing_receipts": bool_value(
            signal("execution_engine_suppress_routing_receipts"),
            default=False,
        ),
        "execution_engine_surface_fast_lane": bool_value(
            signal("execution_engine_surface_fast_lane"),
            default=False,
        ),
        "execution_engine_validation_derived_from": normalize_string_list(
            signal("execution_engine_validation_derived_from"),
            limit=4,
        ),
        "execution_engine_history_rule_hits": normalize_string_list(
            signal("execution_engine_history_rule_hits"),
            limit=4,
        ),
        "execution_engine_pressure_signals": normalize_string_list(
            signal("execution_engine_pressure_signals"),
            limit=4,
        ),
        "execution_engine_nearby_denial_actions": normalize_string_list(
            signal("execution_engine_nearby_denial_actions"),
            limit=4,
        ),
        "execution_engine_runtime_invalidated_by_step": normalize_string(
            signal("execution_engine_runtime_invalidated_by_step")
        ),
    }


__all__ = [
    "execution_engine_summary_from_context_sources",
    "router_execution_engine_fields",
]
