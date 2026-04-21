"""Collapse visible-delivery history to the current unresolved transcript frontier.

The intervention stream is append-only and can record many historical fallback
or manual-visible rows inside one chat session. Replay and proof should operate
on the current unresolved delivery bundle, not on every older row forever.
"""

from __future__ import annotations

from typing import Any
from typing import Mapping

from odylith.runtime.intervention_engine import visibility_contract

_normalize_string = visibility_contract.normalize_string
_normalize_token = visibility_contract.normalize_token


def _event_family(row: Mapping[str, Any]) -> str:
    """Return the normalized visible family for one delivery row."""
    return visibility_contract.event_visibility_family(row)


def teaser_superseded_by_later_live_beat(
    rows: list[Mapping[str, Any]],
    *,
    latest_index: int,
    family: str,
    visible: bool = False,
    chat_confirmed: bool = False,
) -> bool:
    """Return whether a hidden teaser was retired by a later stronger beat."""
    if family != "teaser" or visible or chat_confirmed:
        return False
    return any(
        _event_family(later_row) in {"ambient", "intervention", "assist"}
        for later_row in rows[latest_index + 1 :]
    )


def event_bundle_id(row: Mapping[str, Any]) -> str:
    """Return the stable delivery-bundle id for one intervention event row."""
    metadata = row.get("metadata")
    if isinstance(metadata, Mapping):
        selected_block_set_id = _normalize_string(metadata.get("selected_block_set_id"))
        if selected_block_set_id:
            return f"selected:{selected_block_set_id}"
    session_id = _normalize_string(row.get("session_id"))
    render_surface = _normalize_token(row.get("render_surface"))
    host_family = visibility_contract.event_host_family(row)
    turn_phase = _normalize_token(row.get("turn_phase"))
    delivery_channel = _normalize_token(row.get("delivery_channel"))
    delivery_status = _normalize_token(row.get("delivery_status"))
    ts_iso = _normalize_string(row.get("ts_iso"))
    if session_id and ts_iso and visibility_contract.event_display_text(row):
        return (
            "legacy:"
            f"{session_id}|{host_family}|{turn_phase}|{delivery_channel}|{delivery_status}|"
            f"{render_surface}|{ts_iso}"
        )
    confirmation_key = visibility_contract.event_confirmation_key(row)
    if confirmation_key:
        return f"key:{confirmation_key}"
    return ""


def active_unconfirmed_rows(rows: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Return the current unresolved delivery bundle for one session/host slice."""
    confirmed_keys: set[str] = set()
    confirmed_bundles: set[str] = set()
    bundles: dict[str, list[dict[str, Any]]] = {}
    bundle_last_index: dict[str, int] = {}
    bundle_requires_chat: dict[str, bool] = {}
    bundle_families: dict[str, set[str]] = {}

    for row in rows:
        key = visibility_contract.event_confirmation_key(row)
        bundle_id = event_bundle_id(row)
        if visibility_contract.event_chat_confirmed(row):
            if key:
                confirmed_keys.add(key)
            if bundle_id:
                confirmed_bundles.add(bundle_id)

    for index, row in enumerate(rows):
        if visibility_contract.event_chat_confirmed(row):
            continue
        if not visibility_contract.event_needs_chat_confirmation(row):
            continue
        key = visibility_contract.event_confirmation_key(row)
        if key and key in confirmed_keys:
            continue
        bundle_id = event_bundle_id(row) or f"row:{index}"
        if bundle_id in confirmed_bundles:
            continue
        bundles.setdefault(bundle_id, []).append(dict(row))
        bundle_last_index[bundle_id] = index
        requires_chat = visibility_contract.event_requires_chat_confirmation(row)
        bundle_requires_chat[bundle_id] = bundle_requires_chat.get(bundle_id, False) or requires_chat
        family = _event_family(row)
        if family:
            bundle_families.setdefault(bundle_id, set()).add(family)

    if not bundles:
        return []

    candidate_bundle_ids = [
        bundle_id
        for bundle_id, requires_chat in bundle_requires_chat.items()
        if requires_chat
    ] or list(bundles)
    candidate_bundle_ids = [
        bundle_id
        for bundle_id in candidate_bundle_ids
        if not (
            teaser_superseded_by_later_live_beat(
                rows,
                latest_index=bundle_last_index[bundle_id],
                family="teaser" if bundle_families.get(bundle_id) == {"teaser"} else "",
            )
        )
    ]
    if not candidate_bundle_ids:
        return []
    active_bundle_id = max(candidate_bundle_ids, key=lambda bundle_id: bundle_last_index[bundle_id])

    selected: list[dict[str, Any]] = []
    seen_keys: set[str] = set()
    for row in bundles[active_bundle_id]:
        key = visibility_contract.event_confirmation_key(row)
        if key and key in seen_keys:
            continue
        if key:
            seen_keys.add(key)
        selected.append(dict(row))
    return selected


__all__ = ["active_unconfirmed_rows", "event_bundle_id", "teaser_superseded_by_later_live_beat"]
