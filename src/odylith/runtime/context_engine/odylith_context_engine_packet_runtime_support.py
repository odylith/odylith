"""Shared packet-shaping helpers for context-engine packet runtimes.

These helpers are used by packet summary, architecture, and runtime-learning
paths. They own the compact packet token/selection codec directly so callers do
not need runtime globals rebinding just to interpret packet metadata.
"""

from __future__ import annotations

import re
from typing import Any
from typing import Mapping

from odylith.runtime.common.value_coercion import normalize_string_list


def normalized_string_list(values: Any) -> list[str]:
    """Return a stable deduplicated string list for packet payload fields."""
    return normalize_string_list(values)


def workstream_token(value: str) -> str:
    """Extract the first well-formed workstream id from free-form text."""
    match = re.search(r"B-\d{3,}", str(value or "").upper())
    return match.group(0) if match is not None else ""


def compact_selection_state_parts(value: str) -> tuple[str, str]:
    """Decode compact selection-state tokens into state and explicit id."""
    token = str(value or "").strip()
    if not token:
        return "", ""
    if token.startswith("x:"):
        return "explicit", workstream_token(token[2:])
    if token.startswith("i:"):
        return "inferred_confident", workstream_token(token[2:])
    workstream = workstream_token(token)
    if workstream and token == workstream:
        return "explicit", workstream
    return token, ""


def encode_compact_selection_state(*, state: str, workstream: str) -> str:
    """Encode selection state into the compact packet token form."""
    normalized_state = str(state or "").strip()
    selected_workstream = workstream_token(workstream)
    if normalized_state == "explicit" and selected_workstream:
        return f"x:{selected_workstream}"
    if normalized_state == "inferred_confident" and selected_workstream:
        return f"i:{selected_workstream}"
    return normalized_state


def decode_compact_selected_counts(value: Any) -> dict[str, int]:
    """Decode compact selected-count payloads from token or mapping form."""
    if isinstance(value, Mapping):
        counts: dict[str, int] = {}
        for key, raw in value.items():
            token = str(key).strip()
            if not token:
                continue
            try:
                count = int(raw or 0)
            except (TypeError, ValueError):
                continue
            if count > 0:
                counts[token] = count
        return counts
    token = str(value or "").strip()
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
        count = int(raw_count or 0)
        if key and count > 0:
            counts[key] = count
    return counts


def encode_compact_selected_counts(counts: Mapping[str, Any]) -> str:
    """Encode selected-count mappings into the compact packet token form."""
    normalized = decode_compact_selected_counts(counts)
    if not normalized:
        return ""
    parts: list[str] = []
    for key, alias in (("commands", "c"), ("docs", "d"), ("tests", "t"), ("guidance", "g")):
        count = int(normalized.get(key, 0) or 0)
        if count > 0:
            parts.append(f"{alias}{count}")
    return "".join(parts)


def payload_workstream_hint(
    payload: Mapping[str, Any] | None,
    *,
    include_selection: bool = True,
) -> str:
    """Return the strongest workstream hint available inside a packet payload."""
    if not isinstance(payload, Mapping):
        return ""
    for key in ("inferred_workstream", "workstream", "ws"):
        token = workstream_token(str(payload.get(key, "")).strip())
        if token:
            return token
    context_packet = (
        dict(payload.get("context_packet", {}))
        if isinstance(payload.get("context_packet"), Mapping)
        else {}
    )
    _, compact_workstream = compact_selection_state_parts(str(context_packet.get("selection_state", "")).strip())
    if compact_workstream:
        return compact_workstream
    if not include_selection:
        return ""
    selection = (
        dict(payload.get("workstream_selection", {}))
        if isinstance(payload.get("workstream_selection"), Mapping)
        else {}
    )
    for field_name in ("selected_workstream", "top_candidate"):
        row = dict(selection.get(field_name, {})) if isinstance(selection.get(field_name), Mapping) else {}
        token = workstream_token(str(row.get("entity_id", "")).strip())
        if token:
            return token
    selection_payload = (
        dict(context_packet.get("selection", {}))
        if isinstance(context_packet.get("selection"), Mapping)
        else {}
    )
    for token in normalized_string_list(selection_payload.get("workstream_ids")):
        selected_workstream = workstream_token(token)
        if selected_workstream:
            return selected_workstream
    return ""


def payload_packet_kind(
    payload: Mapping[str, Any] | None,
    *,
    context_packet: Mapping[str, Any] | None = None,
    routing_handoff: Mapping[str, Any] | None = None,
) -> str:
    """Resolve the effective packet kind from payload, context, or routing."""
    if isinstance(payload, Mapping):
        packet_kind = str(payload.get("packet_kind", "")).strip()
        if packet_kind:
            return packet_kind
    if isinstance(context_packet, Mapping):
        packet_kind = str(context_packet.get("packet_kind", "")).strip()
        if packet_kind:
            return packet_kind
        route = dict(context_packet.get("route", {})) if isinstance(context_packet.get("route"), Mapping) else {}
        if isinstance(route.get("governance"), Mapping):
            return "governance_slice"
    if isinstance(routing_handoff, Mapping):
        packet_kind = str(routing_handoff.get("packet_kind", "")).strip()
        if packet_kind:
            return packet_kind
    return "impact" if isinstance(context_packet, Mapping) and context_packet else ""


def repo_scan_degraded_reason(packet: Mapping[str, Any]) -> str:
    """Normalize the bounded repo-scan degradation reason from packet payload."""
    route = dict(packet.get("route", {})) if isinstance(packet.get("route"), Mapping) else {}
    narrowing = dict(packet.get("narrowing_guidance", {})) if isinstance(packet.get("narrowing_guidance"), Mapping) else {}
    fallback = dict(packet.get("fallback_scan", {})) if isinstance(packet.get("fallback_scan"), Mapping) else {}
    reasons = (
        str(packet.get("repo_scan_degraded_reason", "")).strip(),
        str(packet.get("full_scan_reason", "")).strip(),
        str(route.get("full_scan_reason", "")).strip(),
        str(narrowing.get("reason", "")).strip() if bool(narrowing.get("required")) else "",
        str(fallback.get("reason", "")).strip(),
    )
    for reason in reasons:
        if reason:
            return reason
    return ""
