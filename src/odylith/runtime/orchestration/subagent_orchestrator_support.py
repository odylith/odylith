"""Shared support helpers for the subagent orchestrator runtime slice."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from odylith.runtime.common import agent_runtime_contract
from odylith.runtime.common.value_coercion import float_value as _float_value
from odylith.runtime.common.value_coercion import int_value as _int_value
from odylith.runtime.common.value_coercion import normalize_string_list as _dedupe_strings
from odylith.runtime.common.value_coercion import normalize_string as _normalize_string
from odylith.runtime.common.value_coercion import normalize_token as _normalize_token
from odylith.runtime.context_engine import packet_quality_codec
from odylith.runtime.memory import tooling_memory_contracts
from odylith.runtime.orchestration import subagent_router as leaf_router
from odylith.runtime.orchestration.subagent_signal_normalization import mapping_value as _mapping_lookup
from odylith.runtime.orchestration.subagent_signal_normalization import nested_mapping as _nested_mapping
from odylith.runtime.orchestration.subagent_signal_normalization import normalize_context_signals as _normalize_context_signals
from odylith.runtime.orchestration.subagent_signal_normalization import normalize_list as _normalize_list
from odylith.runtime.orchestration.subagent_signal_normalization import normalized_rate as _normalized_rate

_GOVERNANCE_GROUNDING_KEYWORDS: tuple[str, ...] = (
    "governance",
    "workstream",
    "backlog",
    "plan binding",
    "traceability",
    "closeout",
    "delivery truth",
    "registry",
    "compass",
    "radar",
    "sync_workstream_artifacts",
    "governed surface",
)
_ARCHITECTURE_GROUNDING_KEYWORDS: tuple[str, ...] = (
    "architecture",
    "topology",
    "control-plane",
    "shared-stack",
    "shared stack",
    "diagram",
    "mermaid",
    "authority chain",
    "blast radius",
    "ownership boundary",
    "tenant boundary",
)
_AGENT_HOT_PATH_PROFILE = agent_runtime_contract.AGENT_HOT_PATH_PROFILE


def _extract_context_signals_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Extract the orchestration-relevant context payload from a larger mapping."""
    explicit = payload.get("context_signals")
    if isinstance(explicit, Mapping):
        return _normalize_context_signals(explicit)
    extracted: dict[str, Any] = {}
    for key in (
        "routing_handoff",
        "context_packet",
        "evidence_pack",
        "optimization_snapshot",
        "architecture_audit",
        "validation_bundle",
        "governance_obligations",
        "surface_refs",
    ):
        value = payload.get(key)
        if isinstance(value, Mapping):
            extracted[key] = dict(value)
    diagram_watch_gaps = payload.get("diagram_watch_gaps")
    if isinstance(diagram_watch_gaps, list):
        extracted["diagram_watch_gaps"] = list(diagram_watch_gaps)
    if extracted:
        return _normalize_context_signals(extracted)
    return _normalize_context_signals(payload.get("routing_handoff", {}))


def _sanitize_user_facing_text(value: Any) -> str:
    """Delegate user-facing copy cleanup to the router-owned sanitizer."""
    return leaf_router._sanitize_user_facing_text(value)  # noqa: SLF001


def _sanitize_user_facing_lines(values: Sequence[str]) -> list[str]:
    """Delegate line-wise user-facing cleanup to the router-owned sanitizer."""
    return leaf_router._sanitize_user_facing_lines(values)  # noqa: SLF001


def _execution_profile_mapping(value: Any) -> dict[str, Any]:
    """Normalize execution-profile memory into router-friendly runtime fields."""
    profile = tooling_memory_contracts.execution_profile_mapping(value)
    if not profile:
        return {}
    selected = leaf_router._preferred_router_profile_from_execution_profile(profile)  # noqa: SLF001
    if selected is None:
        return profile
    profile["profile"] = selected.value
    profile["model"] = selected.model
    profile["reasoning_effort"] = selected.reasoning_effort
    return profile


def _request_seed_paths(request: Any) -> list[str]:
    """Return the explicit path seeds that can anchor Odylith grounding."""
    return _dedupe_strings(
        [
            *getattr(request, "candidate_paths", []),
            *getattr(request, "claimed_paths", []),
        ]
    )


