"""System-status entrypoint rendering for the tooling dashboard shell."""

from __future__ import annotations

import html
from collections.abc import Callable, Mapping
from typing import Any


def render_system_status_html(
    payload: Mapping[str, Any],
    *,
    odylith_switch: Mapping[str, Any],
    build_drawer_payload: Callable[[Mapping[str, Any]], dict[str, Any]],
    render_curated_system_status_html: Callable[[Mapping[str, Any]], str],
) -> str:
    """Render the shell system-status section from the current runtime payload."""

    if odylith_switch and not bool(odylith_switch.get("enabled", True)):
        meta_tokens = [
            f"source {str(odylith_switch.get('source', '')).strip() or 'default'}",
            f"mode {str(odylith_switch.get('mode', '')).strip() or 'disabled'}",
        ]
        note = str(odylith_switch.get("note", "")).strip()
        if note:
            meta_tokens.append(note)
        meta_html = "".join(
            f'<span class="system-status-meta">{html.escape(token)}</span>'
            for token in meta_tokens
            if str(token).strip()
        )
        return (
            '<section class="system-status-strip" aria-label="Shell ablation status">'
            '<article class="system-status-card">'
            '<p class="system-status-label">Ablation Mode</p>'
            '<p class="system-status-value">odylith disabled</p>'
            '<p class="system-status-copy">Odylith memory, optimization, registry composition, and packet handoff contracts are suppressed for comparison runs.</p>'
            f'<div class="system-status-meta-row">{meta_html}</div>'
            "</article>"
            "</section>"
        )

    return ""
