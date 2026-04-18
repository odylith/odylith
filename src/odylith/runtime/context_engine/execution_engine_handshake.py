"""Execution Engine Handshake helpers for the Odylith context engine layer."""

from __future__ import annotations

import json
import time
from typing import Any
from typing import Mapping
from typing import Sequence

from odylith.runtime.context_engine import packet_quality_codec
from odylith.runtime.execution_engine import runtime_surface_governance
from odylith.runtime.character import runtime as character_runtime
from odylith.runtime.governance import guidance_behavior_runtime


CANONICAL_EXECUTION_ENGINE_COMPONENT_ID = "execution-engine"
HANDSHAKE_VERSION = "v1"
NONCANONICAL_EXECUTION_ENGINE_COMPONENT_IDS = frozenset(
    {
        "execution-governance",
        "execution_governance",
    }
)


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _string(value: Any) -> str:
    return str(value or "").strip()


def _strings(*values: Any) -> list[str]:
    rows: list[str] = []
    seen: set[str] = set()
    for value in values:
        if isinstance(value, str):
            candidates = [value]
        elif isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
            candidates = list(value)
        else:
            candidates = []
        for item in candidates:
            token = _string(item)
            if not token or token in seen:
                continue
            seen.add(token)
            rows.append(token)
    return rows


