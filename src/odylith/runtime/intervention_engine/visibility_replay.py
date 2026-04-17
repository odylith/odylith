"""Transcript-replay read model for Odylith visible delivery.

The delivery ledger can prove that Odylith generated, queued, or attempted a
visible block. It cannot prove chat visibility until an assistant transcript
contains the exact branded text. This module returns the compact Markdown that
still needs assistant-visible replay, using the same identity rules as chat
confirmation.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from typing import Mapping

from odylith.runtime.intervention_engine import stream_state
from odylith.runtime.intervention_engine import visibility_contract


def _normalize_string(value: Any) -> str:
    return visibility_contract.normalize_string(value)


def _normalize_token(value: Any) -> str:
    return visibility_contract.normalize_token(value)


def _normalize_block_string(value: Any) -> str:
    return visibility_contract.normalize_block_string(value)


def _family(row: Mapping[str, Any]) -> str:
    family = visibility_contract.event_visibility_family(row)
    return family if family in {"ambient", "intervention", "assist", "teaser"} else "other"


def _candidate_row(
    row: Mapping[str, Any],
    *,
    key: str,
    display: str,
) -> dict[str, Any]:
    return {
        "kind": _normalize_token(row.get("kind")),
        "visibility_family": _family(row),
        "summary": _normalize_string(row.get("summary")),
        "ts_iso": _normalize_string(row.get("ts_iso")),
        "session_id": _normalize_string(row.get("session_id")),
        "host_family": visibility_contract.event_host_family(row),
        "turn_phase": _normalize_token(row.get("turn_phase")),
        "intervention_key": _normalize_string(row.get("intervention_key")),
        "chat_confirmation_key": key,
        "delivery_channel": _normalize_token(row.get("delivery_channel")),
        "delivery_status": _normalize_token(row.get("delivery_status")),
        "render_surface": _normalize_token(row.get("render_surface")),
        "display_markdown": display,
    }


def replayable_chat_blocks(
    *,
    repo_root: Path | str,
    host_family: str = "",
    session_id: str = "",
    limit: int = 200,
    max_live_blocks: int = 4,
    ambient_cap: int = 3,
    include_assist: bool = True,
    include_teaser: bool = False,
) -> list[dict[str, Any]]:
    """Return distinct Odylith blocks that still need transcript proof.

    Selection is intentionally cheap: one local stream read, host/session
    filtering, duplicate collapse by display-aware confirmation key, and a
    small live-block budget. No provider calls, repo scans, or context-store
    expansion happen here.
    """

    root = Path(repo_root).expanduser().resolve()
    normalized_session = _normalize_string(session_id)
    rows = stream_state.load_recent_intervention_events(
        repo_root=root,
        limit=max(1, int(limit)),
        session_id=normalized_session,
    )
    normalized_host = _normalize_token(host_family)
    if normalized_host:
        rows = [
            row
            for row in rows
            if visibility_contract.event_host_family(row) == normalized_host
        ]

    confirmed_keys = {
        visibility_contract.event_confirmation_key(row)
        for row in rows
        if visibility_contract.event_chat_confirmed(row)
    }
    selected: list[dict[str, Any]] = []
    seen_keys: set[str] = set()
    live_count = 0
    ambient_count = 0
    assist_count = 0
    max_live = max(0, int(max_live_blocks))
    max_ambient = max(0, int(ambient_cap))

    for row in reversed(rows):
        if visibility_contract.event_chat_confirmed(row):
            continue
        display = visibility_contract.event_canonical_display_text(row)
        if not display:
            continue
        family = _family(row)
        if family == "other":
            continue
        if family == "teaser" and not include_teaser:
            continue
        if family == "assist" and not include_assist:
            continue
        key = visibility_contract.event_confirmation_key(row)
        if not key or key in confirmed_keys or key in seen_keys:
            continue
        if family == "assist":
            if assist_count >= 1:
                continue
            assist_count += 1
        else:
            if live_count >= max_live:
                continue
            if family == "ambient":
                if ambient_count >= max_ambient:
                    continue
                ambient_count += 1
            live_count += 1
        seen_keys.add(key)
        selected.append(_candidate_row(row, key=key, display=display))

    return list(reversed(selected))


def replayable_chat_markdown(
    *,
    repo_root: Path | str,
    host_family: str = "",
    session_id: str = "",
    limit: int = 200,
    max_live_blocks: int = 4,
    ambient_cap: int = 3,
    include_assist: bool = True,
    include_teaser: bool = False,
) -> str:
    blocks = replayable_chat_blocks(
        repo_root=repo_root,
        host_family=host_family,
        session_id=session_id,
        limit=limit,
        max_live_blocks=max_live_blocks,
        ambient_cap=ambient_cap,
        include_assist=include_assist,
        include_teaser=include_teaser,
    )
    return "\n\n".join(
        _normalize_block_string(row.get("display_markdown"))
        for row in blocks
        if _normalize_block_string(row.get("display_markdown"))
    ).strip()


__all__ = ["replayable_chat_blocks", "replayable_chat_markdown"]
