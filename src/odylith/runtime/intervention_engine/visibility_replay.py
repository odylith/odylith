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
from odylith.runtime.intervention_engine import visible_delivery_frontier
from odylith.runtime.intervention_engine import visibility_contract
from odylith.runtime.intervention_engine.visibility_contract import normalize_block_string as _normalize_block_string
from odylith.runtime.intervention_engine.visibility_contract import normalize_string as _normalize_string
from odylith.runtime.intervention_engine.visibility_contract import normalize_token as _normalize_token

_FAMILY_PRIORITY: dict[str, int] = {
    "ambient": 0,
    "intervention": 1,
    "teaser": 2,
    "assist": 3,
}
_AMBIENT_LABEL_PRIORITY: dict[str, int] = {
    "risks": 0,
    "history": 0,
    "insight": 1,
}


def _ambient_label_kind(row: Mapping[str, Any]) -> str:
    label_text = " ".join(
        _normalize_string(row.get(field)).lower()
        for field in ("display_markdown", "display_plain", "summary")
    )
    if "odylith risks" in label_text:
        return "risks"
    if "odylith history" in label_text:
        return "history"
    if "odylith insight" in label_text:
        return "insight"
    return "insight" if _family(row) == "ambient" else ""


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
        "ambient_label_kind": _ambient_label_kind(row),
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

    rows = visible_delivery_frontier.active_unconfirmed_rows(rows)
    if not rows:
        return []
    max_live = max(0, int(max_live_blocks))
    max_ambient = max(0, int(ambient_cap))
    deduped_rows: list[tuple[int, Mapping[str, Any]]] = []
    seen_keys: set[str] = set()
    for index, row in reversed(list(enumerate(rows))):
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
        if not key or key in seen_keys:
            continue
        seen_keys.add(key)
        deduped_rows.append((index, row))
    deduped_rows.reverse()

    ambient_rows = [(index, row) for index, row in deduped_rows if _family(row) == "ambient"]
    intervention_rows = [(index, row) for index, row in deduped_rows if _family(row) == "intervention"]
    teaser_rows = [(index, row) for index, row in deduped_rows if _family(row) == "teaser"]
    assist_rows = [(index, row) for index, row in deduped_rows if _family(row) == "assist"]

    if max_ambient >= 0:
        ambient_rows = ambient_rows[-max_ambient:] if max_ambient else []
    live_rows = [*ambient_rows, *intervention_rows, *teaser_rows]
    if max_live >= 0:
        live_rows = live_rows[-max_live:] if max_live else []
    assist_rows = assist_rows[-1:] if assist_rows else []

    selected_rows = sorted(
        [*live_rows, *assist_rows],
        key=lambda item: (
            _FAMILY_PRIORITY.get(_family(item[1]), 99),
            _AMBIENT_LABEL_PRIORITY.get(_ambient_label_kind(item[1]), 99) if _family(item[1]) == "ambient" else 0,
            item[0],
        ),
    )

    return [
        _candidate_row(
            row,
            key=visibility_contract.event_confirmation_key(row),
            display=visibility_contract.event_canonical_display_text(row),
        )
        for _, row in selected_rows
    ]


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
    displays: list[str] = []
    for row in blocks:
        display = _normalize_block_string(row.get("display_markdown"))
        if display:
            displays.append(display)
    return visibility_contract.compose_visible_markdown(*displays)


def preferred_replayable_chat_markdown(
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
    """Return the current unresolved replay bundle as one clean visible beat."""

    return replayable_chat_markdown(
        repo_root=repo_root,
        host_family=host_family,
        session_id=session_id,
        limit=limit,
        max_live_blocks=max_live_blocks,
        ambient_cap=ambient_cap,
        include_assist=include_assist,
        include_teaser=include_teaser,
    )


__all__ = [
    "preferred_replayable_chat_markdown",
    "replayable_chat_blocks",
    "replayable_chat_markdown",
]