def _request_has_odylith_seeds(request: Any) -> bool:
    """Return whether the request already carries usable Odylith grounding hints."""
    return bool(
        _request_seed_paths(request)
        or getattr(request, "workstreams", [])
        or getattr(request, "components", [])
        or getattr(request, "session_id", "")
        or getattr(request, "use_working_tree", False)
    )


def _payload_context_packet(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Return the embedded context packet when present."""
    return dict(payload.get("context_packet", {})) if isinstance(payload.get("context_packet"), Mapping) else {}


def _payload_routing_handoff(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Return the embedded routing handoff when present."""
    return dict(payload.get("routing_handoff", {})) if isinstance(payload.get("routing_handoff"), Mapping) else {}


def _compact_selection_state_parts(value: Any) -> tuple[str, str]:
    """Split compact selection-state tokens into state and detail parts."""
    token = _normalize_string(value)
    if not token:
        return "", ""
    if token.startswith("x:"):
        return "explicit", _normalize_string(token[2:])
    if token.startswith("i:"):
        return "inferred_confident", _normalize_string(token[2:])
    return token, ""


def _payload_packet_kind(payload: Mapping[str, Any], *, context_packet: Mapping[str, Any], routing_handoff: Mapping[str, Any]) -> str:
    """Infer the dominant Odylith packet kind from explicit and embedded fields."""
    packet_kind = _normalize_token(payload.get("packet_kind"))
    if packet_kind:
        return packet_kind
    packet_kind = _normalize_token(context_packet.get("packet_kind"))
    if packet_kind:
        return packet_kind
    packet_kind = _normalize_token(routing_handoff.get("packet_kind"))
    if packet_kind:
        return packet_kind
    route = _nested_mapping(context_packet, "route")
    if route.get("governance"):
        return "governance_slice"
    return "impact" if context_packet else ""


def _odylith_payload_full_scan_recommended(payload: Mapping[str, Any]) -> bool:
    """Return whether the current Odylith payload still recommends a broader scan."""
    context_packet = _payload_context_packet(payload)
    architecture_audit = dict(payload.get("architecture_audit", {})) if isinstance(payload.get("architecture_audit"), Mapping) else {}
    return bool(
        payload.get("full_scan_recommended")
        or context_packet.get("full_scan_recommended")
        or architecture_audit.get("full_scan_recommended")
    )


def _odylith_payload_route_ready(payload: Mapping[str, Any]) -> bool:
    """Return whether the payload says delegation is route-ready right now."""
    context_packet = _payload_context_packet(payload)
    route = dict(context_packet.get("route", {})) if isinstance(context_packet.get("route"), Mapping) else {}
    routing_handoff = _payload_routing_handoff(payload)
    return bool(payload.get("route_ready") or route.get("route_ready") or routing_handoff.get("route_ready"))


def _odylith_payload_selection_state(payload: Mapping[str, Any]) -> str:
    """Return the normalized selection state from the Odylith payload."""
    context_packet = _payload_context_packet(payload)
    state, _ = _compact_selection_state_parts(payload.get("selection_state") or context_packet.get("selection_state"))
    return _normalize_token(state)


def _odylith_payload_routing_confidence(payload: Mapping[str, Any]) -> str:
    """Return the strongest available routing-confidence signal from the payload."""
    context_packet = _payload_context_packet(payload)
    packet_quality = packet_quality_codec.expand_packet_quality(
        dict(context_packet.get("packet_quality", {}))
        if isinstance(context_packet.get("packet_quality"), Mapping)
        else {}
    )
    routing_handoff = _payload_routing_handoff(payload)
    return (
        _normalize_token(routing_handoff.get("routing_confidence"))
        or _normalize_token(packet_quality.get("routing_confidence"))
        or _normalize_token(payload.get("routing_confidence"))
    )


def _odylith_payload_diagram_watch_gap_count(payload: Mapping[str, Any]) -> int:
    """Count unresolved diagram-watch gaps in the current payload."""
    gaps = payload.get("diagram_watch_gaps", [])
    return len(gaps) if isinstance(gaps, list) else 0


def _odylith_payload_component_ids(payload: Mapping[str, Any]) -> list[str]:
    """Extract normalized component ids from payload component rows."""
    component_rows = payload.get("components", [])
    if not isinstance(component_rows, list):
        return []
    return _dedupe_strings(
        [
            str(row.get("entity_id", "")).strip()
            for row in component_rows
            if isinstance(row, Mapping) and str(row.get("entity_id", "")).strip()
        ]
    )


def _odylith_payload_workstreams(payload: Mapping[str, Any]) -> list[str]:
    """Extract normalized workstream identifiers from common payload fields."""
    values: list[str] = []
    for key in ("inferred_workstream", "workstream", "ws"):
        token = _normalize_string(payload.get(key, ""))
        if token:
            values.append(token)
    context_packet = _payload_context_packet(payload)
    _, compact_workstream = _compact_selection_state_parts(context_packet.get("selection_state"))
    if compact_workstream:
        values.append(compact_workstream)
    primary = dict(payload.get("primary_workstream", {})) if isinstance(payload.get("primary_workstream"), Mapping) else {}
    primary_id = _normalize_string(primary.get("entity_id", ""))
    if primary_id:
        values.append(primary_id)
    workstream_selection = dict(payload.get("workstream_selection", {})) if isinstance(payload.get("workstream_selection"), Mapping) else {}
    selected = dict(workstream_selection.get("selected_workstream", {})) if isinstance(workstream_selection.get("selected_workstream"), Mapping) else {}
    selected_id = _normalize_string(selected.get("entity_id", ""))
    if selected_id:
        values.append(selected_id)
    candidate_rows = payload.get("candidate_workstreams", [])
    if isinstance(candidate_rows, list):
        values.extend(
            str(row.get("entity_id", "")).strip()
            for row in candidate_rows
            if isinstance(row, Mapping) and str(row.get("entity_id", "")).strip()
        )
    return _dedupe_strings(values)


def _odylith_payload_paths(payload: Mapping[str, Any]) -> list[str]:
    """Collect the best available path anchors from the Odylith payload."""
    context_packet = _payload_context_packet(payload)
    anchors = dict(context_packet.get("anchors", {})) if isinstance(context_packet.get("anchors"), Mapping) else {}
    values: list[str] = []
    for key in ("changed_paths", "explicit_paths"):
        raw = payload.get(key, [])
        if isinstance(raw, list):
            values.extend(str(token).strip() for token in raw if str(token).strip())
    anchor_paths = anchors.get("changed_paths", [])
    if isinstance(anchor_paths, list):
        values.extend(str(token).strip() for token in anchor_paths if str(token).strip())
    return _dedupe_strings(values)


def _merge_context_signals(base: Mapping[str, Any], overlay: Mapping[str, Any]) -> dict[str, Any]:
    """Merge two context-signal mappings while preserving nested dict structure."""
    merged = {str(key): value for key, value in dict(base).items()}
    for raw_key, raw_value in overlay.items():
        key = _normalize_string(raw_key)
        if not key:
            continue
        existing = merged.get(key)
        if isinstance(existing, Mapping) and isinstance(raw_value, Mapping):
            merged[key] = _merge_context_signals(dict(existing), dict(raw_value))
        else:
            merged[key] = raw_value
    return merged


def _clamp_confidence(value: int | float) -> int:
    """Clamp orchestration confidence values into the router's 0-4 score range."""
    return max(0, min(4, int(round(float(value)))))


__all__ = [
    "_ARCHITECTURE_GROUNDING_KEYWORDS",
    "_AGENT_HOT_PATH_PROFILE",
    "_GOVERNANCE_GROUNDING_KEYWORDS",
    "_clamp_confidence",
    "_compact_selection_state_parts",
    "_dedupe_strings",
    "_execution_profile_mapping",
    "_extract_context_signals_payload",
    "_float_value",
    "_mapping_lookup",
    "_merge_context_signals",
    "_nested_mapping",
    "_normalize_context_signals",
    "_normalize_list",
    "_normalized_rate",
    "_odylith_payload_component_ids",
    "_odylith_payload_diagram_watch_gap_count",
    "_odylith_payload_full_scan_recommended",
    "_odylith_payload_paths",
    "_odylith_payload_route_ready",
    "_odylith_payload_routing_confidence",
    "_odylith_payload_selection_state",
    "_odylith_payload_workstreams",
    "_payload_packet_kind",
    "_request_has_odylith_seeds",
    "_request_seed_paths",
    "_sanitize_user_facing_lines",
    "_sanitize_user_facing_text",
]
