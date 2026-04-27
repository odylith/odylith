"""Governance Signal Codec helpers for the Odylith context engine layer."""

from __future__ import annotations

from typing import Any, Mapping

_CANONICAL_TO_COMPACT = {
    "recommended_command_count": "rc",
    "strict_gate_command_count": "sg",
    "plan_binding_required": "pb",
    "governed_surface_sync_required": "gs",
    "touched_workstream_count": "tw",
    "primary_workstream_id": "w",
    "touched_component_count": "tc",
    "primary_component_id": "c",
    "required_diagram_count": "d",
    "linked_bug_count": "lb",
    "closeout_doc_count": "cd",
    "workstream_state_action_count": "wa",
    "surface_count": "sf",
    "reason_group_count": "rg",
}
_COMPACT_TO_CANONICAL = {value: key for key, value in _CANONICAL_TO_COMPACT.items()}


def expand_governance_signal(signal: Mapping[str, Any] | None) -> dict[str, Any]:
    if not isinstance(signal, Mapping):
        return {}
    expanded: dict[str, Any] = {}
    for raw_key, raw_value in signal.items():
        key = _COMPACT_TO_CANONICAL.get(str(raw_key).strip(), str(raw_key).strip())
        if not key or raw_value in ("", [], {}, None, False):
            continue
        expanded[key] = raw_value
    return expanded


def compact_governance_signal(signal: Mapping[str, Any] | None) -> dict[str, Any]:
    if not isinstance(signal, Mapping):
        return {}
    compact: dict[str, Any] = {}
    for raw_key, raw_value in expand_governance_signal(signal).items():
        key = _CANONICAL_TO_COMPACT.get(str(raw_key).strip(), str(raw_key).strip())
        if not key or raw_value in ("", [], {}, None, False):
            continue
        compact[key] = raw_value
    return compact


def governance_signal_value(signal: Mapping[str, Any] | None, key: str, default: Any = None) -> Any:
    expanded = expand_governance_signal(signal)
    token = str(key or "").strip()
    return expanded.get(token, default) if token else default


__all__ = [
    "compact_governance_signal",
    "expand_governance_signal",
    "governance_signal_value",
]
