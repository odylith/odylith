"""System-status entrypoint rendering for the tooling dashboard shell."""

from __future__ import annotations

import html
from collections.abc import Callable, Mapping
from typing import Any


def _render_benchmark_story_html(payload: Mapping[str, Any]) -> str:
    benchmark_story = (
        dict(payload.get("benchmark_story", {}))
        if isinstance(payload.get("benchmark_story"), Mapping)
        else {}
    )
    if not bool(benchmark_story.get("show")):
        return ""
    metrics = benchmark_story.get("metrics")
    metric_cards = []
    if isinstance(metrics, list):
        for item in metrics[:4]:
            if not isinstance(item, Mapping):
                continue
            label = str(item.get("label", "")).strip()
            value = str(item.get("value", "")).strip()
            direction = str(item.get("direction", "")).strip().lower() or "unchanged"
            if not label or not value:
                continue
            metric_cards.append(
                '<article class="benchmark-story-metric">'
                f'<p class="benchmark-story-metric-label">{html.escape(label)}</p>'
                f'<p class="benchmark-story-metric-value benchmark-story-metric-value-{html.escape(direction)}">{html.escape(value)}</p>'
                f'<p class="benchmark-story-metric-direction">{html.escape(direction.title())}</p>'
                "</article>"
            )
    history_rows = []
    history = benchmark_story.get("history")
    if isinstance(history, list):
        for row in history[:4]:
            if not isinstance(row, Mapping):
                continue
            badge = str(row.get("badge", "")).strip() or "History"
            version = str(row.get("version", "")).strip() or "unknown"
            status = str(row.get("status", "")).strip() or "unknown"
            generated = str(row.get("generated_utc", "")).strip() or "unknown"
            history_rows.append(
                '<div class="benchmark-story-history-row">'
                f'<span class="benchmark-story-history-badge">{html.escape(badge)}</span>'
                f'<span class="benchmark-story-history-version">{html.escape(version)}</span>'
                f'<span class="benchmark-story-history-status">{html.escape(status)}</span>'
                f'<span class="benchmark-story-history-generated">{html.escape(generated)}</span>'
                "</div>"
            )
    summary = str(benchmark_story.get("summary", "")).strip() or "Benchmark compare summary unavailable."
    headline = str(benchmark_story.get("headline", "")).strip() or "Benchmark compare"
    status = str(benchmark_story.get("status", "")).strip().lower() or "unknown"
    return (
        '<section class="system-status-strip benchmark-story-strip" aria-label="Benchmark compare history">'
        '<article class="system-status-card benchmark-story-card">'
        f'<p class="system-status-label">Maintainer Benchmark Lane</p>'
        f'<p class="benchmark-story-headline">{html.escape(headline)}</p>'
        f'<p class="benchmark-story-summary benchmark-story-summary-{html.escape(status)}">{html.escape(summary)}</p>'
        '<div class="benchmark-story-metric-grid">'
        f'{"".join(metric_cards) if metric_cards else "<p class=\"telemetry-empty\">No benchmark deltas recorded yet.</p>"}'
        "</div>"
        '<div class="benchmark-story-history">'
        '<p class="benchmark-story-history-title">Recent benchmark history</p>'
        f'{"".join(history_rows) if history_rows else "<p class=\"telemetry-empty\">No benchmark history recorded yet.</p>"}'
        "</div>"
        "</article>"
        "</section>"
    )


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

    drawer_payload = (
        dict(payload.get("odylith_drawer", {}))
        if isinstance(payload.get("odylith_drawer"), Mapping)
        else build_drawer_payload(payload)
    )
    benchmark_story_html = _render_benchmark_story_html(payload)
    return benchmark_story_html + render_curated_system_status_html(drawer_payload)
