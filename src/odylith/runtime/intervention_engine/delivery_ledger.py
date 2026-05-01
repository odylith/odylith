"""Low-latency delivery read model for visible Odylith moments."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from typing import Mapping

from odylith.runtime.intervention_engine import stream_state
from odylith.runtime.intervention_engine import visible_delivery_frontier
from odylith.runtime.intervention_engine import visibility_contract


_normalize_string = visibility_contract.normalize_string
_normalize_token = visibility_contract.normalize_token
_normalize_string_list = visibility_contract.normalize_string_list


def _compact_event(row: Mapping[str, Any]) -> dict[str, Any]:
    has_display = bool(visibility_contract.event_display_text(row))
    return {
        "kind": _normalize_token(row.get("kind")),
        "visibility_family": visibility_contract.event_visibility_family(row),
        "summary": _normalize_string(row.get("summary")),
        "ts_iso": _normalize_string(row.get("ts_iso")),
        "session_id": _normalize_string(row.get("session_id")),
        "host_family": visibility_contract.event_host_family(row),
        "turn_phase": _normalize_token(row.get("turn_phase")),
        "intervention_key": _normalize_string(row.get("intervention_key")),
        "delivery_channel": _normalize_token(row.get("delivery_channel")),
        "delivery_status": _normalize_token(row.get("delivery_status")),
        "render_surface": _normalize_token(row.get("render_surface")),
        "visible": visibility_contract.event_visible(row),
        "chat_confirmed": visibility_contract.event_chat_confirmed(row),
        "requires_chat_confirmation": visibility_contract.event_requires_chat_confirmation(row),
        "needs_chat_confirmation": visibility_contract.event_needs_chat_confirmation(row),
        "has_display": has_display,
        "chat_confirmation_key": visibility_contract.event_confirmation_key(row) if has_display else "",
        "delivery_bundle_id": visible_delivery_frontier.event_bundle_id(row),
        "action_surfaces": _normalize_string_list(row.get("action_surfaces")),
    }


def _empty_visibility_ratios() -> dict[str, dict[str, Any]]:
    return {
        family: {
            "total": 0,
            "ledger_visible": 0,
            "chat_confirmed": 0,
            "pending_confirmation": 0,
            "ledger_visible_ratio": None,
            "chat_confirmed_ratio": None,
        }
        for family in visibility_contract.VISIBILITY_FAMILIES
    }


def _finalize_visibility_ratios(ratios: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    for bucket in ratios.values():
        total = int(bucket.get("total") or 0)
        if total <= 0:
            continue
        bucket["ledger_visible_ratio"] = round(float(bucket.get("ledger_visible") or 0) / total, 4)
        bucket["chat_confirmed_ratio"] = round(float(bucket.get("chat_confirmed") or 0) / total, 4)
    return ratios


def _ratio_identity(row: Mapping[str, Any]) -> tuple[str, str]:
    """Return the unique beat identity used for chat-visibility ratios."""
    key = str(visibility_contract.event_confirmation_key(row) or "").strip()
    family = str(visibility_contract.event_visibility_family(row) or "other")
    return key, family if family in visibility_contract.VISIBILITY_FAMILIES else "other"


def delivery_snapshot(
    *,
    repo_root: Path | str,
    host_family: str = "",
    session_id: str = "",
    limit: int = 200,
) -> dict[str, Any]:
    """Return a cheap derived ledger from Compass intervention events.

    This deliberately reads only the local append-only agent stream through
    `stream_state`; it never performs repo-wide search or runtime refresh.
    """

    root = Path(repo_root).expanduser().resolve()
    rows = stream_state.load_recent_intervention_events(
        repo_root=root,
        limit=max(1, int(limit)),
        session_id=_normalize_string(session_id),
    )
    host = _normalize_token(host_family)
    if host:
        rows = [row for row in rows if visibility_contract.event_host_family(row) == host]

    counts_by_kind: dict[str, int] = {}
    counts_by_status: dict[str, int] = {}
    counts_by_channel: dict[str, int] = {}
    compact_rows: list[dict[str, Any]] = []
    visible_rows: list[dict[str, Any]] = []
    chat_confirmed_rows: list[dict[str, Any]] = []
    visibility_ratios = _empty_visibility_ratios()
    ratio_states: dict[str, dict[str, Any]] = {}

    for row in rows:
        compact = _compact_event(row)
        kind = str(compact.get("kind") or "unknown")
        status = str(compact.get("delivery_status") or "unknown")
        channel = str(compact.get("delivery_channel") or "unknown")
        counts_by_kind[kind] = counts_by_kind.get(kind, 0) + 1
        counts_by_status[status] = counts_by_status.get(status, 0) + 1
        counts_by_channel[channel] = counts_by_channel.get(channel, 0) + 1
        compact_rows.append(compact)
        if bool(compact.get("visible")):
            visible_rows.append(compact)
        if visibility_contract.event_chat_confirmed(row):
            chat_confirmed_rows.append(compact)
        key, family = _ratio_identity(row)
        if not key:
            continue
        state = ratio_states.setdefault(
            key,
            {
                "family": family,
                "ledger_visible": False,
                "chat_confirmed": False,
                "latest_index": -1,
            },
        )
        state["family"] = family
        state["ledger_visible"] = bool(state["ledger_visible"]) or bool(compact.get("visible"))
        state["chat_confirmed"] = bool(state["chat_confirmed"]) or bool(compact.get("chat_confirmed"))
        state["latest_index"] = max(int(state.get("latest_index") or -1), len(compact_rows) - 1)

    for state in ratio_states.values():
        family = str(state.get("family") or "other")
        if visible_delivery_frontier.teaser_superseded_by_later_live_beat(
            rows,
            latest_index=int(state.get("latest_index") or -1),
            visible=bool(state.get("ledger_visible")),
            chat_confirmed=bool(state.get("chat_confirmed")),
            family=family,
        ):
            continue
        if family not in visibility_ratios:
            family = "other"
        visibility_ratios[family]["total"] += 1
        if bool(state.get("ledger_visible")):
            visibility_ratios[family]["ledger_visible"] += 1
        if bool(state.get("chat_confirmed")):
            visibility_ratios[family]["chat_confirmed"] += 1

    frontier_rows = visible_delivery_frontier.active_unconfirmed_rows(rows)
    unconfirmed_rows = [_compact_event(row) for row in frontier_rows]
    pending_keys: set[str] = set()
    for row in unconfirmed_rows:
        key = str(row.get("chat_confirmation_key") or row.get("delivery_bundle_id") or "").strip()
        if key in pending_keys:
            continue
        if key:
            pending_keys.add(key)
        family = str(row.get("visibility_family") or "other")
        if family not in visibility_ratios:
            family = "other"
        visibility_ratios[family]["pending_confirmation"] += 1

    pending_state = dict(stream_state.pending_proposal_state(repo_root=root))
    pending_rows = pending_state.get("pending")
    if isinstance(pending_rows, list) and (host or _normalize_string(session_id)):
        wanted_session = _normalize_string(session_id)
        filtered_pending = [
            dict(row)
            for row in pending_rows
            if isinstance(row, Mapping)
            and (not host or visibility_contract.event_host_family(row) == host)
            and (not wanted_session or _normalize_string(row.get("session_id")) == wanted_session)
        ]
        pending_state["pending"] = filtered_pending
        pending_state["pending_count"] = len(filtered_pending)
    return {
        "version": "v1",
        "repo_root": str(root),
        "host_family": host,
        "session_id": _normalize_string(session_id),
        "event_count": len(compact_rows),
        "visible_event_count": len(visible_rows),
        "chat_confirmed_event_count": len(chat_confirmed_rows),
        "unconfirmed_event_count": len(unconfirmed_rows),
        "counts_by_kind": counts_by_kind,
        "counts_by_status": counts_by_status,
        "counts_by_channel": counts_by_channel,
        "visibility_ratios": _finalize_visibility_ratios(visibility_ratios),
        "latest_event": compact_rows[-1] if compact_rows else {},
        "latest_visible_event": visible_rows[-1] if visible_rows else {},
        "latest_chat_confirmed_event": chat_confirmed_rows[-1] if chat_confirmed_rows else {},
        "latest_unconfirmed_event": unconfirmed_rows[-1] if unconfirmed_rows else {},
        "recent_events": compact_rows[-8:],
        "recent_unconfirmed_events": unconfirmed_rows[-8:],
        "active_frontier_bundle_id": _normalize_string(unconfirmed_rows[-1].get("delivery_bundle_id")) if unconfirmed_rows else "",
        "active_frontier_event_count": len(unconfirmed_rows),
        "pending_proposal_state": pending_state,
    }


def active_lane_matrix(*, host_family: str) -> list[dict[str, str]]:
    host = _normalize_token(host_family)
    prompt_visibility = (
        "model-context recovery; visible only when the assistant renders it"
        if host == "codex"
        else "prompt-context recovery plus best-effort prompt-teaser stdout"
    )
    edit_visibility = (
        "Bash checkpoint hook with cached grounding and assistant recovery; "
        "native apply_patch depends on host dispatch or visible recovery"
        if host == "codex"
        else "Write/Edit/MultiEdit and Bash checkpoint hooks with assistant recovery"
    )
    return [
        {
            "lane": "Teaser",
            "phase": "prompt_submit",
            "visibility": prompt_visibility,
        },
        {
            "lane": "Ambient Highlight",
            "phase": "post-tool checkpoints and stop-summary recovery",
            "visibility": edit_visibility,
        },
        {
            "lane": "Odylith Observation",
            "phase": "post-tool checkpoints, with stop-summary recovery",
            "visibility": edit_visibility,
        },
        {
            "lane": "Odylith Proposal",
            "phase": "post-tool checkpoints only when governed targets are concrete",
            "visibility": edit_visibility,
        },
        {
            "lane": "Odylith Assist",
            "phase": "prompt-submit visible recovery, explicit visibility feedback, and stop-summary closeout",
            "visibility": (
                "assistant-visible recovery keeps Assist as the final line for prompt-rendered Odylith output; "
                "stop uses the one-shot continuation guard"
            ),
        },
    ]


__all__ = ["active_lane_matrix", "delivery_snapshot"]
