"""Low-latency delivery read model for visible Odylith moments."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from typing import Mapping
from typing import Sequence

from odylith.runtime.intervention_engine import stream_state

_VISIBLE_STATUSES: frozenset[str] = frozenset(
    {
        "best_effort_visible",
        "assistant_fallback_ready",
        "manual_visible",
        "stop_continuation_ready",
        "system_message_ready",
    }
)


def _normalize_string(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _normalize_token(value: Any) -> str:
    return _normalize_string(value).lower().replace(" ", "_").replace("-", "_")


def _normalize_string_list(value: Any) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        token = _normalize_string(value)
        return [token] if token else []
    rows: list[str] = []
    seen: set[str] = set()
    for item in value:
        token = _normalize_string(item)
        if not token or token in seen:
            continue
        seen.add(token)
        rows.append(token)
    return rows


def _event_visible(row: Mapping[str, Any]) -> bool:
    status = _normalize_token(row.get("delivery_status"))
    if status in _VISIBLE_STATUSES:
        return True
    channel = _normalize_token(row.get("delivery_channel"))
    return channel in {"manual_visible_command", "stdout_teaser", "stop_one_shot_guard"}


def _compact_event(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "kind": _normalize_token(row.get("kind")),
        "summary": _normalize_string(row.get("summary")),
        "ts_iso": _normalize_string(row.get("ts_iso")),
        "session_id": _normalize_string(row.get("session_id")),
        "host_family": _normalize_token(row.get("host_family")),
        "turn_phase": _normalize_token(row.get("turn_phase")),
        "intervention_key": _normalize_string(row.get("intervention_key")),
        "delivery_channel": _normalize_token(row.get("delivery_channel")),
        "delivery_status": _normalize_token(row.get("delivery_status")),
        "render_surface": _normalize_token(row.get("render_surface")),
        "visible": _event_visible(row),
        "action_surfaces": _normalize_string_list(row.get("action_surfaces")),
    }


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
        rows = [row for row in rows if _normalize_token(row.get("host_family")) == host]

    counts_by_kind: dict[str, int] = {}
    counts_by_status: dict[str, int] = {}
    counts_by_channel: dict[str, int] = {}
    compact_rows: list[dict[str, Any]] = []
    visible_rows: list[dict[str, Any]] = []

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

    pending_state = dict(stream_state.pending_proposal_state(repo_root=root))
    pending_rows = pending_state.get("pending")
    if isinstance(pending_rows, list) and (host or _normalize_string(session_id)):
        wanted_session = _normalize_string(session_id)
        filtered_pending = [
            dict(row)
            for row in pending_rows
            if isinstance(row, Mapping)
            and (not host or _normalize_token(row.get("host_family")) == host)
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
        "counts_by_kind": counts_by_kind,
        "counts_by_status": counts_by_status,
        "counts_by_channel": counts_by_channel,
        "latest_event": compact_rows[-1] if compact_rows else {},
        "latest_visible_event": visible_rows[-1] if visible_rows else {},
        "recent_events": compact_rows[-8:],
        "pending_proposal_state": pending_state,
    }


def active_lane_matrix(*, host_family: str) -> list[dict[str, str]]:
    host = _normalize_token(host_family)
    prompt_visibility = (
        "model-context fallback; visible only when the assistant renders it"
        if host == "codex"
        else "prompt-context fallback plus best-effort prompt-teaser stdout"
    )
    edit_visibility = (
        "Bash checkpoint hook with assistant fallback"
        if host == "codex"
        else "Write/Edit/MultiEdit and Bash checkpoint hooks with assistant fallback"
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
            "phase": "stop_summary closeout only",
            "visibility": "stop one-shot continuation guard plus assistant fallback",
        },
    ]


__all__ = ["active_lane_matrix", "delivery_snapshot"]
