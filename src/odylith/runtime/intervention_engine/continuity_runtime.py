"""Cache-backed continuity snapshots for intervention moments."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from typing import Sequence

from odylith.runtime.intervention_engine import stream_state
from odylith.runtime.intervention_engine import visibility_contract

_CONTINUITY_CACHE: dict[tuple[tuple[str, int, int], str, str, str, int], dict[str, Any]] = {}
_VISIBLE_DELIVERY_STATUSES = {
    "assistant_chat_confirmed",
    "best_effort_visible",
    "manual_visible",
    "stop_continuation_ready",
}
_VISIBLE_DELIVERY_CHANNELS = {
    "assistant_chat_transcript",
    "manual_visible_command",
    "stdout_teaser",
    "stop_one_shot_guard",
}


_normalize_string = visibility_contract.normalize_string
_normalize_string_list = visibility_contract.normalize_string_list


def _signature_token(value: Any) -> str:
    """Render semantic-signature content into a cache-friendly token."""
    return "|".join(_normalize_string_list(value))


_mapping = visibility_contract.mapping_copy


def _event_kind(event: Mapping[str, Any]) -> str:
    """Normalize intervention event kinds for stage comparisons."""
    return _normalize_string(event.get("kind")).lower()


def _event_stage(event: Mapping[str, Any]) -> str:
    """Map an intervention event into the visible continuity stage it implies."""
    kind = _event_kind(event)
    if kind in {"intervention_teaser", "ambient_signal"}:
        return "teaser"
    if kind == "intervention_card":
        return "card"
    if kind in {"capture_proposed", "capture_applied", "capture_declined"}:
        return "proposal"
    return "silent"


def _event_has_proven_visible_delivery(event: Mapping[str, Any]) -> bool:
    """Return whether delivery metadata proves the event was chat-visible."""
    status = _normalize_string(event.get("delivery_status")).lower().replace("-", "_").replace(" ", "_")
    channel = _normalize_string(event.get("delivery_channel")).lower().replace("-", "_").replace(" ", "_")
    if status in _VISIBLE_DELIVERY_STATUSES:
        return True
    return channel in _VISIBLE_DELIVERY_CHANNELS


def _matching_events(
    *,
    rows: Sequence[Mapping[str, Any]],
    moment_key: str,
    signature_token: str,
) -> list[dict[str, Any]]:
    """Prefer exact-key matches and fall back to semantic-signature matches."""
    key_matches: list[dict[str, Any]] = []
    signature_matches: list[dict[str, Any]] = []
    for row in rows:
        payload = _mapping(row)
        row_key = _normalize_string(payload.get("intervention_key"))
        row_signature = _signature_token(payload.get("semantic_signature"))
        if moment_key and row_key == moment_key:
            key_matches.append(payload)
            continue
        if signature_token and row_signature and row_signature == signature_token:
            signature_matches.append(payload)
    return key_matches if key_matches else signature_matches


def moment_continuity_snapshot(
    *,
    repo_root: Path,
    session_id: str,
    moment_key: str,
    semantic_signature: Sequence[str] = (),
    limit: int = 120,
) -> dict[str, Any]:
    """Return the visible continuity state for one intervention moment."""
    signature_token = _signature_token(semantic_signature)
    cache_key = (
        stream_state.event_cache_signature(repo_root=repo_root),
        _normalize_string(session_id),
        _normalize_string(moment_key),
        signature_token,
        max(1, int(limit)),
    )
    cached = _CONTINUITY_CACHE.get(cache_key)
    if cached is not None:
        return dict(cached)
    rows = stream_state.load_recent_intervention_events(
        repo_root=repo_root,
        limit=limit,
        session_id=session_id,
    )
    matching = _matching_events(
        rows=rows,
        moment_key=_normalize_string(moment_key),
        signature_token=signature_token,
    )
    latest = matching[-1] if matching else {}
    latest_kind = _event_kind(latest)
    seen_teaser = any(_event_kind(row) in {"intervention_teaser", "ambient_signal"} for row in matching)
    seen_card = any(_event_kind(row) == "intervention_card" for row in matching)
    latest_moment_kind = _normalize_string(latest.get("moment_kind")).lower()
    latest_stage = _event_stage(latest)
    proposal_pending = latest_kind == "capture_proposed"
    proposal_applied = latest_kind == "capture_applied"
    declined = latest_kind == "capture_declined"
    if seen_card or proposal_pending or proposal_applied or declined:
        stage_floor = "card"
    elif seen_teaser:
        stage_floor = "teaser"
    else:
        stage_floor = "silent"
    payload = {
        "matching_event_count": len(matching),
        "seen_teaser": seen_teaser,
        "seen_card": seen_card,
        "proposal_pending": proposal_pending,
        "proposal_applied": proposal_applied,
        "declined": declined,
        "stage_floor": stage_floor,
        "latest_kind": latest_kind,
        "latest_stage": latest_stage,
        "latest_moment_kind": latest_moment_kind,
        "latest_summary": _normalize_string(latest.get("summary")),
        "latest_display_markdown": _normalize_string(latest.get("display_markdown")),
        "latest_display_plain": _normalize_string(latest.get("display_plain")),
        "latest_turn_phase": _normalize_string(latest.get("turn_phase")).lower(),
        "latest_delivery_channel": _normalize_string(latest.get("delivery_channel")).lower(),
        "latest_delivery_status": _normalize_string(latest.get("delivery_status")).lower(),
        "latest_proven_visible_delivery": _event_has_proven_visible_delivery(latest),
    }
    _CONTINUITY_CACHE[cache_key] = payload
    return dict(payload)


def evolve_candidate_stage(*, stage: str, continuity: Mapping[str, Any]) -> str:
    """Suppress teaser reruns once the same moment has advanced further."""
    normalized = _normalize_string(stage).lower()
    floor = _normalize_string(continuity.get("stage_floor")).lower()
    if floor == "card" and normalized == "teaser":
        return "silent"
    return normalized or "silent"