def _estimate_json_tokens(value: Any) -> int:
    if value in ("", [], {}, None):
        return 0
    try:
        encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    except (TypeError, ValueError):
        encoded = str(value)
    if not encoded:
        return 0
    return max(1, len(encoded.encode("utf-8")) // 4)


def _component_key(value: Any) -> str:
    return _string(value).lower().replace("_", "-")


def _append_component_token(tokens: list[str], value: Any) -> None:
    token = _string(value)
    if token and token not in tokens:
        tokens.append(token)


def _append_component_tokens(tokens: list[str], value: Any) -> None:
    if isinstance(value, str):
        _append_component_token(tokens, value)
        return
    if isinstance(value, Mapping):
        entity_kind = _component_key(
            value.get("kind")
            or value.get("entity_kind")
            or value.get("entity_type")
            or value.get("type")
        )
        if entity_kind in {"component", "registry-component"}:
            for key in ("value", "entity_id", "id", "name"):
                _append_component_token(tokens, value.get(key))
        for key in (
            "component",
            "component_id",
            "canonical_component_id",
            "target_component_id",
            "requested_component",
            "requested_component_id",
            "requested_target_component_id",
            "primary_component_id",
        ):
            _append_component_token(tokens, value.get(key))
        for key in (
            "components",
            "component_ids",
            "target_component_ids",
            "related_component_ids",
            "linked_component_ids",
            "matched_component_ids",
            "touched_component_ids",
        ):
            _append_component_tokens(tokens, value.get(key))
        return
    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
        for item in value:
            _append_component_tokens(tokens, item)


def _append_target_resolution_component_tokens(tokens: list[str], value: Any) -> None:
    resolution = _mapping(value)
    if not resolution:
        return
    _append_component_tokens(tokens, resolution)
    for key in ("candidate_targets", "diagnostic_anchors"):
        _append_component_tokens(tokens, resolution.get(key))


def _append_related_entity_component_tokens(tokens: list[str], value: Any) -> None:
    related_entities = _mapping(value)
    if not related_entities:
        return
    components = related_entities.get("component")
    if isinstance(components, Sequence) and not isinstance(components, (str, bytes, bytearray)):
        for row in components:
            if isinstance(row, Mapping):
                _append_component_token(tokens, row.get("component_id") or row.get("entity_id"))
            else:
                _append_component_token(tokens, row)
        return
    _append_component_tokens(tokens, components)


def _component_ids(
    payload: Mapping[str, Any],
    context_packet: Mapping[str, Any],
    routing_handoff: Mapping[str, Any],
) -> list[str]:
    tokens: list[str] = []
    for source in (payload, context_packet, routing_handoff):
        _append_component_tokens(tokens, source)
        _append_component_tokens(tokens, source.get("execution_engine"))
        _append_target_resolution_component_tokens(tokens, source.get("target_resolution"))
        _append_related_entity_component_tokens(tokens, source.get("related_entities"))
    return tokens


def _target_component_status(component_ids: Sequence[str]) -> str:
    keys = {_component_key(token) for token in component_ids if _string(token)}
    if not keys:
        return "missing"
    if keys.intersection(NONCANONICAL_EXECUTION_ENGINE_COMPONENT_IDS):
        return "blocked_noncanonical_execution_engine"
    if CANONICAL_EXECUTION_ENGINE_COMPONENT_ID in keys:
        return "execution_engine" if len(keys) == 1 else "execution_engine_plus_related"
    return "other_component"


def _noncanonical_targets_first(component_ids: Sequence[str]) -> list[str]:
    targets = [token for token in component_ids if _string(token)]
    noncanonical_targets = [
        token
        for token in targets
        if _component_key(token) in NONCANONICAL_EXECUTION_ENGINE_COMPONENT_IDS
    ]
    if not noncanonical_targets:
        return targets
    return [
        *noncanonical_targets,
        *(token for token in targets if token not in noncanonical_targets),
    ]


def _packet_quality(
    payload: Mapping[str, Any],
    context_packet: Mapping[str, Any],
    routing_handoff: Mapping[str, Any],
) -> dict[str, Any]:
    for source in (
        payload.get("packet_quality"),
        routing_handoff.get("packet_quality"),
        context_packet.get("packet_quality"),
    ):
        if isinstance(source, Mapping) and source:
            return packet_quality_codec.expand_packet_quality(dict(source))
    return {}


def _recommended_validation(payload: Mapping[str, Any], context_packet: Mapping[str, Any]) -> dict[str, Any]:
    validation_bundle = _mapping(payload.get("validation_bundle")) or _mapping(
        context_packet.get("validation_bundle")
    )
    guidance_behavior = guidance_behavior_runtime.summary_from_sources(payload, context_packet, limit=6)
    guidance_behavior_command = _string(guidance_behavior.get("validator_command"))
    character_summary = character_runtime.summary_from_sources(payload, context_packet, limit=6)
    character_command = _string(character_summary.get("validator_command"))
    recommended_tests = [
        _string(row.get("path"))
        for row in payload.get("recommended_tests", [])
        if isinstance(row, Mapping) and _string(row.get("path"))
    ]
    recommended_commands = _strings(payload.get("recommended_commands"), guidance_behavior_command, character_command)
    strict_gate_commands = _strings(validation_bundle.get("strict_gate_commands"))
    strict_gate_count = int(validation_bundle.get("strict_gate_command_count", 0) or 0)
    if strict_gate_count <= 0:
        strict_gate_count = len(strict_gate_commands)
    return {
        key: value
        for key, value in {
            "recommended_tests": recommended_tests[:4],
            "recommended_commands": recommended_commands[:4],
            "strict_gate_command_count": strict_gate_count,
            "plan_binding_required": bool(validation_bundle.get("plan_binding_required")),
            "governed_surface_sync_required": bool(
                validation_bundle.get("governed_surface_sync_required")
            ),
            "guidance_behavior_status": _string(guidance_behavior.get("status")),
            "guidance_behavior_validation_status": _string(guidance_behavior.get("validation_status")),
            "character_status": _string(character_summary.get("status")),
            "character_validation_status": _string(character_summary.get("validation_status")),
        }.items()
        if value not in ("", [], {}, None, False, 0)
    }


def normalize_execution_engine_handshake(
    *,
    payload: Mapping[str, Any],
    context_packet: Mapping[str, Any] | None = None,
    routing_handoff: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    context = _mapping(context_packet) or _mapping(payload.get("context_packet"))
    handoff = _mapping(routing_handoff) or _mapping(payload.get("routing_handoff"))
    route = _mapping(context.get("route"))
    packet_kind = _string(payload.get("packet_kind")) or _string(context.get("packet_kind")) or "packet"
    packet_state = _string(payload.get("context_packet_state")) or _string(context.get("packet_state"))
    target_component_ids = _component_ids(payload, context, handoff)
    target_component_status = _target_component_status(target_component_ids)
    if target_component_status == "blocked_noncanonical_execution_engine":
        target_component_ids = _noncanonical_targets_first(target_component_ids)
    identity_status = (
        "blocked_noncanonical_target"
        if target_component_status == "blocked_noncanonical_execution_engine"
        else "canonical"
    )
    return {
        "version": HANDSHAKE_VERSION,
        "component_id": CANONICAL_EXECUTION_ENGINE_COMPONENT_ID,
        "canonical_component_id": CANONICAL_EXECUTION_ENGINE_COMPONENT_ID,
        "identity_status": identity_status,
        "target_component_id": target_component_ids[0] if target_component_ids else "",
        "target_component_ids": target_component_ids[:4],
        "target_component_status": target_component_status,
        "packet_kind": packet_kind,
        "packet_state": packet_state,
        "packet_quality": _packet_quality(payload, context, handoff),
        "turn_context": _mapping(payload.get("turn_context")) or _mapping(_mapping(payload.get("session")).get("turn_context")),
        "target_resolution": _mapping(payload.get("target_resolution")),
        "presentation_policy": _mapping(payload.get("presentation_policy")),
        "recommended_validation": _recommended_validation(payload, context),
        "route_readiness": {
            "route_ready": bool(handoff.get("route_ready") or route.get("route_ready")),
            "native_spawn_ready": bool(
                handoff.get("native_spawn_ready") or route.get("native_spawn_ready")
            ),
            "narrowing_required": bool(handoff.get("narrowing_required") or route.get("narrowing_required")),
            "full_scan_recommended": bool(
                payload.get("full_scan_recommended") or context.get("full_scan_recommended")
            ),
        },
    }


def attach_execution_engine_handshake(
    context_packet: Mapping[str, Any],
    *,
    payload: Mapping[str, Any],
    routing_handoff: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    packet = dict(context_packet)
    packet["execution_engine_handshake"] = normalize_execution_engine_handshake(
        payload=payload,
        context_packet=packet,
        routing_handoff=routing_handoff,
    )
    return packet


def _apply_handshake_metadata(compact: Mapping[str, Any], handshake: Mapping[str, Any]) -> dict[str, Any]:
    enriched = dict(compact)
    for key in (
        "component_id",
        "canonical_component_id",
        "identity_status",
        "target_component_id",
        "target_component_ids",
        "target_component_status",
    ):
        value = handshake.get(key)
        if value not in ("", [], {}, (), None):
            if enriched.get(key) in ("", [], {}, (), None):
                enriched[key] = value
            else:
                enriched.setdefault(key, value)
    enriched.setdefault("handshake_version", _string(handshake.get("version")) or HANDSHAKE_VERSION)
    enriched.setdefault("handshake_estimated_tokens", _estimate_json_tokens(handshake))
    return enriched


def _fail_closed_identity_snapshot(handshake: Mapping[str, Any]) -> dict[str, Any]:
    blocker = (
        "noncanonical execution-engine component id is not admissible after the canonical hard cut"
    )
    compact = {
        "present": True,
        "objective": "reject noncanonical execution-engine identity",
        "authoritative_lane": "context_engine.identity.fail_closed",
        "outcome": "deny",
        "rationale": blocker,
        "requires_reanchor": True,
        "mode": "recover",
        "next_move": "re_anchor.execution_engine_identity",
        "current_phase": "recover",
        "last_successful_phase": "re_anchor",
        "blocker": blocker,
        "closure": "incomplete",
        "resume_token": "resume:execution-engine-identity",
        "validation_archetype": "identity",
        "validation_minimum_pass_count": 1,
        "validation_derived_from": ["identity:canonical-component"],
        "event_count": 1,
        "pressure_signals": ["identity:noncanonical_execution_engine"],
        "nearby_denial_actions": ["implement.target_scope", "verify.selected_matrix"],
        "snapshot_reuse_status": "fail_closed_identity",
        "snapshot_duration_ms": 0.0,
    }
    compact = _apply_handshake_metadata(compact, handshake)
    compact.setdefault("snapshot_estimated_tokens", _estimate_json_tokens(compact))
    compact.setdefault("runtime_contract_estimated_tokens", 0)
    compact.setdefault("total_payload_estimated_tokens", 0)
    return compact


def _declares_noncanonical_execution_identity(value: Mapping[str, Any]) -> bool:
    identity_status = _component_key(value.get("identity_status"))
    target_component_status = _component_key(value.get("target_component_status"))
    return (
        identity_status == "blocked-noncanonical-target"
        or target_component_status == "blocked-noncanonical-execution-engine"
        or _target_component_status(_component_ids(value, {}, {})) == "blocked_noncanonical_execution_engine"
    )


def _fail_closed_handshake_from_snapshot(
    handshake: Mapping[str, Any],
    snapshot: Mapping[str, Any],
) -> dict[str, Any]:
    compact_handshake = dict(handshake)
    target_component_ids = _noncanonical_targets_first(_component_ids(snapshot, {}, {}))
    if target_component_ids:
        compact_handshake["target_component_id"] = target_component_ids[0]
        compact_handshake["target_component_ids"] = target_component_ids[:4]
    compact_handshake["identity_status"] = "blocked_noncanonical_target"
    compact_handshake["target_component_status"] = "blocked_noncanonical_execution_engine"
    return compact_handshake


def compact_execution_engine_snapshot_for_packet(
    *,
    payload: Mapping[str, Any],
    context_packet: Mapping[str, Any] | None = None,
    routing_handoff: Mapping[str, Any] | None = None,
    host_candidates: Sequence[Any] = (),
    environ: Mapping[str, str] | None = None,
    context_pressure: str = "",
    reuse_existing: bool = True,
) -> dict[str, Any]:
    context = _mapping(context_packet) or _mapping(payload.get("context_packet"))
    handshake = normalize_execution_engine_handshake(
        payload=payload,
        context_packet=context,
        routing_handoff=routing_handoff,
    )
    if handshake.get("target_component_status") == "blocked_noncanonical_execution_engine":
        compact = _fail_closed_identity_snapshot(handshake)
        compact["total_payload_estimated_tokens"] = _estimate_json_tokens(payload)
        return compact

    if reuse_existing:
        for source, reuse_status in (
            (payload.get("execution_engine"), "reused_payload_snapshot"),
            (context.get("execution_engine"), "reused_context_packet_snapshot"),
        ):
            existing = _mapping(source)
            if existing:
                if "contract" in existing:
                    compact = runtime_surface_governance.compact_execution_engine_snapshot(existing)
                else:
                    compact = dict(existing)
                compact = _apply_handshake_metadata(compact, handshake)
                if _declares_noncanonical_execution_identity(compact):
                    failed = _fail_closed_identity_snapshot(
                        _fail_closed_handshake_from_snapshot(handshake, compact)
                    )
                    failed["total_payload_estimated_tokens"] = _estimate_json_tokens(payload)
                    return failed
                compact.setdefault("snapshot_reuse_status", reuse_status)
                compact.setdefault("handshake_version", HANDSHAKE_VERSION)
                compact.setdefault("snapshot_estimated_tokens", _estimate_json_tokens(compact))
                compact.setdefault("runtime_contract_estimated_tokens", _estimate_json_tokens(existing.get("runtime_contract")))
                compact.setdefault("total_payload_estimated_tokens", _estimate_json_tokens(payload))
                compact.setdefault("handshake_estimated_tokens", _estimate_json_tokens(handshake))
                return compact

    started_at = time.perf_counter()
    host_candidate_rows = [
        *tuple(host_candidates),
        *_strings(payload.get("host_candidates")),
        _string(payload.get("host_runtime")),
        _string(_mapping(context.get("execution_profile")).get("host_runtime")),
    ]
    snapshot = runtime_surface_governance.build_packet_execution_engine_snapshot(
        payload=payload,
        context_packet=context,
        routing_handoff=routing_handoff,
        host_candidates=tuple(row for row in host_candidate_rows if _string(row)),
        environ=environ,
        context_pressure=context_pressure,
    )
    compact = runtime_surface_governance.compact_execution_engine_snapshot(snapshot)
    duration_ms = round((time.perf_counter() - started_at) * 1000.0, 3)
    compact["handshake_version"] = HANDSHAKE_VERSION
    compact["snapshot_reuse_status"] = "built"
    compact["snapshot_duration_ms"] = duration_ms
    compact["snapshot_estimated_tokens"] = _estimate_json_tokens(compact)
    compact["runtime_contract_estimated_tokens"] = _estimate_json_tokens(
        snapshot.get("runtime_contract")
    )
    compact["total_payload_estimated_tokens"] = _estimate_json_tokens(payload)
    compact["handshake_estimated_tokens"] = _estimate_json_tokens(
        handshake
    )
    return _apply_handshake_metadata(compact, handshake)


__all__ = [
    "CANONICAL_EXECUTION_ENGINE_COMPONENT_ID",
    "HANDSHAKE_VERSION",
    "NONCANONICAL_EXECUTION_ENGINE_COMPONENT_IDS",
    "attach_execution_engine_handshake",
    "compact_execution_engine_snapshot_for_packet",
    "normalize_execution_engine_handshake",
]
