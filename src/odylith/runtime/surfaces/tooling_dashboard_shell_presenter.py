"""Build reusable template context for the tooling dashboard shell."""

from __future__ import annotations

import html
import math
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any

from odylith.runtime.governance import proof_state
from odylith.runtime.surfaces import dashboard_template_runtime
from odylith.runtime.surfaces import tooling_dashboard_cheatsheet_presenter
from odylith.runtime.surfaces import tooling_dashboard_execution_governance_presenter
from odylith.runtime.surfaces import tooling_dashboard_release_presenter
from odylith.runtime.surfaces import tooling_dashboard_system_status_presenter
from odylith.runtime.surfaces import tooling_dashboard_template_context
from odylith.runtime.surfaces import tooling_dashboard_welcome_presenter


@dataclass(frozen=True)
class MaintainerNote:
    note_id: str
    title: str
    recorded_at: str
    context: str
    section_title: str
    bullets: tuple[str, ...]


def _odylith_switch(payload: Mapping[str, Any]) -> dict[str, Any]:
    return dict(payload.get("odylith_switch", {})) if isinstance(payload.get("odylith_switch"), Mapping) else {}


def shell_case_preview_rows(case_queue: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Adapt Tribunal case rows into compact shell preview cards."""

    rows: list[dict[str, Any]] = []
    for index, case in enumerate(case_queue):
        if not isinstance(case, Mapping):
            continue
        headline = str(case.get("headline", "")).strip()
        brief = str(case.get("brief", "")).strip()
        decision = str(case.get("decision_at_stake", "")).strip()
        scope_key = str(case.get("scope_key", "")).strip()
        resolved_proof_state = proof_state.normalize_proof_state(case.get("proof_state", {}))
        proof_lines = proof_state.proof_preview_lines(resolved_proof_state, compact=True, limit=4)
        proof_reopen = (
            dict(case.get("proof_reopen", {}))
            if isinstance(case.get("proof_reopen"), Mapping)
            else {}
        )
        reopen_summary = str(proof_reopen.get("summary", "")).strip()
        if reopen_summary and reopen_summary not in proof_lines:
            proof_lines = [reopen_summary, *proof_lines][:4]
        proof_state_resolution = (
            dict(case.get("proof_state_resolution", {}))
            if isinstance(case.get("proof_state_resolution"), Mapping)
            else {}
        )
        if not proof_lines:
            resolution_message = proof_state.proof_resolution_message(proof_state_resolution)
            if resolution_message:
                proof_lines = [resolution_message]
        claim_guard = (
            dict(case.get("claim_guard", {}))
            if isinstance(case.get("claim_guard"), Mapping)
            else {}
        )
        if not scope_key or not headline:
            continue
        rows.append(
            {
                "id": str(case.get("id", "")).strip() or f"case-{index + 1}",
                "rank": int(case.get("rank", index + 1) or (index + 1)),
                "count_label": f"#{int(case.get('rank', index + 1) or (index + 1))}",
                "severity_label": str(case.get("action_label", "")).strip() or "Review manually",
                "primary_scope_key": scope_key,
                "primary_scope_id": str(case.get("scope_id", "")).strip(),
                "title": headline,
                "summary": brief,
                "start_here": decision or brief,
                "start_here_short": decision or brief,
                "proof_state": resolved_proof_state,
                "proof_state_resolution": proof_state_resolution,
                "claim_guard": claim_guard,
                "proof_reopen": proof_reopen,
                "proof_lines": proof_lines,
                "proof_claim": str(claim_guard.get("highest_truthful_claim", "")).strip(),
            }
        )
    return rows


def _default_maintainer_notes() -> tuple[MaintainerNote, ...]:
    return ()


def _coerce_maintainer_notes(payload: Mapping[str, Any]) -> tuple[MaintainerNote, ...]:
    raw_notes = payload.get("maintainer_notes")
    if not isinstance(raw_notes, Sequence) or isinstance(raw_notes, (str, bytes, bytearray)):
        return ()
    notes: list[MaintainerNote] = []
    for index, raw_note in enumerate(raw_notes, start=1):
        if not isinstance(raw_note, Mapping):
            continue
        title = str(raw_note.get("title", "")).strip()
        if not title:
            continue
        bullets_value = raw_note.get("bullets", ())
        bullets: tuple[str, ...] = ()
        if isinstance(bullets_value, Sequence) and not isinstance(bullets_value, (str, bytes, bytearray)):
            bullets = tuple(str(item).strip() for item in bullets_value if str(item).strip())
        notes.append(
            MaintainerNote(
                note_id=str(raw_note.get("note_id", "")).strip() or f"N-{index:03d}",
                title=title,
                recorded_at=str(raw_note.get("recorded_at", "")).strip() or "unknown",
                context=str(raw_note.get("context", "")).strip() or "No developer context recorded.",
                section_title=str(raw_note.get("section_title", "")).strip() or "Pending",
                bullets=bullets,
            )
        )
    return tuple(notes)


def _render_maintainer_notes_html(notes: Sequence[MaintainerNote]) -> str:
    cards = []
    for note in notes:
        bullets_html = "".join(
            f"<li>{html.escape(bullet)}</li>"
            for bullet in note.bullets
        )
        cards.append(
            (
                '<article class="maintainer-note-card" role="listitem">'
                '<div class="maintainer-note-head">'
                f'<span class="maintainer-note-id">{html.escape(note.note_id)}</span>'
                f'<h3 class="maintainer-note-title">{html.escape(note.title)}</h3>'
                "</div>"
                '<div class="maintainer-note-meta">'
                f'<p><strong>Recorded</strong> {html.escape(note.recorded_at)}</p>'
                f'<p><strong>Context</strong> {html.escape(note.context)}</p>'
                "</div>"
                '<div class="maintainer-note-section">'
                f'<p class="maintainer-note-section-title">{html.escape(note.section_title)}</p>'
                f'<ul class="maintainer-note-bullets">{bullets_html}</ul>'
                "</div>"
                "</article>"
            )
        )
    if not cards:
        cards.append(
            (
                '<article class="maintainer-note-card maintainer-note-card-empty" role="listitem">'
                '<div class="maintainer-note-head">'
                '<span class="maintainer-note-id">N-000</span>'
                '<h3 class="maintainer-note-title">No developer notes recorded</h3>'
                "</div>"
                '<p class="maintainer-note-empty-copy">'
                "Add a source-owned developer note before relying on the shell drawer for platform context."
                "</p>"
                "</article>"
            )
        )
    return '<section class="maintainer-note-list" aria-label="Developer notes">' + "".join(cards) + "</section>"


def _render_release_spotlight_html(payload: Mapping[str, Any]) -> str:
    return tooling_dashboard_release_presenter.render_release_spotlight_html(payload)


def _render_welcome_state_html(payload: Mapping[str, Any]) -> str:
    return tooling_dashboard_welcome_presenter.render_welcome_state_html(payload)


def _safe_ratio_percent(value: Any) -> float:
    return max(0.0, min(100.0, _safe_float(value, 0.0, minimum=0.0, maximum=1.0) * 100.0))


def _safe_score_percent(value: Any) -> float:
    return max(0.0, min(100.0, _safe_float(value, 0.0, minimum=0.0, maximum=100.0)))


def _format_percent(value: Any) -> str:
    return f"{_safe_ratio_percent(value):.1f}%"


def _format_score(value: Any) -> str:
    return f"{_safe_float(value, 0.0, minimum=0.0, maximum=100.0):.1f}"


def _format_timestamp_utc(value: Any) -> str:
    token = str(value or "").strip()
    if not token:
        return "unknown"
    normalized = token.replace("Z", "+00:00") if token.endswith("Z") else token
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return token
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def _format_bytes(value: Any) -> str:
    size = _safe_float(value, 0.0, minimum=0.0)
    if size >= 1024**3:
        return f"{size / (1024**3):.1f} GB"
    if size >= 1024**2:
        return f"{size / (1024**2):.1f} MB"
    if size >= 1024:
        return f"{size / 1024:.1f} KB"
    return f"{_safe_int(size, minimum=0)} B"


def _format_latency_ms(value: Any) -> str:
    latency = _safe_float(value, 0.0, minimum=0.0, maximum=300000.0)
    if latency >= 100.0:
        return f"{latency:.0f} ms"
    if latency >= 10.0:
        return f"{latency:.1f} ms"
    return f"{latency:.2f} ms"


def _safe_float(value: Any, default: float = 0.0, *, minimum: float | None = None, maximum: float | None = None) -> float:
    try:
        numeric = float(value or 0.0)
    except (TypeError, ValueError):
        numeric = float(default)
    if math.isnan(numeric):
        numeric = float(default)
    elif math.isinf(numeric):
        if numeric > 0 and maximum is not None:
            numeric = float(maximum)
        elif numeric < 0 and minimum is not None:
            numeric = float(minimum)
        else:
            numeric = float(default)
    if minimum is not None:
        numeric = max(float(minimum), numeric)
    if maximum is not None:
        numeric = min(float(maximum), numeric)
    return numeric


def _safe_int(
    value: Any,
    default: int = 0,
    *,
    minimum: int | None = None,
    maximum: int | None = None,
) -> int:
    try:
        numeric_float = float(value or 0)
        if math.isnan(numeric_float):
            raise ValueError("non-finite numeric value")
        if math.isinf(numeric_float):
            if numeric_float > 0 and maximum is not None:
                return int(maximum)
            if numeric_float < 0 and minimum is not None:
                return int(minimum)
            raise ValueError("non-finite numeric value")
        numeric = int(round(numeric_float))
    except (TypeError, ValueError, OverflowError):
        numeric = int(default)
    if minimum is not None:
        numeric = max(int(minimum), numeric)
    if maximum is not None:
        numeric = min(int(maximum), numeric)
    return numeric


def _normalized_count_map(
    value: Any,
    *,
    maximum: int = 1_000_000,
) -> dict[str, int]:
    raw_map = dict(value) if isinstance(value, Mapping) else {}
    normalized: dict[str, int] = {}
    for raw_label, raw_count in raw_map.items():
        label = str(raw_label or "").strip()
        if not label:
            continue
        normalized[label] = _safe_int(raw_count, minimum=0, maximum=maximum)
    return normalized


def _distribution_rows_from_counts(
    counts: Mapping[str, Any] | Any,
    *,
    denominator: int | None = None,
) -> list[tuple[str, str, float]]:
    normalized = _normalized_count_map(counts)
    if denominator is None:
        scale_max = max(normalized.values(), default=1)
    else:
        scale_max = max(1, _safe_int(denominator, minimum=1))
    return [
        (
            _humanize_display(label, title_case=True),
            str(count),
            (float(count) / float(scale_max)) * 100.0 if scale_max else 0.0,
        )
        for label, count in normalized.items()
    ]


def _parse_timestamp_utc(value: Any) -> datetime | None:
    token = str(value or "").strip()
    if not token:
        return None
    normalized = token.replace("Z", "+00:00") if token.endswith("Z") else token
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _compact_unique_text(items: Sequence[Any], *, limit: int = 3, title_case: bool = False) -> list[str]:
    seen: set[str] = set()
    compacted: list[str] = []
    for raw in items:
        token = str(raw or "").strip()
        if not token:
            continue
        normalized = token.lower()
        if normalized in seen:
            continue
        seen.add(normalized)
        compacted.append(_humanize_display(token, title_case=title_case) if title_case else token)
        if len(compacted) >= max(1, int(limit)):
            break
    return compacted


def _odylith_freshness_posture(
    *,
    snapshot_time: Any,
    event_times: Sequence[Any],
) -> dict[str, Any]:
    candidate_times = [dt for dt in [_parse_timestamp_utc(snapshot_time), *(_parse_timestamp_utc(item) for item in event_times)] if dt is not None]
    if not candidate_times:
        return {
            "level": "unknown",
            "label": "Unknown",
            "age_minutes": None,
            "note": "No recent Odylith snapshot or history timestamp was available.",
        }
    newest = max(candidate_times)
    age_minutes = max(0.0, (datetime.now(timezone.utc) - newest).total_seconds() / 60.0)
    if age_minutes <= 30.0:
        level = "fresh"
        note = "Recent Odylith telemetry is current enough to guide shell decisions confidently."
    elif age_minutes <= 180.0:
        level = "warming"
        note = "Telemetry is present but no longer near-live; trend is still useful."
    elif age_minutes <= 1440.0:
        level = "stale"
        note = "Telemetry is aging out; use current shell posture with caution."
    else:
        level = "cold"
        note = "Only old Odylith telemetry is available; treat trend visuals as archival context."
    return {
        "level": level,
        "label": _humanize_display(level, title_case=True) or "Unknown",
        "age_minutes": round(age_minutes, 1),
        "note": note,
    }


def _odylith_signal_posture(
    *,
    packet_count: int,
    router_count: int,
    orchestration_count: int,
    timing_count: int,
) -> dict[str, Any]:
    total = max(0, int(packet_count)) + max(0, int(router_count)) + max(0, int(orchestration_count)) + max(0, int(timing_count))
    if total <= 0:
        level = "empty"
        note = "No recent Odylith history is available beyond the current snapshot."
    elif packet_count >= 4 and total >= 18 and (router_count >= 3 or orchestration_count >= 3):
        level = "rich"
        note = "Recent packet, router, orchestration, and timing signal is deep enough for trend-heavy interpretation."
    elif packet_count >= 2 and total >= 8:
        level = "usable"
        note = "Recent signal is present and bounded; trend views are informative but not exhaustive."
    else:
        level = "sparse"
        note = "Recent signal is thin; emphasize the current snapshot over the trend visuals."
    return {
        "level": level,
        "label": _humanize_display(level, title_case=True) or "Unknown",
        "total_events": total,
        "note": note,
    }


def _humanize_token(value: Any) -> str:
    token = str(value or "").strip()
    if not token:
        return ""
    return token.replace("_", " ")


def _humanize_display(value: Any, *, title_case: bool = False) -> str:
    token = _humanize_token(value)
    if not token:
        return ""
    return token.title() if title_case else token


def _display_list_text(items: Sequence[str]) -> str:
    cleaned = [item.strip() for item in items if item.strip()]
    if not cleaned:
        return ""
    if len(cleaned) == 1:
        return cleaned[0]
    return ", ".join(cleaned[:-1]) + f", and {cleaned[-1]}"


def _sparkline_points(
    values: Sequence[Any],
    *,
    width: float = 320.0,
    height: float = 188.0,
    left: float = 18.0,
    right: float = 10.0,
    top: float = 16.0,
    bottom: float = 22.0,
    max_value: float = 100.0,
) -> list[tuple[float, float] | None]:
    usable_max = max(1.0, float(max_value))
    inner_width = max(8.0, width - left - right)
    inner_height = max(8.0, height - top - bottom)
    cleaned = []
    for raw in values:
        if raw is None:
            cleaned.append(None)
        else:
            cleaned.append(_safe_float(raw, 0.0, minimum=0.0, maximum=usable_max))
    if len(cleaned) == 1:
        value = cleaned[0]
        return [None if value is None else (left + inner_width / 2.0, top + inner_height - ((value / usable_max) * inner_height))]
    points: list[tuple[float, float] | None] = []
    step = inner_width / max(1, len(cleaned) - 1)
    for index, value in enumerate(cleaned):
        if value is None:
            points.append(None)
            continue
        x = left + (step * index)
        y = top + inner_height - ((value / usable_max) * inner_height)
        points.append((round(x, 2), round(y, 2)))
    return points


def _svg_path_from_points(points: Sequence[tuple[float, float] | None]) -> str:
    parts: list[str] = []
    pen_down = False
    for point in points:
        if point is None:
            pen_down = False
            continue
        x, y = point
        parts.append(("L" if pen_down else "M") + f"{x:.2f},{y:.2f}")
        pen_down = True
    return " ".join(parts)


def _render_odylith_chart_legend(items: Sequence[tuple[str, str]]) -> str:
    rendered = []
    for label, color in items:
        token = str(label or "").strip()
        tone = str(color or "").strip()
        if not token or not tone:
            continue
        rendered.append(
            '<span class="odylith-chart-legend-item">'
            f'<span class="odylith-chart-legend-swatch" style="background: {html.escape(tone)};"></span>'
            f'<span>{html.escape(token)}</span>'
            "</span>"
        )
    return '<div class="odylith-chart-legend">' + "".join(rendered) + "</div>" if rendered else ""


def _render_odylith_line_chart_svg(
    *,
    series: Sequence[tuple[str, Sequence[Any], str]],
    max_value: float,
    caption: str,
) -> str:
    width = 320.0
    height = 188.0
    inner_top = 16.0
    inner_bottom = 22.0
    inner_left = 18.0
    inner_right = 10.0
    grid_y = [inner_top, inner_top + ((height - inner_top - inner_bottom) / 2.0), height - inner_bottom]
    grid = "".join(
        f'<line x1="{inner_left:.0f}" y1="{y:.2f}" x2="{width - inner_right:.0f}" y2="{y:.2f}" class="odylith-chart-grid-line" />'
        for y in grid_y
    )
    paths: list[str] = []
    legend: list[tuple[str, str]] = []
    for label, values, color in series:
        points = _sparkline_points(values, width=width, height=height, left=inner_left, right=inner_right, top=inner_top, bottom=inner_bottom, max_value=max_value)
        path = _svg_path_from_points(points)
        if path:
            paths.append(f'<path d="{path}" fill="none" stroke="{html.escape(color)}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" />')
            for point in points:
                if point is None:
                    continue
                paths.append(
                    f'<circle cx="{point[0]:.2f}" cy="{point[1]:.2f}" r="3.1" fill="{html.escape(color)}" stroke="#f8fbff" stroke-width="1.2" />'
                )
        legend.append((label, color))
    svg = (
        f'<svg class="odylith-chart-svg" viewBox="0 0 {int(width)} {int(height)}" aria-hidden="true" focusable="false">'
        f'{grid}{"".join(paths)}'
        "</svg>"
    )
    return (
        '<div class="odylith-chart-fallback">'
        f"{svg}"
        f'{_render_odylith_chart_legend(legend)}'
        f'<p class="odylith-chart-fallback-copy">{html.escape(caption)}</p>'
        "</div>"
    )


def _render_odylith_bar_line_chart_svg(
    *,
    bars: Sequence[Any],
    lines: Sequence[tuple[str, Sequence[Any], str]],
    caption: str,
) -> str:
    width = 320.0
    height = 188.0
    left = 18.0
    right = 10.0
    top = 16.0
    bottom = 22.0
    inner_width = width - left - right
    inner_height = height - top - bottom
    normalized_bars = [_safe_float(item, 0.0, minimum=0.0) for item in bars]
    max_bar = max(max(normalized_bars, default=0.0), 1.0)
    bar_count = max(1, len(normalized_bars))
    slot_width = inner_width / float(bar_count)
    bar_width = max(8.0, min(18.0, slot_width * 0.56))
    bar_rects = []
    for index, value in enumerate(normalized_bars):
        bar_height = (value / max_bar) * inner_height
        x = left + (slot_width * index) + ((slot_width - bar_width) / 2.0)
        y = top + inner_height - bar_height
        bar_rects.append(
            f'<rect x="{x:.2f}" y="{y:.2f}" width="{bar_width:.2f}" height="{bar_height:.2f}" rx="5" fill="rgba(251, 113, 133, 0.78)" />'
        )
    overlay = _render_odylith_line_chart_svg(series=lines, max_value=100.0, caption=caption)
    svg_match_start = overlay.find("<svg")
    svg_match_end = overlay.find("</svg>")
    legend_start = overlay.find('<div class="odylith-chart-legend">')
    legend_end = overlay.find("</div>", legend_start)
    copy_start = overlay.find('<p class="odylith-chart-fallback-copy">')
    line_svg = overlay[svg_match_start:svg_match_end + len("</svg>")] if svg_match_start >= 0 and svg_match_end >= 0 else ""
    legend_html = overlay[legend_start:legend_end + len("</div>")] if legend_start >= 0 and legend_end >= 0 else ""
    copy_end = overlay.find("</p>", copy_start) if copy_start >= 0 else -1
    copy_html = overlay[copy_start:copy_end + len("</p>")] if copy_start >= 0 and copy_end >= 0 else ""
    grid = "".join(
        f'<line x1="{left:.0f}" y1="{y:.2f}" x2="{width - right:.0f}" y2="{y:.2f}" class="odylith-chart-grid-line" />'
        for y in (top, top + (inner_height / 2.0), height - bottom)
    )
    base_svg = (
        f'<svg class="odylith-chart-svg" viewBox="0 0 {int(width)} {int(height)}" aria-hidden="true" focusable="false">'
        f"{grid}{''.join(bar_rects)}"
        "</svg>"
    )
    if line_svg:
        combined_svg = base_svg.replace("</svg>", "") + line_svg[line_svg.find(">") + 1 : line_svg.rfind("</svg>")] + "</svg>"
    else:
        combined_svg = base_svg
    return (
        '<div class="odylith-chart-fallback">'
        f"{combined_svg}"
        f"{legend_html}"
        f"{copy_html or f'<p class=\"odylith-chart-fallback-copy\">{html.escape(caption)}</p>'}"
        "</div>"
    )


def _render_odylith_control_story_trend_fallback(
    *,
    labels: Sequence[Any],
    bars: Sequence[Any],
    signal_series: Sequence[tuple[str, Sequence[Any], str]],
    caption: str,
) -> str:
    width = 320.0
    spend_height = 86.0
    signal_height = 118.0
    left = 18.0
    right = 10.0
    spend_top = 12.0
    spend_bottom = 16.0
    signal_top = 12.0
    signal_bottom = 20.0
    cleaned_labels = [str(label or "").strip() or f"P{index + 1}" for index, label in enumerate(labels)]
    normalized_bars = [_safe_float(item, 0.0, minimum=0.0) for item in bars]
    if len(normalized_bars) < len(cleaned_labels):
        normalized_bars.extend([0.0] * (len(cleaned_labels) - len(normalized_bars)))
    cleaned_bars = normalized_bars[: len(cleaned_labels)] or [0.0]
    slot_width = (width - left - right) / float(max(1, len(cleaned_bars)))
    bar_width = max(8.0, min(18.0, slot_width * 0.54))
    spend_grid_y = (
        spend_top,
        spend_top + ((spend_height - spend_top - spend_bottom) / 2.0),
        spend_height - spend_bottom,
    )
    spend_grid = "".join(
        f'<line x1="{left:.0f}" y1="{y:.2f}" x2="{width - right:.0f}" y2="{y:.2f}" class="odylith-chart-grid-line" />'
        for y in spend_grid_y
    )
    max_bar = max(max(cleaned_bars, default=0.0), 1.0)
    spend_bars = []
    for index, value in enumerate(cleaned_bars):
        bar_height = (value / max_bar) * (spend_height - spend_top - spend_bottom)
        x = left + (slot_width * index) + ((slot_width - bar_width) / 2.0)
        y = spend_top + (spend_height - spend_top - spend_bottom) - bar_height
        spend_bars.append(
            f'<rect x="{x:.2f}" y="{y:.2f}" width="{bar_width:.2f}" height="{bar_height:.2f}" rx="5" fill="rgba(251, 113, 133, 0.82)" />'
        )
    spend_svg = (
        f'<svg class="odylith-chart-svg" viewBox="0 0 {int(width)} {int(spend_height)}" aria-hidden="true" focusable="false">'
        f"{spend_grid}{''.join(spend_bars)}"
        "</svg>"
    )

    signal_grid_y = (
        signal_top,
        signal_top + ((signal_height - signal_top - signal_bottom) / 2.0),
        signal_height - signal_bottom,
    )
    signal_grid = "".join(
        f'<line x1="{left:.0f}" y1="{y:.2f}" x2="{width - right:.0f}" y2="{y:.2f}" class="odylith-chart-grid-line" />'
        for y in signal_grid_y
    )
    signal_paths: list[str] = []
    legend: list[tuple[str, str]] = []
    for label, values, color in signal_series:
        points = _sparkline_points(
            values,
            width=width,
            height=signal_height,
            left=left,
            right=right,
            top=signal_top,
            bottom=signal_bottom,
            max_value=100.0,
        )
        path = _svg_path_from_points(points)
        if path:
            signal_paths.append(
                f'<path d="{path}" fill="none" stroke="{html.escape(color)}" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" />'
            )
            for point in points:
                if point is None:
                    continue
                signal_paths.append(
                    f'<circle cx="{point[0]:.2f}" cy="{point[1]:.2f}" r="2.9" fill="{html.escape(color)}" stroke="#f8fbff" stroke-width="1.2" />'
                )
        legend.append((label, color))
    signal_svg = (
        f'<svg class="odylith-chart-svg" viewBox="0 0 {int(width)} {int(signal_height)}" aria-hidden="true" focusable="false">'
        f'{signal_grid}{"".join(signal_paths)}'
        "</svg>"
    )
    return (
        '<div class="odylith-chart-fallback odylith-chart-fallback-split">'
        '<div class="odylith-chart-fallback-panel">'
        '<p class="odylith-chart-fallback-panel-label">Spend</p>'
        f"{spend_svg}"
        '</div>'
        '<div class="odylith-chart-fallback-panel">'
        '<p class="odylith-chart-fallback-panel-label">Outcome signals</p>'
        f"{signal_svg}"
        f"{_render_odylith_chart_legend(legend)}"
        '</div>'
        f'<p class="odylith-chart-fallback-copy">{html.escape(caption)}</p>'
        '</div>'
    )


def _render_odylith_control_story_snapshot_fallback(
    *,
    detail: Mapping[str, Any],
    caption: str,
) -> str:
    label = str(detail.get("label", "")).strip() or "Latest"
    tokens = _safe_int(detail.get("tokens", 0), minimum=0, maximum=250000)
    budget_state = str(detail.get("budget_state", "")).strip() or "Budget unknown"
    packet_state = str(detail.get("state", "")).strip() or "Unknown"
    recorded_at = str(detail.get("recorded_at", "")).strip()
    workstream = str(detail.get("workstream", "")).strip()
    session_id = str(detail.get("session_id", "")).strip()
    meta_tokens = [token for token in (recorded_at, workstream and f"WS {workstream}", session_id and f"Session {session_id}") if token]
    snapshot_meta = " · ".join(meta_tokens) or "Single routed slice available."
    metric_rows = "".join(
        _telemetry_meter_html(
            label=metric_label,
            value_text=f"{metric_value:.0f}%",
            percent=metric_value,
            accent=metric_accent,
        )
        for metric_label, metric_value, metric_accent in (
            ("Budget fit", _safe_float(detail.get("budget_fit", 0.0), minimum=0.0, maximum=100.0), "#2dd4bf"),
            ("Utility", _safe_float(detail.get("utility", 0.0), minimum=0.0, maximum=100.0), "#2dd4bf"),
            ("Alignment", _safe_float(detail.get("alignment", 0.0), minimum=0.0, maximum=100.0), "#60a5fa"),
            ("Yield", _safe_float(detail.get("yield", 0.0), minimum=0.0, maximum=100.0), "#f59e0b"),
            ("Route ready", _safe_float(detail.get("route_ready", 0.0), minimum=0.0, maximum=100.0), "#38bdf8"),
        )
    )
    return (
        '<div class="odylith-chart-fallback odylith-chart-fallback-snapshot">'
        '<div class="odylith-chart-snapshot-head">'
        f'<p class="odylith-chart-snapshot-title">{html.escape(f"{tokens:,} tokens")}</p>'
        f'<p class="odylith-chart-snapshot-subtitle">{html.escape(f"{label} · {budget_state} · {packet_state}")}</p>'
        f'<p class="odylith-chart-snapshot-meta">{html.escape(snapshot_meta)}</p>'
        '</div>'
        f'<div class="odylith-chart-snapshot-meters">{metric_rows}</div>'
        f'<p class="odylith-chart-fallback-copy">{html.escape(caption)}</p>'
        '</div>'
    )


def _render_odylith_donut_chart_svg(
    *,
    labels: Sequence[Any],
    values: Sequence[Any],
    colors: Sequence[str],
    caption: str,
) -> str:
    radius = 42.0
    cx = 96.0
    cy = 86.0
    circumference = 2.0 * math.pi * radius
    cleaned_labels = [str(label or "").strip() for label in labels if str(label or "").strip()]
    cleaned_values = [_safe_float(value, 0.0, minimum=0.0) for value in values[: len(cleaned_labels)]]
    total = sum(cleaned_values)
    if total <= 0.0 or not cleaned_labels:
        cleaned_labels = ["No recent execution"]
        cleaned_values = [1.0]
    rings = []
    offset = 0.0
    legend: list[tuple[str, str]] = []
    palette = list(colors) or ["#7dd3fc"]
    for index, label in enumerate(cleaned_labels):
        color = palette[index % len(palette)]
        portion = max(0.0, cleaned_values[index]) / max(1.0, sum(cleaned_values))
        segment = circumference * portion
        rings.append(
            f'<circle cx="{cx:.0f}" cy="{cy:.0f}" r="{radius:.0f}" fill="none" stroke="{html.escape(color)}" stroke-width="22" '
            f'stroke-linecap="butt" stroke-dasharray="{segment:.2f} {circumference - segment:.2f}" stroke-dashoffset="{-offset:.2f}" '
            f'transform="rotate(-90 {cx:.0f} {cy:.0f})" />'
        )
        offset += segment
        legend.append((label, color))
    svg = (
        '<svg class="odylith-chart-svg odylith-chart-svg-donut" viewBox="0 0 192 188" aria-hidden="true" focusable="false">'
        f'<circle cx="{cx:.0f}" cy="{cy:.0f}" r="{radius:.0f}" fill="none" stroke="rgba(148, 163, 184, 0.18)" stroke-width="22" />'
        f'{"".join(rings)}'
        f'<text x="{cx:.0f}" y="{cy - 2:.0f}" text-anchor="middle" class="odylith-chart-center-label">{len(cleaned_labels)}</text>'
        f'<text x="{cx:.0f}" y="{cy + 16:.0f}" text-anchor="middle" class="odylith-chart-center-subtitle">profiles</text>'
        "</svg>"
    )
    return (
        '<div class="odylith-chart-fallback">'
        f"{svg}"
        f"{_render_odylith_chart_legend(legend)}"
        f'<p class="odylith-chart-fallback-copy">{html.escape(caption)}</p>'
        "</div>"
    )


def _render_odylith_radar_chart_svg(
    *,
    labels: Sequence[Any],
    values: Sequence[Any],
    caption: str,
) -> str:
    center_x = 160.0
    center_y = 88.0
    radius = 60.0
    cleaned_labels = [str(label or "").strip() or f"S{index + 1}" for index, label in enumerate(labels[:6])]
    if not cleaned_labels:
        cleaned_labels = ["Density", "Readiness", "Diversity", "Budget", "Coverage", "Satisfaction"]
    cleaned_values = [_safe_float(value, 0.0, minimum=0.0, maximum=100.0) for value in values[: len(cleaned_labels)]]
    if len(cleaned_values) < len(cleaned_labels):
        cleaned_values.extend([0.0] * (len(cleaned_labels) - len(cleaned_values)))

    def _polygon(scale: float) -> str:
        coords = []
        for index in range(len(cleaned_labels)):
            angle = ((math.pi * 2.0) / float(len(cleaned_labels))) * index - (math.pi / 2.0)
            coords.append(
                f"{center_x + math.cos(angle) * radius * scale:.2f},{center_y + math.sin(angle) * radius * scale:.2f}"
            )
        return " ".join(coords)

    data_points = []
    axis_lines = []
    for index, value in enumerate(cleaned_values):
        angle = ((math.pi * 2.0) / float(len(cleaned_labels))) * index - (math.pi / 2.0)
        axis_x = center_x + math.cos(angle) * radius
        axis_y = center_y + math.sin(angle) * radius
        axis_lines.append(
            f'<line x1="{center_x:.2f}" y1="{center_y:.2f}" x2="{axis_x:.2f}" y2="{axis_y:.2f}" class="odylith-chart-grid-line" />'
        )
        data_points.append(
            f"{center_x + math.cos(angle) * radius * (value / 100.0):.2f},{center_y + math.sin(angle) * radius * (value / 100.0):.2f}"
        )
    svg = (
        '<svg class="odylith-chart-svg" viewBox="0 0 320 188" aria-hidden="true" focusable="false">'
        f'<polygon points="{_polygon(1.0)}" fill="rgba(191, 219, 254, 0.14)" stroke="rgba(148, 163, 184, 0.24)" stroke-width="1" />'
        f'<polygon points="{_polygon(0.66)}" fill="rgba(191, 219, 254, 0.10)" stroke="rgba(148, 163, 184, 0.18)" stroke-width="1" />'
        f'<polygon points="{_polygon(0.33)}" fill="rgba(191, 219, 254, 0.06)" stroke="rgba(148, 163, 184, 0.12)" stroke-width="1" />'
        f'{"".join(axis_lines)}'
        f'<polygon points="{" ".join(data_points)}" fill="rgba(125, 211, 252, 0.24)" stroke="#7dd3fc" stroke-width="2.2" />'
        "</svg>"
    )
    return (
        '<div class="odylith-chart-fallback">'
        f"{svg}"
        f"{_render_odylith_chart_legend(tuple((label, '#7dd3fc') for label in cleaned_labels))}"
        f'<p class="odylith-chart-fallback-copy">{html.escape(caption)}</p>'
        "</div>"
    )


def _render_odylith_chart_canvas(
    *,
    chart_key: str,
    aria_label: str,
    fallback_html: str,
) -> str:
    return (
        f'<div class="odylith-chart-canvas" data-odylith-chart="{html.escape(chart_key)}" '
        f'aria-label="{html.escape(aria_label)}">{fallback_html}</div>'
    )


def _tooltip_attrs(tooltip: str = "", *, aria_label: str = "") -> str:
    tooltip_text = str(tooltip or "").strip()
    if not tooltip_text:
        return ""
    aria_text = str(aria_label or "").strip() or tooltip_text
    return (
        f' data-tooltip="{html.escape(tooltip_text, quote=True)}"'
        f' aria-label="{html.escape(aria_text, quote=True)}"'
    )


def _token_label_html(
    *,
    css_class: str,
    text: str,
    tooltip: str = "",
    aria_label: str = "",
) -> str:
    return f'<span class="{css_class}"{_tooltip_attrs(tooltip, aria_label=aria_label)}>{html.escape(text)}</span>'


def _telemetry_gauge_html(*, label: str, value_text: str, percent: float, accent: str, note: str = "") -> str:
    note_html = f'<p class="telemetry-gauge-note">{html.escape(note)}</p>' if note else ""
    return (
        '<div class="telemetry-gauge" '
        f'style="--telemetry-value: {max(0.0, min(100.0, percent)):.1f}; --telemetry-accent: {accent};">'
        '<div class="telemetry-gauge-ring">'
        '<div class="telemetry-gauge-core">'
        f'<span class="telemetry-gauge-value">{html.escape(value_text)}</span>'
        f'<span class="telemetry-gauge-label">{html.escape(label)}</span>'
        '</div>'
        '</div>'
        f'{note_html}'
        '</div>'
    )


def _telemetry_stat_card_html(
    *,
    label: str,
    value_text: str,
    note: str,
    meter_percent: float | None = None,
    accent: str = "#2563eb",
    mono_value: bool = False,
) -> str:
    value_class = "telemetry-stat-value telemetry-stat-value-mono" if mono_value else "telemetry-stat-value"
    meter_html = ""
    if meter_percent is not None:
        safe_percent = max(0.0, min(100.0, meter_percent))
        meter_html = (
            '<span class="telemetry-stat-meter">'
            f'<span class="telemetry-stat-meter-fill" style="width: {safe_percent:.1f}%; background: {accent};"></span>'
            '</span>'
        )
    return (
        '<article class="telemetry-stat-card">'
        f'<p class="telemetry-stat-label">{html.escape(label)}</p>'
        f'<p class="{value_class}">{html.escape(value_text)}</p>'
        f'<p class="telemetry-stat-note">{html.escape(note)}</p>'
        f"{meter_html}"
        "</article>"
    )


def _telemetry_meter_html(*, label: str, value_text: str, percent: float, accent: str) -> str:
    safe_percent = max(0.0, min(100.0, percent))
    return (
        '<div class="telemetry-meter-row">'
        '<div class="telemetry-meter-copy">'
        f'<span class="telemetry-meter-label">{html.escape(label)}</span>'
        f'<span class="telemetry-meter-value">{html.escape(value_text)}</span>'
        '</div>'
        '<span class="telemetry-meter-bar">'
        f'<span class="telemetry-meter-fill" style="width: {safe_percent:.1f}%; background: {accent};"></span>'
        '</span>'
        '</div>'
    )


def _telemetry_distribution_html(*, title: str, items: Sequence[tuple[str, str, float]], accent: str) -> str:
    rows = []
    for label, value_text, percent in items:
        safe_percent = max(0.0, min(100.0, percent))
        rows.append(
            '<div class="telemetry-distribution-row">'
            f'<span class="telemetry-distribution-label">{html.escape(label)}</span>'
            '<span class="telemetry-distribution-bar">'
            f'<span class="telemetry-distribution-fill" style="width: {safe_percent:.1f}%; background: {accent};"></span>'
            '</span>'
            f'<span class="telemetry-distribution-value">{html.escape(value_text)}</span>'
            '</div>'
        )
    if not rows:
        rows.append('<p class="telemetry-empty">No telemetry recorded yet.</p>')
    return (
        '<section class="telemetry-section">'
        f'<p class="telemetry-section-title">{html.escape(title)}</p>'
        '<div class="telemetry-distribution-list">'
        + "".join(rows)
        + '</div></section>'
    )


def _telemetry_recommendations_html(title: str, recommendations: Sequence[Any]) -> str:
    items = []
    for item in recommendations:
        token = str(item).strip()
        if not token:
            continue
        if "_" in token and " " not in token:
            token = _humanize_display(token, title_case=True)
        items.append(token)
    if not items:
        return (
            '<section class="telemetry-section">'
            f'<p class="telemetry-section-title">{html.escape(title)}</p>'
            '<p class="telemetry-empty">No recommendations recorded.</p>'
            '</section>'
        )
    bullets = "".join(f'<li>{html.escape(item)}</li>' for item in items[:3])
    return (
        '<section class="telemetry-section">'
        f'<p class="telemetry-section-title">{html.escape(title)}</p>'
        f'<ul class="telemetry-bullet-list">{bullets}</ul>'
        '</section>'
    )


def _telemetry_capabilities_html(capabilities: Mapping[str, Any]) -> str:
    ordered = (
        (
            "Exact lookup",
            bool(capabilities.get("exact_lookup")),
            "Direct identifier and path lookup from the compiler snapshot and local evidence index.",
        ),
        (
            "Sparse recall",
            bool(capabilities.get("sparse_recall")),
            "Keyword-style recall lane backed by sparse retrieval.",
        ),
        (
            "Typed graph",
            bool(capabilities.get("typed_graph_expansion")),
            "Relationship expansion across typed entities linked in projection memory.",
        ),
        (
            "Miss recovery",
            bool(capabilities.get("miss_recovery")),
            "Fallback recovery lane used when the primary retrieval slice misses.",
        ),
        (
            "Routing handoff",
            bool(capabilities.get("routing_handoff")),
            "Handoff path from memory retrieval into route-specific execution or analysis lanes.",
        ),
        (
            "Hybrid rerank",
            bool(capabilities.get("hybrid_rerank_enabled")),
            "Combined reranking across multiple recall sources before final packet selection.",
        ),
    )
    chips = "".join(
        _token_label_html(
            css_class="telemetry-capability telemetry-capability-" + ("on" if enabled else "off"),
            text=label,
            tooltip=f"{tooltip} {'Enabled' if enabled else 'Not enabled'} in the current runtime snapshot.",
            aria_label=f"{label}: {'enabled' if enabled else 'not enabled'}. {tooltip}",
        )
        for label, enabled, tooltip in ordered
    )
    return (
        '<section class="telemetry-section">'
        '<p class="telemetry-section-title">Capability Rail</p>'
        f'<div class="telemetry-capability-row">{chips}</div>'
        '</section>'
    )


def _telemetry_snapshot_rows(title: str, rows: Sequence[tuple[str, str, str]]) -> str:
    rendered = []
    for label, primary, secondary in rows:
        rendered.append(
            '<div class="telemetry-snapshot-row">'
            '<div class="telemetry-snapshot-copy">'
            f'<span class="telemetry-snapshot-label">{html.escape(label)}</span>'
            f'<span class="telemetry-snapshot-primary">{html.escape(primary)}</span>'
            '</div>'
            f'<span class="telemetry-snapshot-secondary">{html.escape(secondary)}</span>'
            '</div>'
        )
    if not rendered:
        rendered.append('<p class="telemetry-empty">No telemetry recorded yet.</p>')
    return (
        '<section class="telemetry-section">'
        f'<p class="telemetry-section-title">{html.escape(title)}</p>'
        '<div class="telemetry-snapshot-list">'
        + "".join(rendered)
        + '</div></section>'
    )


def _telemetry_index_rows_html(
    *,
    title: str,
    rows: Sequence[tuple[str, int, str]],
    accent: str,
) -> str:
    max_count = max((count for _label, count, _updated in rows), default=1)
    rendered = []
    for label, count, updated in rows:
        safe_percent = (float(count) / float(max_count)) * 100.0 if max_count else 0.0
        rendered.append(
            '<div class="telemetry-index-row">'
            '<div class="telemetry-index-head">'
            f'<span class="telemetry-index-label">{html.escape(label)}</span>'
            f'<span class="telemetry-index-count">{count} rows</span>'
            '</div>'
            '<span class="telemetry-index-bar">'
            f'<span class="telemetry-index-fill" style="width: {safe_percent:.1f}%; background: {accent};"></span>'
            '</span>'
            f'<span class="telemetry-index-updated">Updated {html.escape(updated)}</span>'
            '</div>'
        )
    if not rendered:
        rendered.append('<p class="telemetry-empty">No index telemetry recorded yet.</p>')
    return (
        '<section class="telemetry-section">'
        f'<p class="telemetry-section-title">{html.escape(title)}</p>'
        '<div class="telemetry-index-list">'
        + "".join(rendered)
        + '</div></section>'
    )


def build_odylith_drawer_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Telemetry drawer removed from the shell contract."""

    return {}

    odylith_switch = _odylith_switch(payload)
    if odylith_switch and not bool(odylith_switch.get("enabled", True)):
        return {
            "contract": "odylith_drawer.v1",
            "status": "disabled",
            "mode": str(odylith_switch.get("mode", "")).strip() or "disabled",
            "source": str(odylith_switch.get("source", "")).strip() or "default",
            "note": str(odylith_switch.get("note", "")).strip(),
        }

    memory = dict(payload.get("memory_snapshot", {})) if isinstance(payload.get("memory_snapshot"), Mapping) else {}
    optimization = (
        dict(payload.get("optimization_snapshot", {}))
        if isinstance(payload.get("optimization_snapshot"), Mapping)
        else {}
    )
    evaluation = dict(payload.get("evaluation_snapshot", {})) if isinstance(payload.get("evaluation_snapshot"), Mapping) else {}
    history = (
        dict(payload.get("odylith_drawer_history", {}))
        if isinstance(payload.get("odylith_drawer_history"), Mapping)
        else {}
    )

    memory_engine = dict(memory.get("engine", {})) if isinstance(memory.get("engine"), Mapping) else {}
    memory_transition = dict(memory.get("backend_transition", {})) if isinstance(memory.get("backend_transition"), Mapping) else {}
    memory_areas = dict(memory.get("memory_areas", {})) if isinstance(memory.get("memory_areas"), Mapping) else {}
    judgment_memory = dict(memory.get("judgment_memory", {})) if isinstance(memory.get("judgment_memory"), Mapping) else {}
    guidance_catalog = dict(memory.get("guidance_catalog", {})) if isinstance(memory.get("guidance_catalog"), Mapping) else {}
    entity_counts = dict(memory.get("entity_counts", {})) if isinstance(memory.get("entity_counts"), Mapping) else {}
    runtime_state = dict(memory.get("runtime_state", {})) if isinstance(memory.get("runtime_state"), Mapping) else {}
    remote_retrieval = dict(memory.get("remote_retrieval", {})) if isinstance(memory.get("remote_retrieval"), Mapping) else {}
    optimization_overall = dict(optimization.get("overall", {})) if isinstance(optimization.get("overall"), Mapping) else {}
    optimization_packet = dict(optimization.get("packet_posture", {})) if isinstance(optimization.get("packet_posture"), Mapping) else {}
    optimization_quality = dict(optimization.get("quality_posture", {})) if isinstance(optimization.get("quality_posture"), Mapping) else {}
    optimization_orchestration = (
        dict(optimization.get("orchestration_posture", {}))
        if isinstance(optimization.get("orchestration_posture"), Mapping)
        else {}
    )
    optimization_intent = dict(optimization.get("intent_posture", {})) if isinstance(optimization.get("intent_posture"), Mapping) else {}
    optimization_latency = dict(optimization.get("latency_posture", {})) if isinstance(optimization.get("latency_posture"), Mapping) else {}
    latest_packet = dict(optimization.get("latest_packet", {})) if isinstance(optimization.get("latest_packet"), Mapping) else {}
    learning_loop = dict(optimization.get("learning_loop", {})) if isinstance(optimization.get("learning_loop"), Mapping) else {}
    learning_control_posture = (
        dict(learning_loop.get("control_posture", {}))
        if isinstance(learning_loop.get("control_posture"), Mapping)
        else {}
    )
    evaluation_posture = (
        dict(optimization.get("evaluation_posture", {}))
        if isinstance(optimization.get("evaluation_posture"), Mapping)
        else {}
    )
    control_advisories = (
        dict(optimization.get("control_advisories", {}))
        if isinstance(optimization.get("control_advisories"), Mapping)
        else {}
    )
    evaluation_packet_events = (
        dict(evaluation_posture.get("packet_events", {}))
        if isinstance(evaluation_posture.get("packet_events"), Mapping)
        else {}
    )
    evaluation_decision_quality = (
        dict(evaluation_posture.get("decision_quality", {}))
        if isinstance(evaluation_posture.get("decision_quality"), Mapping)
        else {}
    )
    evaluation_decision_quality_confidence = (
        dict(evaluation_decision_quality.get("confidence", {}))
        if isinstance(evaluation_decision_quality.get("confidence"), Mapping)
        else {}
    )
    evaluation_program = dict(evaluation.get("program", {})) if isinstance(evaluation.get("program"), Mapping) else {}
    architecture_posture = dict(evaluation.get("architecture", {})) if isinstance(evaluation.get("architecture"), Mapping) else {}

    actual_backend = dict(memory_engine.get("backend", {})) if isinstance(memory_engine.get("backend"), Mapping) else {}
    target_backend = dict(memory_engine.get("target_backend", {})) if isinstance(memory_engine.get("target_backend"), Mapping) else {}
    local_backend_status = (
        dict(memory_transition.get("local_backend_status", {}))
        if isinstance(memory_transition.get("local_backend_status"), Mapping)
        else {}
    )

    packet_events = [dict(row) for row in history.get("packet_events", []) if isinstance(row, Mapping)] if isinstance(history.get("packet_events"), list) else []
    router_events = [dict(row) for row in history.get("router_events", []) if isinstance(row, Mapping)] if isinstance(history.get("router_events"), list) else []
    orchestration_events = [dict(row) for row in history.get("orchestration_events", []) if isinstance(row, Mapping)] if isinstance(history.get("orchestration_events"), list) else []
    timing_events = [dict(row) for row in history.get("timing_events", []) if isinstance(row, Mapping)] if isinstance(history.get("timing_events"), list) else []

    if not packet_events and latest_packet:
        packet_events = [
            {
                "index": 1,
                "label": "P1",
                "recorded_at": str(optimization.get("freshness_utc", "")).strip() or str(payload.get("generated_utc", "")).strip(),
                "workstream": str(latest_packet.get("workstream", "")).strip(),
                "session_id": str(latest_packet.get("session_id", "")).strip(),
                "packet_state": str(latest_packet.get("packet_state", "")).strip(),
                "context_density_score": _safe_int(optimization_quality.get("avg_context_density_score", 0.0), minimum=0, maximum=4),
                "reasoning_readiness_score": _safe_int(optimization_quality.get("avg_reasoning_readiness_score", 0.0), minimum=0, maximum=4),
                "evidence_diversity_score": _safe_int(optimization_quality.get("avg_evidence_diversity_score", 0.0), minimum=0, maximum=4),
                "utility_score": _safe_int(optimization_quality.get("avg_utility_score", 0.0), minimum=0, maximum=4),
                "density_per_1k_tokens": round(_safe_float(optimization_quality.get("avg_density_per_1k_tokens", 0.0), minimum=0.0, maximum=1000.0), 3),
                "estimated_tokens": _safe_int(latest_packet.get("estimated_tokens", 0), minimum=0, maximum=250000),
                "within_budget_score": 100 if bool(latest_packet.get("within_budget")) else 0,
                "route_ready_score": 100 if bool(latest_packet.get("route_ready")) else 0,
                "spawn_ready_score": 100 if bool(latest_packet.get("native_spawn_ready")) else 0,
                "deep_reasoning_ready_score": 100 if bool(optimization_quality.get("deep_reasoning_ready_rate", 0.0)) else 0,
                "benchmark_match_score": 100 if _safe_float(evaluation.get("coverage_rate", 0.0), minimum=0.0, maximum=1.0) > 0.0 else 0,
                "benchmark_satisfaction_score": _safe_int(_safe_ratio_percent(evaluation.get("satisfaction_rate", 0.0)), minimum=0, maximum=100),
                "advisory_alignment_score": _safe_int(
                    _safe_ratio_percent(evaluation_packet_events.get("advisory_alignment_rate", 0.0)),
                    minimum=0,
                    maximum=100,
                ),
                "yield_score": _safe_int(
                    _safe_ratio_percent(evaluation_packet_events.get("avg_effective_yield_score", 0.0)),
                    minimum=0,
                    maximum=100,
                ),
                "execution_profile": str(latest_packet.get("odylith_execution_profile", "")).strip(),
                "execution_delegate_preference": str(latest_packet.get("odylith_execution_delegate_preference", "")).strip(),
                "packet_strategy": str(latest_packet.get("packet_strategy", "")).strip(),
                "budget_mode": str(latest_packet.get("budget_mode", "")).strip(),
                "retrieval_focus": str(latest_packet.get("retrieval_focus", "")).strip(),
                "speed_mode": str(latest_packet.get("speed_mode", "")).strip(),
                "reliability": str(latest_packet.get("reliability", "")).strip(),
                "selection_bias": str(latest_packet.get("selection_bias", "")).strip(),
                "advised_packet_strategy": str(latest_packet.get("advised_packet_strategy", "")).strip(),
                "advised_budget_mode": str(latest_packet.get("advised_budget_mode", "")).strip(),
                "advised_retrieval_focus": str(latest_packet.get("advised_retrieval_focus", "")).strip(),
                "advised_speed_mode": str(latest_packet.get("advised_speed_mode", "")).strip(),
                "packet_alignment_state": str(latest_packet.get("packet_alignment_state", "")).strip()
                or str(control_advisories.get("packet_alignment_state", "")).strip(),
            }
        ]

    reasoning_labels = [str(row.get("label", "")).strip() or f"P{index + 1}" for index, row in enumerate(packet_events)]
    reasoning_density = [_safe_int(row.get("context_density_score", 0), minimum=0, maximum=4) for row in packet_events]
    reasoning_readiness = [_safe_int(row.get("reasoning_readiness_score", 0), minimum=0, maximum=4) for row in packet_events]
    reasoning_diversity = [_safe_int(row.get("evidence_diversity_score", 0), minimum=0, maximum=4) for row in packet_events]
    reasoning_utility = [_safe_int(row.get("utility_score", 0), minimum=0, maximum=4) for row in packet_events]
    reasoning_tokens = [_safe_int(row.get("estimated_tokens", 0), minimum=0, maximum=250000) for row in packet_events]
    reasoning_budget = [_safe_int(row.get("within_budget_score", 0), minimum=0, maximum=100) for row in packet_events]
    reasoning_route_ready = [_safe_int(row.get("route_ready_score", 0), minimum=0, maximum=100) for row in packet_events]
    reasoning_spawn_ready = [_safe_int(row.get("spawn_ready_score", 0), minimum=0, maximum=100) for row in packet_events]
    reasoning_satisfaction = [_safe_int(row.get("benchmark_satisfaction_score", 0), minimum=0, maximum=100) for row in packet_events]
    reasoning_alignment = [_safe_int(row.get("advisory_alignment_score", 0), minimum=0, maximum=100) for row in packet_events]
    reasoning_yield = [_safe_int(row.get("yield_score", 0), minimum=0, maximum=100) for row in packet_events]
    reasoning_utility_average = round(sum(reasoning_utility) / len(reasoning_utility), 1) if reasoning_utility else 0.0
    signal_density = [round(_safe_float(value, minimum=0.0, maximum=4.0) * 25.0, 1) for value in reasoning_density] or [0.0]
    signal_readiness = [round(_safe_float(value, minimum=0.0, maximum=4.0) * 25.0, 1) for value in reasoning_readiness] or [0.0]
    signal_diversity = [round(_safe_float(value, minimum=0.0, maximum=4.0) * 25.0, 1) for value in reasoning_diversity] or [0.0]
    signal_utility = [round(_safe_float(value, minimum=0.0, maximum=4.0) * 25.0, 1) for value in reasoning_utility] or [0.0]
    control_story_sample_count = max(1, len(reasoning_labels))
    control_story_mode = "snapshot" if control_story_sample_count <= 1 else "lollipop" if control_story_sample_count <= 3 else "trend"
    control_story_latest_row = packet_events[-1] if packet_events else {}
    control_story_previous_row = packet_events[-2] if len(packet_events) >= 2 else {}

    def _series_delta(values: Sequence[int | float]) -> float | None:
        if len(values) < 2:
            return None
        current = _safe_float(values[-1], minimum=-250000.0, maximum=250000.0)
        previous = _safe_float(values[-2], minimum=-250000.0, maximum=250000.0)
        return round(current - previous, 1)

    control_story_detail = {
        "label": str(control_story_latest_row.get("label", "")).strip() or (reasoning_labels[-1] if reasoning_labels else "P1"),
        "recorded_at": _format_timestamp_utc(
            control_story_latest_row.get("recorded_at")
            or latest_packet.get("recorded_at")
            or optimization.get("freshness_utc")
            or payload.get("generated_utc")
        ),
        "workstream": str(control_story_latest_row.get("workstream", "")).strip() or str(latest_packet.get("workstream", "")).strip(),
        "session_id": str(control_story_latest_row.get("session_id", "")).strip() or str(latest_packet.get("session_id", "")).strip(),
        "state": _humanize_display(
            str(control_story_latest_row.get("packet_state", "")).strip() or str(latest_packet.get("packet_state", "")).strip() or "unknown",
            title_case=True,
        )
        or "Unknown",
        "tokens": _safe_int(control_story_latest_row.get("estimated_tokens", reasoning_tokens[-1] if reasoning_tokens else 0), minimum=0, maximum=250000),
        "budget_fit": _safe_int(control_story_latest_row.get("within_budget_score", reasoning_budget[-1] if reasoning_budget else 0), minimum=0, maximum=100),
        "budget_state": (
            "Within budget"
            if _safe_int(control_story_latest_row.get("within_budget_score", reasoning_budget[-1] if reasoning_budget else 0), minimum=0, maximum=100) >= 50
            else "Over budget"
        ),
        "utility": _safe_float(signal_utility[-1] if signal_utility else 0.0, minimum=0.0, maximum=100.0),
        "alignment": _safe_int(reasoning_alignment[-1] if reasoning_alignment else 0, minimum=0, maximum=100),
        "yield": _safe_int(reasoning_yield[-1] if reasoning_yield else 0, minimum=0, maximum=100),
        "route_ready": _safe_int(reasoning_route_ready[-1] if reasoning_route_ready else 0, minimum=0, maximum=100),
        "token_delta": _series_delta(reasoning_tokens),
        "utility_delta": _series_delta(signal_utility),
        "alignment_delta": _series_delta(reasoning_alignment),
        "yield_delta": _series_delta(reasoning_yield),
        "route_ready_delta": _series_delta(reasoning_route_ready),
        "previous_label": str(control_story_previous_row.get("label", "")).strip() if control_story_previous_row else "",
    }

    def _control_story_note() -> str:
        if control_story_mode == "snapshot":
            return "Single routed slice. Read spend first, then packet outcome signals."
        if control_story_mode == "lollipop":
            return "Short window. Latest spend is called out separately so the signal deltas stay readable."

        average_tokens = (sum(reasoning_tokens) / len(reasoning_tokens)) if reasoning_tokens else 0.0
        token_span = (max(reasoning_tokens) - min(reasoning_tokens)) if reasoning_tokens else 0.0
        if average_tokens >= 4500.0:
            spend_phrase = "Spend stays high"
        elif average_tokens >= 2500.0:
            spend_phrase = "Spend stays elevated"
        else:
            spend_phrase = "Spend stays light"
        if token_span <= max(600.0, average_tokens * 0.18):
            spend_phrase += " and steady"
        elif reasoning_tokens and reasoning_tokens[-1] >= average_tokens * 1.18:
            spend_phrase += " and is rising"
        elif reasoning_tokens and reasoning_tokens[-1] <= average_tokens * 0.82:
            spend_phrase += " and is easing"
        else:
            spend_phrase += " with visible swing"

        alignment_values = [_safe_int(value, minimum=0, maximum=100) for value in reasoning_alignment]
        alignment_avg = (sum(alignment_values) / len(alignment_values)) if alignment_values else 0.0
        alignment_span = (max(alignment_values) - min(alignment_values)) if alignment_values else 0.0
        if alignment_span >= 35.0:
            alignment_phrase = "Alignment is inconsistent"
        elif alignment_avg >= 80.0:
            alignment_phrase = "Alignment holds"
        elif alignment_avg >= 60.0:
            alignment_phrase = "Alignment is mixed"
        else:
            alignment_phrase = "Alignment is weak"

        yield_values = [_safe_int(value, minimum=0, maximum=100) for value in reasoning_yield]
        yield_avg = (sum(yield_values) / len(yield_values)) if yield_values else 0.0
        if yield_avg >= 70.0:
            yield_phrase = "Yield is strong"
        elif yield_avg >= 50.0:
            yield_phrase = "Yield is workable"
        else:
            yield_phrase = "Yield is weak"

        utility_avg = (sum(signal_utility) / len(signal_utility)) if signal_utility else 0.0
        route_avg = (sum(reasoning_route_ready) / len(reasoning_route_ready)) if reasoning_route_ready else 0.0
        if utility_avg >= 70.0 and yield_avg >= 60.0 and route_avg >= 70.0 and alignment_span < 35.0:
            verdict_phrase = "Current spend is buying credible routed outcomes"
        elif route_avg < 60.0:
            verdict_phrase = "Route readiness is still gating the quality of extra spend"
        else:
            verdict_phrase = "Extra spend is not clearly buying better routed outcomes"
        return f"{spend_phrase}. {alignment_phrase}. {yield_phrase}. {verdict_phrase}."

    control_story_note = _control_story_note()
    control_story_detail["story_note"] = control_story_note

    max_learning_len = max(len(packet_events), len(router_events), len(orchestration_events), 1)

    def _series(items: Sequence[Mapping[str, Any]], key: str, *, prefix: str) -> tuple[list[str], list[int | None]]:
        values = [_safe_int(row.get(key, 0), minimum=0, maximum=100) for row in items if isinstance(row, Mapping)]
        labels = [str(row.get("label", "")).strip() or f"{prefix}{index + 1}" for index, row in enumerate(items) if isinstance(row, Mapping)]
        if not values:
            return ([f"{prefix}1"], [0])
        pad = max(0, max_learning_len - len(values))
        return ([f"{prefix}{index + 1}" for index in range(max_learning_len)], ([None] * pad) + values)

    learning_labels = [f"L{index + 1}" for index in range(max_learning_len)]
    packet_learning = ([None] * max(0, max_learning_len - len(reasoning_satisfaction))) + reasoning_satisfaction if reasoning_satisfaction else [0]
    packet_alignment_learning = ([None] * max(0, max_learning_len - len(reasoning_alignment))) + reasoning_alignment if reasoning_alignment else [0]
    packet_yield_learning = ([None] * max(0, max_learning_len - len(reasoning_yield))) + reasoning_yield if reasoning_yield else [0]
    router_learning = _series(router_events, "accepted_score", prefix="R")[1]
    orchestration_learning = _series(orchestration_events, "token_efficient_score", prefix="O")[1]

    def _normalized_distribution(source: Any) -> dict[str, int]:
        if not isinstance(source, Mapping):
            return {}
        normalized: dict[str, int] = {}
        for label, value in source.items():
            token = str(label or "").strip()
            count = _safe_int(value, minimum=0, maximum=1000)
            if not token or count <= 0:
                continue
            normalized[token] = count
        return normalized

    backend_gap_labels = [
        _humanize_display(token, title_case=True) or str(token)
        for token in memory_transition.get("gaps", ())
        if str(token).strip()
    ]
    regressions = (
        _compact_unique_text(evaluation_posture.get("regressions", []), limit=3, title_case=True)
        if isinstance(evaluation_posture.get("regressions"), list)
        else []
    )

    actual_storage = str(actual_backend.get("storage", "")).strip() or "local derived memory"
    actual_sparse = str(actual_backend.get("sparse_recall", "")).strip() or "sparse recall"
    target_storage = str(target_backend.get("storage", "")).strip() or "-"
    target_sparse = str(target_backend.get("sparse_recall", "")).strip() or "-"
    snapshot_time = _format_timestamp_utc(
        memory.get("generated_utc")
        or optimization.get("generated_utc")
        or evaluation.get("generated_utc")
        or payload.get("generated_utc")
    )
    memory_status = str(memory_transition.get("status", "")).strip() or str(memory.get("status", "")).strip() or "cold"
    optimization_status = str(optimization_overall.get("level", "")).strip() or str(optimization.get("status", "")).strip() or "cold"
    evaluation_status = str(evaluation.get("status", "")).strip() or "unseeded"

    freshness_posture = _odylith_freshness_posture(
        snapshot_time=memory.get("generated_utc") or optimization.get("generated_utc") or evaluation.get("generated_utc") or payload.get("generated_utc"),
        event_times=[
            *(row.get("recorded_at") for row in packet_events),
            *(row.get("recorded_at") for row in router_events),
            *(row.get("recorded_at") for row in orchestration_events),
            *(row.get("recorded_at") for row in timing_events),
        ],
    )
    signal_posture = _odylith_signal_posture(
        packet_count=len(packet_events),
        router_count=len(router_events),
        orchestration_count=len(orchestration_events),
        timing_count=len(timing_events),
    )

    radar_values = [
        round(_safe_float(optimization_quality.get("avg_context_density_score", 0.0), minimum=0.0, maximum=4.0) * 25.0, 1),
        round(_safe_float(optimization_quality.get("avg_reasoning_readiness_score", 0.0), minimum=0.0, maximum=4.0) * 25.0, 1),
        round(_safe_float(optimization_quality.get("avg_evidence_diversity_score", 0.0), minimum=0.0, maximum=4.0) * 25.0, 1),
        _safe_ratio_percent(optimization_packet.get("within_budget_rate", 0.0)),
        _safe_ratio_percent(evaluation.get("coverage_rate", 0.0)),
        _safe_ratio_percent(evaluation.get("satisfaction_rate", 0.0)),
    ]

    recommendation_rows = (
        _compact_unique_text(optimization.get("recommendations", []), limit=3)
        if isinstance(optimization.get("recommendations"), list)
        else []
    )
    learning_recommendation_rows = (
        _compact_unique_text(evaluation_posture.get("recommendations", []), limit=3)
        if isinstance(evaluation_posture.get("recommendations"), list)
        else []
    )
    architecture_recommendation_rows = (
        _compact_unique_text(architecture_posture.get("recommendations", []), limit=2)
        if isinstance(architecture_posture.get("recommendations"), list)
        else []
    )

    advisory_confidence = dict(control_advisories.get("confidence", {})) if isinstance(control_advisories.get("confidence"), Mapping) else {}
    advisory_evidence_strength = (
        dict(control_advisories.get("evidence_strength", {}))
        if isinstance(control_advisories.get("evidence_strength"), Mapping)
        else {}
    )
    advisory_focus_areas = (
        _compact_unique_text(control_advisories.get("focus_areas", []), limit=4, title_case=True)
        if isinstance(control_advisories.get("focus_areas"), list)
        else []
    )
    decision_quality_state = (
        _humanize_display(str(control_advisories.get("decision_quality_state", "")).strip(), title_case=True)
        or "Unknown"
    )
    advisory_confidence_label = (
        _humanize_display(str(advisory_confidence.get("level", "")).strip(), title_case=True) or "Unknown"
    )
    evidence_strength_label = (
        _humanize_display(str(advisory_evidence_strength.get("level", "")).strip(), title_case=True) or "Unknown"
    )
    reasoning_mode_label = (
        _humanize_display(str(control_advisories.get("reasoning_mode", "")).strip(), title_case=True) or "Unknown"
    )
    architecture_status_label = (
        _humanize_display(str(architecture_posture.get("status", "")).strip(), title_case=True) or "Unknown"
    )
    decision_quality_score = _safe_float(
        control_advisories.get("decision_quality_score", 0.0),
        minimum=0.0,
        maximum=1.0,
    )
    decision_quality_percent = round(decision_quality_score * 100.0, 1)
    architecture_coverage_rate = _safe_ratio_percent(architecture_posture.get("coverage_rate", 0.0))
    architecture_satisfaction_rate = _safe_ratio_percent(architecture_posture.get("satisfaction_rate", 0.0))
    architecture_corpus_size = _safe_int(architecture_posture.get("corpus_size", 0), minimum=0)
    architecture_covered_count = _safe_int(architecture_posture.get("covered_case_count", 0), minimum=0)
    architecture_satisfied_count = _safe_int(architecture_posture.get("satisfied_case_count", 0), minimum=0)
    decision_quality_confidence_level = (
        _humanize_display(
            str(evaluation_decision_quality_confidence.get("level", "")).strip()
            or str(control_advisories.get("decision_quality_confidence_level", "")).strip(),
            title_case=True,
        )
        or advisory_confidence_label
    )
    decision_quality_confidence_score = _safe_int(
        evaluation_decision_quality_confidence.get("score", control_advisories.get("decision_quality_confidence_score", 0)),
        minimum=0,
        maximum=4,
    )
    decision_quality_sample_balance = (
        _humanize_display(str(evaluation_decision_quality_confidence.get("sample_balance", "")).strip(), title_case=True)
        or "Unknown"
    )
    decision_quality_closeout_rate = _safe_ratio_percent(
        evaluation_decision_quality.get(
            "closeout_observation_rate",
            evaluation_decision_quality_confidence.get("closeout_observation_rate", 0.0),
        )
    )
    decision_quality_regret_rate = _safe_ratio_percent(evaluation_decision_quality.get("delegation_regret_rate", 0.0))
    decision_quality_churn_rate = _safe_ratio_percent(evaluation_decision_quality.get("followup_churn_rate", 0.0))

    def _recorder_budget_posture(score: Any) -> tuple[int, str, str]:
        budget_percent = _safe_int(score, minimum=0, maximum=100)
        if budget_percent >= 75:
            return budget_percent, "Within budget", "steady"
        if budget_percent >= 40:
            return budget_percent, "Near budget edge", "watch"
        return budget_percent, "Over budget", "risk"

    def _recorder_operator_guidance(
        *,
        budget_percent: int,
        utility_percent: int,
        alignment_percent: int,
        route_ready_percent: int,
    ) -> tuple[str, str, str]:
        if budget_percent < 40 and route_ready_percent < 60:
            return (
                "Intervene",
                "Spend is already past budget and the route is still not ready. Narrow the slice or add stronger path/workstream grounding before another delegated pass.",
                "intervene",
            )
        if budget_percent < 40:
            return (
                "Intervene",
                "Spend is running past budget. Tighten the slice before adding more depth or delegation.",
                "intervene",
            )
        if route_ready_percent < 60 and utility_percent < 60:
            return (
                "Intervene",
                "The slice is still gated and not earning its spend. Ground it before spending more on the next pass.",
                "intervene",
            )
        if alignment_percent < 60:
            return (
                "Intervene",
                "Alignment is weak. Add stronger path or workstream anchors before more automation.",
                "intervene",
            )
        if route_ready_percent < 60:
            return (
                "Watch",
                "The route is not ready yet. Keep this slice local or serial until the next pass improves readiness.",
                "watch",
            )
        if utility_percent < 55:
            return (
                "Watch",
                "The signals are still weak for the spend. Check retrieval grounding before you spend more here.",
                "watch",
            )
        if utility_percent >= 75 and alignment_percent >= 75 and route_ready_percent >= 75 and budget_percent >= 75:
            return (
                "Keep",
                "Signals are strong and spend is under control. Current posture is working on this slice.",
                "keep",
            )
        return (
            "Watch",
            "Signals are usable but not decisive. Hold the current posture until one more slice confirms direction.",
            "watch",
        )

    recorder_rows: list[dict[str, Any]] = []
    for row in packet_events[-8:]:
        packet_strategy = _humanize_display(str(row.get("packet_strategy", "")).strip(), title_case=True) or (
            _humanize_display(str(row.get("advised_packet_strategy", "")).strip(), title_case=True) or "Balanced"
        )
        budget_percent, budget_label, budget_tone = _recorder_budget_posture(row.get("within_budget_score", 0))
        utility_percent = _safe_int(_safe_float(row.get("utility_score", 0.0), minimum=0.0, maximum=4.0) * 25.0, minimum=0, maximum=100)
        alignment_percent = _safe_int(row.get("advisory_alignment_score", 0), minimum=0, maximum=100)
        route_ready_percent = _safe_int(row.get("route_ready_score", 0), minimum=0, maximum=100)
        operator_call, operator_summary, operator_tone = _recorder_operator_guidance(
            budget_percent=budget_percent,
            utility_percent=utility_percent,
            alignment_percent=alignment_percent,
            route_ready_percent=route_ready_percent,
        )
        recorder_rows.append(
            {
                "label": str(row.get("label", "")).strip() or f'P{len(recorder_rows) + 1}',
                "recorded_at": _format_timestamp_utc(row.get("recorded_at", "")),
                "state": _humanize_display(str(row.get("packet_state", "")).strip() or "unknown", title_case=True) or "Unknown",
                "tokens": _safe_int(row.get("estimated_tokens", 0), minimum=0, maximum=250000),
                "utility_percent": utility_percent,
                "alignment_percent": alignment_percent,
                "budget_percent": budget_percent,
                "route_ready": route_ready_percent,
                "packet_strategy": packet_strategy,
                "workstream": str(row.get("workstream", "")).strip(),
                "session_id": str(row.get("session_id", "")).strip(),
                "budget_label": budget_label,
                "budget_tone": budget_tone,
                "operator_call": operator_call,
                "operator_summary": operator_summary,
                "operator_tone": operator_tone,
            }
        )
    if not recorder_rows:
        fallback_budget_percent = 100 if bool(latest_packet.get("within_budget")) else 0
        budget_percent, budget_label, budget_tone = _recorder_budget_posture(fallback_budget_percent)
        utility_percent = _safe_int(_safe_float(optimization_quality.get("avg_utility_score", 0.0), minimum=0.0, maximum=4.0) * 25.0, minimum=0, maximum=100)
        alignment_percent = _safe_int(_safe_ratio_percent(control_advisories.get("packet_alignment_rate", 0.0)), minimum=0, maximum=100)
        route_ready_percent = 100 if bool(latest_packet.get("route_ready")) else 0
        operator_call, operator_summary, operator_tone = _recorder_operator_guidance(
            budget_percent=budget_percent,
            utility_percent=utility_percent,
            alignment_percent=alignment_percent,
            route_ready_percent=route_ready_percent,
        )
        recorder_rows = [
            {
                "label": "Latest",
                "recorded_at": snapshot_time,
                "state": _humanize_display(str(latest_packet.get("packet_state", "")).strip() or "unknown", title_case=True) or "Unknown",
                "tokens": _safe_int(latest_packet.get("estimated_tokens", 0), minimum=0, maximum=250000),
                "utility_percent": utility_percent,
                "alignment_percent": alignment_percent,
                "budget_percent": budget_percent,
                "route_ready": route_ready_percent,
                "packet_strategy": _humanize_display(str(latest_packet.get("advised_packet_strategy", "")).strip(), title_case=True) or "Precision First",
                "workstream": str(latest_packet.get("workstream", "")).strip(),
                "session_id": str(latest_packet.get("session_id", "")).strip(),
                "budget_label": budget_label,
                "budget_tone": budget_tone,
                "operator_call": operator_call,
                "operator_summary": operator_summary,
                "operator_tone": operator_tone,
            }
        ]

    execution_distribution_candidates = (
        ("Parallelism Hints", _normalized_distribution(optimization_orchestration.get("parallelism_hint_distribution"))),
        ("Reasoning Bias", _normalized_distribution(optimization_orchestration.get("reasoning_bias_distribution"))),
        (
            "Execution Modes",
            _normalized_distribution(optimization_orchestration.get("odylith_execution_selection_mode_distribution")),
        ),
        ("Execution Profiles", _normalized_distribution(optimization_orchestration.get("odylith_execution_profile_distribution"))),
        ("Packet States", _normalized_distribution(optimization_packet.get("state_distribution"))),
    )
    execution_flow_source = "No Distribution"
    execution_flow_map: dict[str, int] = {}
    for label, distribution in execution_distribution_candidates:
        if len(distribution) >= 2:
            execution_flow_source = label
            execution_flow_map = distribution
            break
    if not execution_flow_map:
        for label, distribution in execution_distribution_candidates:
            if distribution:
                execution_flow_source = label
                execution_flow_map = distribution
                break
    execution_flow_labels = [
        _humanize_display(label, title_case=True) or str(label)
        for label in execution_flow_map.keys()
        if str(label).strip()
    ]
    execution_flow_values = [_safe_int(value, minimum=0, maximum=1000) for value in execution_flow_map.values()]
    if not execution_flow_labels or sum(execution_flow_values) <= 0:
        execution_flow_labels = ["No recent routed distribution"]
        execution_flow_values = [1]
        execution_flow_source = "No Distribution"

    control_calibration_labels = [
        "Closeout",
        "Confidence",
        "Low regret",
        "Low churn",
        "Alignment",
        "Yield",
        "Arch fit",
    ]
    control_calibration_values = [
        round(decision_quality_closeout_rate, 1),
        round(_safe_int(decision_quality_confidence_score, minimum=0, maximum=4) * 25.0, 1),
        round(max(0.0, 100.0 - decision_quality_regret_rate), 1),
        round(max(0.0, 100.0 - decision_quality_churn_rate), 1),
        round(
            _safe_ratio_percent(
                control_advisories.get(
                    "reliable_packet_alignment_rate",
                    control_advisories.get("packet_alignment_rate", 0.0),
                )
            ),
            1,
        ),
        round(
            _safe_ratio_percent(
                control_advisories.get(
                    "reliable_high_yield_rate",
                    control_advisories.get(
                        "high_yield_rate",
                        evaluation_packet_events.get(
                            "avg_effective_yield_score",
                            optimization_quality.get("avg_effective_yield_score", 0.0),
                        ),
                    ),
                )
            ),
            1,
        ),
        round(architecture_satisfaction_rate, 1),
    ]

    watchlist_rows: list[str] = []
    if advisory_focus_areas:
        watchlist_rows.append(f"Control focus: {', '.join(advisory_focus_areas[:3])}.")
    if decision_quality_confidence_score and decision_quality_confidence_score < 3:
        watchlist_rows.append(
            "Decision-quality evidence is still thin; keep delegation calibration provisional until more slices close out."
        )
    elif decision_quality_regret_rate >= 25:
        watchlist_rows.append(
            f"Delegation regret is {decision_quality_regret_rate:.0f}%; bias tighter bounded execution until closeout quality recovers."
        )
    elif decision_quality_churn_rate >= 25:
        watchlist_rows.append(
            f"Follow-up churn is {decision_quality_churn_rate:.0f}%; prefer narrower packets before widening fan-out again."
        )
    if architecture_recommendation_rows:
        watchlist_rows.extend(architecture_recommendation_rows[:1])
    if recommendation_rows:
        watchlist_rows.extend(recommendation_rows[:1])
    if learning_recommendation_rows:
        watchlist_rows.extend(learning_recommendation_rows[:1])
    if drawer_regressions := (
        _compact_unique_text(evaluation_posture.get("regressions", []), limit=2, title_case=True)
        if isinstance(evaluation_posture.get("regressions"), list)
        else []
    ):
        watchlist_rows.extend(drawer_regressions[:1])
    watchlist_rows = [row for row in watchlist_rows if str(row).strip()][:4]

    freshness_label = str(freshness_posture.get("label", "")).strip() or "Unknown"
    signal_label = str(signal_posture.get("label", "")).strip() or "Unknown"
    route_ready_percent = _safe_ratio_percent(optimization_quality.get("route_ready_rate", 0.0))
    packet_alignment_percent = _safe_ratio_percent(control_advisories.get("packet_alignment_rate", 0.0))

    def _sentence_line(value: Any) -> str:
        text = str(value or "").strip()
        if not text:
            return ""
        text = text[0].upper() + text[1:]
        return text if text.endswith((".", "!", "?")) else f"{text}."

    def _push_unique_line(lines: list[str], value: str) -> None:
        token = str(value or "").strip()
        if token and token not in lines:
            lines.append(token)

    operator_depth_label = _humanize_display(
        str(learning_control_posture.get("depth", "")).strip() or str(control_advisories.get("depth", "")).strip(),
        title_case=True,
    ) or "Balanced"
    operator_delegation_label = _humanize_display(
        str(learning_control_posture.get("delegation", "")).strip() or str(control_advisories.get("delegation", "")).strip(),
        title_case=True,
    ) or "Balanced"
    operator_parallelism_label = _humanize_display(
        str(learning_control_posture.get("parallelism", "")).strip() or str(control_advisories.get("parallelism", "")).strip(),
        title_case=True,
    ) or "Balanced"
    operator_packet_strategy_label = _humanize_display(
        str(learning_control_posture.get("packet_strategy", "")).strip() or str(control_advisories.get("packet_strategy", "")).strip(),
        title_case=True,
    ) or "Balanced"
    operator_budget_mode_label = _humanize_display(
        str(learning_control_posture.get("budget_mode", "")).strip() or str(control_advisories.get("budget_mode", "")).strip(),
        title_case=True,
    ) or "Balanced"
    operator_alignment_state_label = _humanize_display(
        str(learning_control_posture.get("packet_alignment_state", "")).strip()
        or str(control_advisories.get("packet_alignment_state", "")).strip(),
        title_case=True,
    ) or "Unknown"
    operator_yield_state_label = _humanize_display(
        str(learning_control_posture.get("yield_state", "")).strip() or str(control_advisories.get("yield_state", "")).strip(),
        title_case=True,
    ) or "Unknown"

    primary_recommendation = next(
        (
            str(row).strip()
            for row in (
                *recommendation_rows,
                *learning_recommendation_rows,
                *architecture_recommendation_rows,
            )
            if str(row).strip()
        ),
        "",
    )
    if primary_recommendation:
        operator_story_title = _sentence_line(primary_recommendation)
    elif decision_quality_confidence_score < 2 or signal_label.lower() == "sparse":
        operator_story_title = "Keep execution balanced and grounded until evidence strengthens."
    elif architecture_corpus_size > 0 and architecture_coverage_rate < 60.0:
        operator_story_title = "Hold wider execution until architecture evidence improves."
    else:
        operator_story_title = _sentence_line(
            f"Favor {operator_packet_strategy_label.lower()} packets with {operator_delegation_label.lower()} delegation"
        )

    posture_cluster = {
        operator_packet_strategy_label.lower(),
        operator_delegation_label.lower(),
        operator_parallelism_label.lower(),
        operator_budget_mode_label.lower(),
    }
    if len(posture_cluster) == 1:
        shared_posture = next(iter(posture_cluster))
        operator_story_summary = (
            f"Current control posture stays {shared_posture} across packet strategy, delegation, execution, and budget. "
            f"Alignment is {operator_alignment_state_label.lower()}, and yield is {operator_yield_state_label.lower()}."
        )
    else:
        operator_story_summary = (
            f"Current control posture stays {operator_packet_strategy_label.lower()} with "
            f"{operator_delegation_label.lower()} delegation and {operator_parallelism_label.lower()} execution. "
            f"Budget remains {operator_budget_mode_label.lower()}, alignment is {operator_alignment_state_label.lower()}, "
            f"and yield is {operator_yield_state_label.lower()}."
        )

    operator_story_reasons_raw: list[str] = []
    decision_confidence_story = (
        f"{decision_quality_confidence_level.lower()} confidence"
        if decision_quality_confidence_level.lower() != "none"
        else "no confidence signal"
    )
    _push_unique_line(
        operator_story_reasons_raw,
        (
            f"Decision quality is {decision_quality_state.lower()} with {decision_confidence_story} "
            f"and {decision_quality_closeout_rate:.0f}% closeout coverage"
        ),
    )
    if architecture_corpus_size > 0 and architecture_covered_count > 0:
        _push_unique_line(
            operator_story_reasons_raw,
            (
                f"Architecture posture is {architecture_status_label.lower()} with "
                f"{architecture_covered_count}/{architecture_corpus_size} recent benchmark cases covered"
            ),
        )
    else:
        _push_unique_line(
            operator_story_reasons_raw,
            (
                f"Architecture benchmarks are present but only {architecture_covered_count}/{architecture_corpus_size} recent cases are covered"
                if architecture_corpus_size > 0
                else "Architecture posture has no recent benchmark cases, so architecture guidance stays provisional"
            ),
        )
    if signal_label.lower() == "sparse":
        _push_unique_line(
            operator_story_reasons_raw,
            "Recent recorder history is sparse, so the recommendation is anchored to the freshest routed slice",
        )
    else:
        _push_unique_line(
            operator_story_reasons_raw,
            (
                f"History is {freshness_label.lower()} with {len(packet_events)} packet slices and "
                + (
                    f"{len(orchestration_events)} orchestration outcomes behind the current call"
                    if orchestration_events
                    else "no orchestration outcomes behind the current call"
                )
            ),
        )
    if advisory_focus_areas:
        _push_unique_line(
            operator_story_reasons_raw,
            f"Current focus remains {', '.join(advisory_focus_areas[:3])}",
        )
    operator_story_reasons = [_sentence_line(row) for row in operator_story_reasons_raw[:4]]

    operator_story_actions_raw: list[str] = []
    if architecture_corpus_size > 0 and architecture_covered_count <= 0:
        _push_unique_line(
            operator_story_actions_raw,
            "Run the benchmarked architecture slice on the touched path before tightening policy further",
        )
    else:
        for row in architecture_recommendation_rows[:1]:
            _push_unique_line(operator_story_actions_raw, row)
    for row in learning_recommendation_rows[:1]:
        _push_unique_line(operator_story_actions_raw, row)
    for row in recommendation_rows[:1]:
        if str(row).strip().lower() != primary_recommendation.lower():
            _push_unique_line(operator_story_actions_raw, row)
    if advisory_focus_areas:
        _push_unique_line(
            operator_story_actions_raw,
            f"Watch {', '.join(advisory_focus_areas[:3])} on the next routed slice",
        )
    if regressions:
        _push_unique_line(operator_story_actions_raw, f"Verify regression watch: {regressions[0]}")
    operator_story_actions = [_sentence_line(row) for row in operator_story_actions_raw[:3]] or [
        "No immediate follow-up action recorded."
    ]

    decision_evidence_value = (
        f"{decision_quality_confidence_level} confidence · {decision_quality_closeout_rate:.0f}% closeout"
        if decision_quality_confidence_level.lower() != "none"
        else f"No confidence signal · {decision_quality_closeout_rate:.0f}% closeout"
    )
    architecture_fact_value = (
        f"{architecture_status_label} · {architecture_covered_count}/{architecture_corpus_size} covered"
        if architecture_corpus_size > 0 and architecture_covered_count > 0
        else (
            f"No recent benchmark evidence · {architecture_covered_count}/{architecture_corpus_size} covered"
            if architecture_corpus_size > 0
            else "No recent benchmark evidence"
        )
    )
    history_fact_value = f"{freshness_label} · {signal_label.lower()} history"
    route_fact_value = f"{round(packet_alignment_percent):.0f}% alignment · {round(route_ready_percent):.0f}% route ready"

    return {
        "contract": "odylith_drawer.v1",
        "status": "active",
        "snapshot_time": snapshot_time,
        "headline": "Maintainer cockpit for current control posture, runtime drift, and next actions.",
        "subhead": (
            "Shell-owned Telemetry cockpit: recorder tape, spend-versus-outcome drift, execution distribution, and benchmark-backed guidance from the current runtime telemetry."
        ),
        "hero_stats": [
            {
                "label": "Decision Quality",
                "value": decision_quality_state,
                "note": (
                    f"{decision_quality_score:.2f} score · {advisory_confidence_label.lower()} confidence · {evidence_strength_label.lower()} evidence"
                ),
                "percent": decision_quality_percent,
                "accent": "#7c3aed",
            },
            {
                "label": "Coverage",
                "value": _format_percent(evaluation.get("coverage_rate", 0.0)),
                "note": (
                    f'{_safe_int(evaluation.get("covered_case_count", 0), minimum=0)}/{_safe_int(evaluation.get("corpus_size", 0), minimum=0)} covered · '
                    f'{_format_percent(evaluation.get("satisfaction_rate", 0.0))} satisfaction'
                ),
                "percent": _safe_ratio_percent(evaluation.get("coverage_rate", 0.0)),
                "accent": "#2563eb",
            },
            {
                "label": "Budget Discipline",
                "value": _format_percent(optimization_packet.get("within_budget_rate", 0.0)),
                "note": (
                    f'{_format_percent(optimization_quality.get("route_ready_rate", 0.0))} route ready · '
                    f'{_format_percent(control_advisories.get("packet_alignment_rate", 0.0))} alignment'
                ),
                "percent": _safe_ratio_percent(optimization_packet.get("within_budget_rate", 0.0)),
                "accent": "#0f766e",
            },
            {
                "label": "Architecture Lane",
                "value": architecture_status_label,
                "note": (
                    f"{architecture_covered_count}/{architecture_corpus_size} covered · {architecture_satisfied_count} satisfied"
                ),
                "percent": architecture_coverage_rate,
                "accent": "#ea580c",
            },
        ],
        "meta_ribbon": [
            {"label": "Memory", "value": _humanize_display(memory_status, title_case=True) or memory_status},
            {"label": "Mode", "value": reasoning_mode_label},
            {"label": "Confidence", "value": advisory_confidence_label},
            {"label": "Evidence", "value": evidence_strength_label},
            {"label": "Freshness", "value": str(freshness_posture.get("label", "")).strip() or "Unknown"},
            {"label": "Architecture", "value": architecture_status_label},
            {
                "label": "Alignment",
                "value": _humanize_display(
                    str(control_advisories.get("packet_alignment_state", "")).strip()
                    or str(evaluation_packet_events.get("alignment_state", "")).strip(),
                    title_case=True,
                )
                or "Unknown",
            },
            {
                "label": "Yield",
                "value": _humanize_display(
                    str(control_advisories.get("yield_state", "")).strip()
                    or str(evaluation_packet_events.get("yield_state", "")).strip(),
                    title_case=True,
                )
                or "Unknown",
            },
            {
                "label": "Learning loop",
                "value": _humanize_display(str(learning_loop.get("state", "")).strip() or "cold", title_case=True) or "Cold",
            },
        ],
        "backend_summary": {
            "actual": f"{actual_storage} / {actual_sparse}",
            "target": f"{target_storage} / {target_sparse}",
            "status": _humanize_display(str(local_backend_status.get("status", "")).strip() or memory_status, title_case=True) or "Unknown",
            "gaps": backend_gap_labels,
            "entities": _safe_int(entity_counts.get("indexed_entity_count", 0), minimum=0),
            "evidence_documents": _safe_int(entity_counts.get("evidence_documents", 0), minimum=0),
            "guidance_chunks": _safe_int(guidance_catalog.get("chunk_count", 0), minimum=0),
            "active_sessions": _safe_int(runtime_state.get("active_sessions", 0), minimum=0),
            "remote_enabled": bool(remote_retrieval.get("enabled")),
            "projection_snapshot_bytes": _format_bytes(runtime_state.get("projection_snapshot_bytes", 0)),
            "architecture_bundle_bytes": _format_bytes(runtime_state.get("architecture_bundle_bytes", 0)),
            "bootstrap_packets": _safe_int(runtime_state.get("bootstrap_packets", 0), minimum=0),
        },
        "memory_areas": memory_areas,
        "judgment_memory": judgment_memory,
        "advisory_posture": {
            "reasoning_mode": reasoning_mode_label,
            "confidence": advisory_confidence_label,
            "confidence_score": _safe_int(advisory_confidence.get("score", 0), minimum=0, maximum=100),
            "evidence_strength": evidence_strength_label,
            "evidence_score": _safe_int(advisory_evidence_strength.get("score", 0), minimum=0, maximum=100),
            "decision_quality_state": decision_quality_state,
            "decision_quality_score": round(decision_quality_score, 2),
            "decision_quality_confidence_level": decision_quality_confidence_level,
            "decision_quality_confidence_score": decision_quality_confidence_score,
            "decision_quality_sample_balance": decision_quality_sample_balance,
            "closeout_observation_rate": decision_quality_closeout_rate,
            "delegation_regret_rate": decision_quality_regret_rate,
            "followup_churn_rate": decision_quality_churn_rate,
            "signal_conflict": bool(control_advisories.get("signal_conflict")),
            "focus_areas": advisory_focus_areas,
        },
        "control_posture": {
            "depth": _humanize_display(str(learning_control_posture.get("depth", "")).strip() or str(control_advisories.get("depth", "")).strip(), title_case=True) or "Balanced",
            "delegation": _humanize_display(str(learning_control_posture.get("delegation", "")).strip() or str(control_advisories.get("delegation", "")).strip(), title_case=True) or "Balanced",
            "parallelism": _humanize_display(str(learning_control_posture.get("parallelism", "")).strip() or str(control_advisories.get("parallelism", "")).strip(), title_case=True) or "Balanced",
            "packet_strategy": _humanize_display(str(learning_control_posture.get("packet_strategy", "")).strip() or str(control_advisories.get("packet_strategy", "")).strip(), title_case=True) or "Balanced",
            "budget_mode": _humanize_display(str(learning_control_posture.get("budget_mode", "")).strip() or str(control_advisories.get("budget_mode", "")).strip(), title_case=True) or "Balanced",
            "retrieval_focus": _humanize_display(str(learning_control_posture.get("retrieval_focus", "")).strip() or str(control_advisories.get("retrieval_focus", "")).strip(), title_case=True) or "Balanced",
            "speed_mode": _humanize_display(str(learning_control_posture.get("speed_mode", "")).strip() or str(control_advisories.get("speed_mode", "")).strip(), title_case=True) or "Balanced",
            "yield_state": _humanize_display(
                str(learning_control_posture.get("yield_state", "")).strip()
                or str(control_advisories.get("yield_state", "")).strip(),
                title_case=True,
            )
            or "Unknown",
            "packet_alignment_state": _humanize_display(
                str(learning_control_posture.get("packet_alignment_state", "")).strip()
                or str(control_advisories.get("packet_alignment_state", "")).strip(),
                title_case=True,
            )
            or "Unknown",
        },
        "history_posture": {
            "freshness": freshness_posture,
            "signal": signal_posture,
        },
        "latest_packet": tooling_dashboard_execution_governance_presenter.build_latest_packet_summary(
            {
                **latest_packet,
                "advised_yield_state": str(latest_packet.get("advised_yield_state", "")).strip()
                or str(control_advisories.get("yield_state", "")).strip(),
                "packet_alignment_state": str(latest_packet.get("packet_alignment_state", "")).strip()
                or str(control_advisories.get("packet_alignment_state", "")).strip(),
            }
        ),
        "recommendations": recommendation_rows,
        "learning_recommendations": learning_recommendation_rows,
        "regressions": regressions,
        "operator_story": {
            "title": operator_story_title,
            "summary": operator_story_summary,
            "facts": [
                {
                    "label": "Decision evidence",
                    "value": decision_evidence_value,
                },
                {
                    "label": "Architecture",
                    "value": architecture_fact_value,
                },
                {
                    "label": "History window",
                    "value": history_fact_value,
                },
                {
                    "label": "Current route",
                    "value": route_fact_value,
                },
            ],
            "reasons": operator_story_reasons,
            "actions": operator_story_actions,
        },
        "program_context": {
            "wave": str(evaluation_program.get("active_wave_id", "")).strip(),
            "workstream": str(evaluation_program.get("active_workstream_id", "")).strip(),
            "top_intent_family": _humanize_display(str(optimization_intent.get("top_family", "")).strip(), title_case=True),
        },
        "architecture_posture": {
            "status": architecture_status_label,
            "coverage_rate": architecture_coverage_rate,
            "satisfaction_rate": architecture_satisfaction_rate,
            "corpus_size": architecture_corpus_size,
            "covered_case_count": architecture_covered_count,
            "satisfied_case_count": architecture_satisfied_count,
            "avg_latency_ms": _format_latency_ms(architecture_posture.get("avg_latency_ms", 0.0)),
            "recommendations": architecture_recommendation_rows,
        },
        "recorder_tape": recorder_rows,
        "watchlist": watchlist_rows,
        "chart_summaries": {
            "control_story": [
                {"label": "Utility", "value": f"{reasoning_utility_average * 25.0:.0f}"},
                {"label": "Budget", "value": _format_percent(optimization_packet.get("within_budget_rate", 0.0))},
                {"label": "Alignment", "value": _format_percent(control_advisories.get("packet_alignment_rate", 0.0))},
                {"label": "Yield", "value": _format_percent(control_advisories.get("high_yield_rate", 0.0))},
            ],
            "execution_flow": [
                {"label": "Source", "value": execution_flow_source},
                {"label": "Runtime backed", "value": _format_percent(optimization_orchestration.get("runtime_backed_execution_rate", 0.0))},
                {"label": "High confidence", "value": _format_percent(optimization_orchestration.get("high_execution_confidence_rate", 0.0))},
            ],
            "signal_envelope": [
                {"label": "Density", "value": _format_score(optimization_quality.get("avg_context_density_score", 0.0))},
                {"label": "Readiness", "value": _format_score(optimization_quality.get("avg_reasoning_readiness_score", 0.0))},
                {"label": "Diversity", "value": _format_score(optimization_quality.get("avg_evidence_diversity_score", 0.0))},
                {"label": "Utility", "value": f"{reasoning_utility_average * 25.0:.0f}"},
            ],
            "control_calibration": [
                {"label": "Closeout", "value": _format_percent(evaluation_decision_quality.get("closeout_observation_rate", 0.0))},
                {"label": "Confidence", "value": f"{decision_quality_confidence_score}/4"},
                {"label": "Alignment", "value": _format_percent(control_advisories.get("packet_alignment_rate", 0.0))},
                {
                    "label": "Yield",
                    "value": _format_percent(
                        evaluation_packet_events.get(
                            "avg_effective_yield_score",
                            optimization_quality.get("avg_effective_yield_score", 0.0),
                        )
                    ),
                },
                {"label": "Architecture", "value": _format_percent(architecture_posture.get("satisfaction_rate", 0.0))},
            ],
        },
        "charts": {
            "control_story": {
                "mode": control_story_mode,
                "sample_count": control_story_sample_count,
                "note": control_story_note,
                "labels": reasoning_labels or ["P1"],
                "tokens": reasoning_tokens or [0],
                "utility": [round(_safe_float(value, minimum=0.0, maximum=4.0) * 25.0, 1) for value in reasoning_utility] or [0],
                "alignment": reasoning_alignment or [0],
                "yield": reasoning_yield or [0],
                "route_ready": reasoning_route_ready or [0],
                "detail": control_story_detail,
            },
            "execution_flow": {
                "labels": execution_flow_labels,
                "values": execution_flow_values,
                "source": execution_flow_source,
            },
            "signal_envelope": {
                "labels": reasoning_labels or ["P1"],
                "density": signal_density,
                "readiness": signal_readiness,
                "diversity": signal_diversity,
                "utility": signal_utility,
            },
            "control_calibration": {
                "labels": control_calibration_labels,
                "values": control_calibration_values,
                "source": "Evaluation + advisory",
            },
        },
    }


def _render_odylith_chart_fallback_for_drawer(chart_key: str, drawer_payload: Mapping[str, Any]) -> str:
    charts = dict(drawer_payload.get("charts", {})) if isinstance(drawer_payload.get("charts"), Mapping) else {}
    history_posture = (
        dict(drawer_payload.get("history_posture", {}))
        if isinstance(drawer_payload.get("history_posture"), Mapping)
        else {}
    )
    freshness = dict(history_posture.get("freshness", {})) if isinstance(history_posture.get("freshness"), Mapping) else {}
    signal = dict(history_posture.get("signal", {})) if isinstance(history_posture.get("signal"), Mapping) else {}
    freshness_label = str(freshness.get("label", "")).strip() or "Unknown"
    signal_label = str(signal.get("label", "")).strip() or "Unknown"
    caption = f"Static fallback from the current drawer contract. Freshness {freshness_label} · History {signal_label}."

    if chart_key == "control-story":
        chart = dict(charts.get("control_story", {})) if isinstance(charts.get("control_story"), Mapping) else {}
        mode = str(chart.get("mode", "")).strip().lower()
        if mode == "snapshot":
            return _render_odylith_control_story_snapshot_fallback(
                detail=dict(chart.get("detail", {})) if isinstance(chart.get("detail"), Mapping) else {},
                caption=f"{caption} Single routed slice available; rendering snapshot mode.",
            )
        if mode == "lollipop":
            detail = dict(chart.get("detail", {})) if isinstance(chart.get("detail"), Mapping) else {}
            latest_tokens = _safe_int(detail.get("tokens", 0), minimum=0, maximum=250000)
            token_delta = detail.get("token_delta")
            delta_suffix = ""
            if token_delta is not None:
                delta_value = _safe_float(token_delta, minimum=-250000.0, maximum=250000.0)
                delta_suffix = f" Latest spend {latest_tokens:,} tokens ({delta_value:+.0f} vs prior slice)."
            return _render_odylith_line_chart_svg(
                series=(
                    ("Utility", chart.get("utility", []), "#2dd4bf"),
                    ("Alignment", chart.get("alignment", []), "#60a5fa"),
                    ("Yield", chart.get("yield", []), "#f59e0b"),
                    ("Route ready", chart.get("route_ready", []), "#38bdf8"),
                ),
                max_value=100.0,
                caption=f"{caption} Short history window; rendering delta mode.{delta_suffix}",
            )
        note = str(chart.get("note", "")).strip()
        return _render_odylith_control_story_trend_fallback(
            labels=chart.get("labels", []),
            bars=chart.get("tokens", []),
            signal_series=(
                ("Utility", chart.get("utility", []), "#2dd4bf"),
                ("Alignment", chart.get("alignment", []), "#60a5fa"),
                ("Yield", chart.get("yield", []), "#f59e0b"),
                ("Route ready", chart.get("route_ready", []), "#38bdf8"),
            ),
            caption=f"{caption} {note}".strip(),
        )
    if chart_key == "execution-flow":
        chart = dict(charts.get("execution_flow", {})) if isinstance(charts.get("execution_flow"), Mapping) else {}
        return _render_odylith_bar_line_chart_svg(
            bars=chart.get("values", []),
            lines=(),
            caption=caption,
        )
    if chart_key == "reasoning-envelope":
        chart = dict(charts.get("reasoning_envelope", {})) if isinstance(charts.get("reasoning_envelope"), Mapping) else {}
        return _render_odylith_line_chart_svg(
            series=(
                ("Density", chart.get("density", []), "#60a5fa"),
                ("Readiness", chart.get("readiness", []), "#a78bfa"),
                ("Diversity", chart.get("diversity", []), "#f59e0b"),
                ("Utility", chart.get("utility", []), "#2dd4bf"),
            ),
            max_value=4.0,
            caption=caption,
        )
    if chart_key == "budget-pressure":
        chart = dict(charts.get("budget_pressure", {})) if isinstance(charts.get("budget_pressure"), Mapping) else {}
        return _render_odylith_bar_line_chart_svg(
            bars=chart.get("tokens", []),
            lines=(
                ("Within budget", chart.get("within_budget", []), "#2dd4bf"),
                ("Route ready", chart.get("route_ready", []), "#38bdf8"),
                ("Spawn ready", chart.get("spawn_ready", []), "#c084fc"),
            ),
            caption=caption,
        )
    if chart_key == "execution-mix":
        chart = dict(charts.get("execution_mix", {})) if isinstance(charts.get("execution_mix"), Mapping) else {}
        return _render_odylith_donut_chart_svg(
            labels=chart.get("labels", []),
            values=chart.get("values", []),
            colors=("#7dd3fc", "#a78bfa", "#34d399", "#fb7185", "#f59e0b", "#60a5fa"),
            caption=caption,
        )
    if chart_key == "signal-envelope":
        chart = dict(charts.get("signal_envelope", {})) if isinstance(charts.get("signal_envelope"), Mapping) else {}
        return _render_odylith_line_chart_svg(
            series=(
                ("Density", chart.get("density", []), "#60a5fa"),
                ("Readiness", chart.get("readiness", []), "#a78bfa"),
                ("Diversity", chart.get("diversity", []), "#f59e0b"),
                ("Utility", chart.get("utility", []), "#2dd4bf"),
            ),
            max_value=100.0,
            caption=caption,
        )
    if chart_key == "control-calibration":
        chart = dict(charts.get("control_calibration", {})) if isinstance(charts.get("control_calibration"), Mapping) else {}
        return _render_odylith_bar_line_chart_svg(
            bars=chart.get("values", []),
            lines=(),
            caption=caption,
        )
    if chart_key == "learning-loop":
        chart = dict(charts.get("learning_loop", {})) if isinstance(charts.get("learning_loop"), Mapping) else {}
        return _render_odylith_line_chart_svg(
            series=(
                ("Packet satisfaction", chart.get("packet", []), "#60a5fa"),
                ("Packet Alignment", chart.get("alignment", []), "#f59e0b"),
                ("Evidence yield", chart.get("yield", []), "#2dd4bf"),
                ("Router acceptance", chart.get("router", []), "#c084fc"),
                ("Orchestration efficiency", chart.get("orchestration", []), "#34d399"),
            ),
            max_value=100.0,
            caption=caption,
        )
    chart = dict(charts.get("reasoning_radar", {})) if isinstance(charts.get("reasoning_radar"), Mapping) else {}
    return _render_odylith_radar_chart_svg(
        labels=chart.get("labels", []),
        values=chart.get("values", []),
        caption=caption,
    )


def _render_curated_system_status_html(drawer_payload: Mapping[str, Any]) -> str:
    return ""

    if str(drawer_payload.get("status", "")).strip() == "disabled":
        note = str(drawer_payload.get("note", "")).strip() or "Odylith runtime telemetry is not available for this comparison run."
        return (
            '<section class="system-status-strip" aria-label="Shell ablation status">'
            '<article class="system-status-card">'
            '<p class="system-status-label">Ablation Mode</p>'
            '<p class="system-status-value">odylith disabled</p>'
            f'<p class="system-status-copy">{html.escape(note)}</p>'
            "</article>"
            "</section>"
        )

    def _render_pair_chip(*, css_class: str, label: str, value: str, tooltip: str = "") -> str:
        chip_label = str(label or "").strip()
        chip_value = str(value or "").strip()
        if not chip_label and not chip_value:
            return ""
        aria_label = f"{chip_label} {chip_value}".strip()
        return (
            f'<span class="{css_class} odylith-pair-chip"{_tooltip_attrs(tooltip, aria_label=aria_label)}>'
            f'<span class="odylith-pair-label">{html.escape(chip_label)}</span>'
            f'<span class="odylith-pair-value">{html.escape(chip_value)}</span>'
            "</span>"
        )

    def _render_pair_row(
        items: Sequence[tuple[str, str, str]],
        *,
        wrapper_class: str,
        item_class: str,
    ) -> str:
        rendered = [
            _render_pair_chip(css_class=item_class, label=label, value=value, tooltip=tooltip)
            for label, value, tooltip in items
            if str(label).strip() or str(value).strip()
        ]
        rendered = [row for row in rendered if row]
        return f'<div class="{wrapper_class}">{"".join(rendered)}</div>' if rendered else ""

    snapshot_time = str(drawer_payload.get("snapshot_time", "")).strip() or "unknown"
    hero_stats_rows = [
        dict(row)
        for row in drawer_payload.get("hero_stats", [])
        if isinstance(row, Mapping)
    ] if isinstance(drawer_payload.get("hero_stats"), list) else []
    meta_ribbon_rows = [
        dict(row)
        for row in drawer_payload.get("meta_ribbon", [])
        if isinstance(row, Mapping)
    ] if isinstance(drawer_payload.get("meta_ribbon"), list) else []
    drawer_backend = dict(drawer_payload.get("backend_summary", {})) if isinstance(drawer_payload.get("backend_summary"), Mapping) else {}
    drawer_memory_areas = dict(drawer_payload.get("memory_areas", {})) if isinstance(drawer_payload.get("memory_areas"), Mapping) else {}
    drawer_judgment_memory = dict(drawer_payload.get("judgment_memory", {})) if isinstance(drawer_payload.get("judgment_memory"), Mapping) else {}
    drawer_control = dict(drawer_payload.get("control_posture", {})) if isinstance(drawer_payload.get("control_posture"), Mapping) else {}
    drawer_charts = dict(drawer_payload.get("charts", {})) if isinstance(drawer_payload.get("charts"), Mapping) else {}
    drawer_program_context = dict(drawer_payload.get("program_context", {})) if isinstance(drawer_payload.get("program_context"), Mapping) else {}
    drawer_advisory = dict(drawer_payload.get("advisory_posture", {})) if isinstance(drawer_payload.get("advisory_posture"), Mapping) else {}
    drawer_architecture = dict(drawer_payload.get("architecture_posture", {})) if isinstance(drawer_payload.get("architecture_posture"), Mapping) else {}
    drawer_history_posture = dict(drawer_payload.get("history_posture", {})) if isinstance(drawer_payload.get("history_posture"), Mapping) else {}
    drawer_operator_story = dict(drawer_payload.get("operator_story", {})) if isinstance(drawer_payload.get("operator_story"), Mapping) else {}
    drawer_freshness = dict(drawer_history_posture.get("freshness", {})) if isinstance(drawer_history_posture.get("freshness"), Mapping) else {}
    drawer_signal = dict(drawer_history_posture.get("signal", {})) if isinstance(drawer_history_posture.get("signal"), Mapping) else {}
    drawer_regressions = [str(token).strip() for token in drawer_payload.get("regressions", []) if str(token).strip()] if isinstance(drawer_payload.get("regressions"), list) else []
    drawer_recommendations = [str(token).strip() for token in drawer_payload.get("recommendations", []) if str(token).strip()] if isinstance(drawer_payload.get("recommendations"), list) else []
    drawer_learning_recommendations = [str(token).strip() for token in drawer_payload.get("learning_recommendations", []) if str(token).strip()] if isinstance(drawer_payload.get("learning_recommendations"), list) else []
    drawer_recorder = [dict(row) for row in drawer_payload.get("recorder_tape", []) if isinstance(row, Mapping)] if isinstance(drawer_payload.get("recorder_tape"), list) else []
    drawer_control_story = dict(drawer_charts.get("control_story", {})) if isinstance(drawer_charts.get("control_story"), Mapping) else {}
    drawer_execution_flow = dict(drawer_charts.get("execution_flow", {})) if isinstance(drawer_charts.get("execution_flow"), Mapping) else {}
    drawer_backend_gaps = [
        str(token).strip()
        for token in drawer_backend.get("gaps", [])
        if str(token).strip()
    ] if isinstance(drawer_backend.get("gaps"), list) else []
    drawer_memory_area_rows = [
        dict(row)
        for row in drawer_memory_areas.get("areas", [])
        if isinstance(row, Mapping)
    ] if isinstance(drawer_memory_areas.get("areas"), list) else []
    drawer_memory_live_rows = [
        row
        for row in drawer_memory_area_rows
        if str(row.get("state", "")).strip().lower() in {"strong", "partial", "cold"}
    ] or drawer_memory_area_rows[:5]
    drawer_memory_gaps = [
        str(token).strip()
        for token in drawer_memory_areas.get("gaps", [])
        if str(token).strip()
    ] if isinstance(drawer_memory_areas.get("gaps"), list) else []
    drawer_judgment_rows = [
        dict(row)
        for row in drawer_judgment_memory.get("areas", [])
        if isinstance(row, Mapping)
    ] if isinstance(drawer_judgment_memory.get("areas"), list) else []
    drawer_judgment_live_rows = [
        row
        for row in drawer_judgment_rows
        if str(row.get("state", "")).strip().lower() in {"strong", "partial", "cold"}
    ] or drawer_judgment_rows[:5]
    drawer_judgment_gaps = [
        str(token).strip()
        for token in drawer_judgment_memory.get("gaps", [])
        if str(token).strip()
    ] if isinstance(drawer_judgment_memory.get("gaps"), list) else []
    recorder_peak_tokens = max(
        (_safe_int(row.get("tokens", 0), minimum=0, maximum=250000) for row in drawer_recorder),
        default=0,
    )
    recorder_peak_tokens = max(recorder_peak_tokens, 1)

    def _render_recorder_item(row: Mapping[str, Any]) -> str:
        token_count = _safe_int(row.get("tokens", 0), minimum=0, maximum=250000)
        budget_percent = _safe_int(row.get("budget_percent", 0), minimum=0, maximum=100)
        budget_tone = str(row.get("budget_tone", "")).strip().lower()
        if budget_tone not in {"steady", "watch", "risk"}:
            budget_tone = "steady"
        budget_label = str(row.get("budget_label", "")).strip() or "Budget posture unavailable"
        operator_call = str(row.get("operator_call", "")).strip() or "Watch"
        operator_summary = str(row.get("operator_summary", "")).strip() or "Signals are mixed. Hold the current posture until one more slice confirms direction."
        operator_tone = str(row.get("operator_tone", "")).strip().lower()
        if operator_tone not in {"keep", "watch", "intervene"}:
            operator_tone = "watch"
        spend_percent = min(100.0, max(0.0, (token_count / recorder_peak_tokens) * 100.0))
        spend_percent = max(spend_percent, 6.0) if token_count > 0 else 0.0
        meta_tokens = [
            str(row.get("packet_strategy", "")).strip(),
            f'WS {str(row.get("workstream", "")).strip()}' if str(row.get("workstream", "")).strip() else "",
            str(row.get("session_id", "")).strip(),
        ]
        meta_text = " · ".join(token for token in meta_tokens if token)
        signal_rows = (
            ("Utility", _safe_int(row.get("utility_percent", 0), minimum=0, maximum=100), "Latest packet utility signal.", "utility"),
            ("Alignment", _safe_int(row.get("alignment_percent", 0), minimum=0, maximum=100), "Advisory alignment score.", "alignment"),
            ("Budget fit", budget_percent, "Within-budget score.", "budget"),
            ("Route ready", _safe_int(row.get("route_ready", 0), minimum=0, maximum=100), "Route-readiness score.", "route"),
        )
        signals_html = "".join(
            (
                f'<div class="odylith-recorder-signal-row"{_tooltip_attrs(f"{tooltip} {value}/100.", aria_label=f"{label} {value} out of 100.")}>'
                f'<span class="odylith-recorder-signal-label">{html.escape(label)}</span>'
                '<span class="odylith-recorder-signal-track">'
                f'<span class="odylith-recorder-signal-fill odylith-recorder-signal-fill-{css_suffix}" style="width: {value:.1f}%"></span>'
                '</span>'
                '</div>'
            )
            for label, value, tooltip, css_suffix in signal_rows
        )
        return (
            f'<article class="odylith-recorder-item odylith-recorder-item-budget-{budget_tone}">'
            '<div class="odylith-recorder-item-head">'
            '<div class="odylith-recorder-item-identity">'
            f'<p class="odylith-recorder-item-label">{html.escape(str(row.get("label", "")).strip() or "Latest")}</p>'
            f'<p class="odylith-recorder-item-state">{html.escape(str(row.get("state", "")).strip() or "Unknown")}</p>'
            '</div>'
            f'<p class="odylith-recorder-item-time">{html.escape(str(row.get("recorded_at", "")).strip() or snapshot_time)}</p>'
            '</div>'
            + (
                f'<p class="odylith-recorder-item-meta">{html.escape(meta_text)}</p>'
                if meta_text
                else ""
            )
            + f'<div class="odylith-recorder-guidance odylith-recorder-guidance-{operator_tone}"{_tooltip_attrs(operator_summary, aria_label=f"{operator_call}. {operator_summary}")}>'
            + f'<p class="odylith-recorder-guidance-label">{html.escape(operator_call)}</p>'
            + f'<p class="odylith-recorder-guidance-copy">{html.escape(operator_summary)}</p>'
            + '</div>'
            + '<div class="odylith-recorder-ledger">'
            + f'<div class="odylith-recorder-spend-lane"{_tooltip_attrs(f"{token_count:,} tokens. {budget_label}. Scaled to the visible recorder window peak of {recorder_peak_tokens:,} tokens.", aria_label=f"Spend {token_count:,} tokens. {budget_label}.")}>'
            + '<div class="odylith-recorder-lane-head">'
            + '<span class="odylith-recorder-lane-label">Spend</span>'
            + f'<span class="odylith-recorder-lane-copy">{token_count:,} tokens · {html.escape(budget_label)}</span>'
            + '</div>'
            + '<span class="odylith-recorder-spend-track">'
            + f'<span class="odylith-recorder-spend-fill" style="width: {spend_percent:.1f}%"></span>'
            + '</span>'
            + '</div>'
            + '<div class="odylith-recorder-signal-strip" aria-label="Packet signals">'
            + signals_html
            + '</div>'
            + '</div>'
            '</article>'
        )

    hero_overview = "".join(
        (
            _token_label_html(
                css_class="system-status-hero-chip",
                text=snapshot_time,
                tooltip="Snapshot timestamp for this Telemetry drawer render.",
                aria_label=f"{snapshot_time}. Snapshot timestamp for this Telemetry drawer render.",
            ),
            _token_label_html(
                css_class="system-status-hero-chip",
                text=f'Mode {str(drawer_advisory.get("reasoning_mode", "")).strip() or "Unknown"}',
                tooltip="Current control-advisory reasoning mode.",
            ),
            _token_label_html(
                css_class="system-status-hero-chip",
                text=f'Confidence {str(drawer_advisory.get("confidence", "")).strip() or "Unknown"}',
                tooltip="Current advisory confidence posture.",
            ),
            _token_label_html(
                css_class="system-status-hero-chip",
                text=f'Architecture {str(drawer_architecture.get("status", "")).strip() or "Unknown"}',
                tooltip="Architecture benchmark lane posture from the latest runtime evaluation snapshot.",
            ),
            _token_label_html(
                css_class="system-status-hero-chip",
                text=f'Freshness {str(drawer_freshness.get("label", "")).strip() or "Unknown"}',
                tooltip=str(drawer_freshness.get("note", "")).strip(),
            ),
        )
    )
    hero_stats = "".join(
        _telemetry_stat_card_html(
            label=str(row.get("label", "")).strip() or "Metric",
            value_text=str(row.get("value", "")).strip() or "Unknown",
            note=str(row.get("note", "")).strip() or "No note available.",
            meter_percent=_safe_float(row.get("percent", None), minimum=0.0, maximum=100.0) if row.get("percent") is not None else None,
            accent=str(row.get("accent", "")).strip() or "#2563eb",
        )
        for row in hero_stats_rows
    )
    drawer_meta_ribbon_html = "".join(
        _render_pair_chip(
            css_class="odylith-command-pill",
            label=str(row.get("label", "")).strip(),
            value=str(row.get("value", "")).strip(),
        )
        for row in meta_ribbon_rows
    )

    backend_metrics_html = _render_pair_row(
        (
            ("Entities", f'{_safe_int(drawer_backend.get("entities", 0), minimum=0):,}', "Entities currently indexed in the local telemetry projection."),
            ("Evidence", f'{_safe_int(drawer_backend.get("evidence_documents", 0), minimum=0):,}', "Typed evidence documents retained in the current local memory backend."),
            ("Guidance", f'{_safe_int(drawer_backend.get("guidance_chunks", 0), minimum=0):,}', "Compiled guidance chunks available to shape packet retention."),
            ("Projection", str(drawer_backend.get("projection_snapshot_bytes", "")).strip() or "0 B", "Projection snapshot footprint."),
            ("Arch bundle", str(drawer_backend.get("architecture_bundle_bytes", "")).strip() or "0 B", "Architecture bundle footprint."),
            ("Bootstrap", str(_safe_int(drawer_backend.get("bootstrap_packets", 0), minimum=0)), "Bootstrap packets currently retained in local runtime state."),
            ("Sessions", str(_safe_int(drawer_backend.get("active_sessions", 0), minimum=0)), "Active shell sessions currently attached to the local runtime."),
            ("Gaps", str(len(drawer_backend_gaps)), ("Remaining target backend gaps: " + _display_list_text(tuple(drawer_backend_gaps))) if drawer_backend_gaps else "No target backend gaps remain."),
        ),
        wrapper_class="odylith-inline-metric-row",
        item_class="odylith-inline-metric",
    )
    memory_area_counts = dict(drawer_memory_areas.get("counts", {})) if isinstance(drawer_memory_areas.get("counts"), Mapping) else {}
    memory_count_text = ", ".join(
        f"{_humanize_display(label, title_case=True) or label} {count}"
        for label in ("strong", "partial", "cold", "planned", "disabled")
        if (count := _safe_int(memory_area_counts.get(label, 0), minimum=0)) > 0
    ) or "No memory area counts recorded."
    memory_area_facts_html = "".join(
        "".join(
            (
                '<div class="odylith-summary-fact">',
                f'<dt class="odylith-summary-fact-label">{html.escape(str(row.get("label", "")).strip() or "Memory area")}</dt>',
                f'<dd class="odylith-summary-fact-value">{html.escape((_humanize_display(str(row.get("state", "")).strip(), title_case=True) or "Unknown") + " · " + (str(row.get("summary", "")).strip() or "No summary available."))}</dd>',
                '</div>',
            )
        )
        for row in drawer_memory_live_rows[:5]
    )
    memory_areas_html = (
        '<section class="odylith-backend-card" aria-label="Odylith memory areas">'
        '<div class="odylith-backend-card-head">'
        '<p class="odylith-command-card-kicker">Memory Areas</p>'
        f'<p class="odylith-command-card-title">{html.escape(str(drawer_memory_areas.get("headline", "")).strip() or "No memory-area headline available.")}</p>'
        '</div>'
        f'<p class="odylith-command-card-copy">{html.escape(memory_count_text)}</p>'
        + (
            f'<dl class="odylith-summary-facts">{memory_area_facts_html}</dl>'
            if memory_area_facts_html
            else '<p class="odylith-command-card-copy">No memory-area details recorded.</p>'
        )
        + '<div class="odylith-summary-section">'
        + '<p class="odylith-summary-section-title">Gaps To Close</p>'
        + '<ul class="odylith-signal-list">'
        + "".join(f"<li>{html.escape(row)}</li>" for row in (drawer_memory_gaps[:4] or ["No explicit memory gaps recorded."]))
        + '</ul></div>'
        + '</section>'
    )
    judgment_counts = dict(drawer_judgment_memory.get("counts", {})) if isinstance(drawer_judgment_memory.get("counts"), Mapping) else {}
    judgment_count_text = ", ".join(
        f"{_humanize_display(label, title_case=True) or label} {count}"
        for label in ("strong", "partial", "cold", "planned", "disabled")
        if (count := _safe_int(judgment_counts.get(label, 0), minimum=0)) > 0
    ) or "No judgment memory counts recorded."
    judgment_facts_html = "".join(
        "".join(
            (
                '<div class="odylith-summary-fact">',
                f'<dt class="odylith-summary-fact-label">{html.escape(str(row.get("label", "")).strip() or "Judgment area")}</dt>',
                f'<dd class="odylith-summary-fact-value">{html.escape((_humanize_display(str(row.get("state", "")).strip(), title_case=True) or "Unknown") + " · " + (str(row.get("summary", "")).strip() or "No summary available."))}</dd>',
                '</div>',
            )
        )
        for row in drawer_judgment_live_rows[:5]
    )
    judgment_memory_html = (
        '<section class="odylith-backend-card" aria-label="Odylith judgment memory">'
        '<div class="odylith-backend-card-head">'
        '<p class="odylith-command-card-kicker">Judgment Memory</p>'
        f'<p class="odylith-command-card-title">{html.escape(str(drawer_judgment_memory.get("headline", "")).strip() or "No judgment-memory headline available.")}</p>'
        '</div>'
        f'<p class="odylith-command-card-copy">{html.escape(judgment_count_text)}</p>'
        + (
            f'<dl class="odylith-summary-facts">{judgment_facts_html}</dl>'
            if judgment_facts_html
            else '<p class="odylith-command-card-copy">No judgment-memory details recorded.</p>'
        )
        + '<div class="odylith-summary-section">'
        + '<p class="odylith-summary-section-title">Gaps To Close</p>'
        + '<ul class="odylith-signal-list">'
        + "".join(f"<li>{html.escape(row)}</li>" for row in (drawer_judgment_gaps[:4] or ["No explicit judgment-memory gaps recorded."]))
        + '</ul></div>'
        + '</section>'
    )

    story_facts = [
        dict(row)
        for row in drawer_operator_story.get("facts", [])
        if isinstance(row, Mapping) and (str(row.get("label", "")).strip() or str(row.get("value", "")).strip())
    ] if isinstance(drawer_operator_story.get("facts"), list) else []
    story_reasons = [
        str(row).strip()
        for row in drawer_operator_story.get("reasons", [])
        if str(row).strip()
    ] if isinstance(drawer_operator_story.get("reasons"), list) else []
    story_actions = [
        str(row).strip()
        for row in drawer_operator_story.get("actions", [])
        if str(row).strip()
    ] if isinstance(drawer_operator_story.get("actions"), list) else []
    story_facts_html = "".join(
        "".join(
            (
                '<div class="odylith-summary-fact">',
                f'<dt class="odylith-summary-fact-label">{html.escape(str(row.get("label", "")).strip() or "Signal")}</dt>',
                f'<dd class="odylith-summary-fact-value">{html.escape(str(row.get("value", "")).strip() or "Unknown")}</dd>',
                '</div>',
            )
        )
        for row in story_facts
    )
    summary_card_html = (
        '<article class="odylith-summary-card">'
        '<p class="odylith-command-card-kicker">Maintainer Verdict</p>'
        f'<p class="odylith-command-card-title">{html.escape(str(drawer_operator_story.get("title", "")).strip() or "No clear recommendation available.")}</p>'
        f'<p class="odylith-command-card-copy">{html.escape(str(drawer_operator_story.get("summary", "")).strip() or "Current posture is derived from the latest advisory, history, and architecture telemetry.")}</p>'
        + (f'<dl class="odylith-summary-facts">{story_facts_html}</dl>' if story_facts_html else "")
        + '<div class="odylith-summary-section">'
        + '<p class="odylith-summary-section-title">Why This Call</p>'
        + '<ul class="odylith-signal-list">'
        + "".join(f"<li>{html.escape(row)}</li>" for row in (story_reasons or ["No rationale captured."]))
        + '</ul></div>'
        + '<div class="odylith-summary-section">'
        + '<p class="odylith-summary-section-title">Next Actions</p>'
        + '<ul class="odylith-signal-list">'
        + "".join(f"<li>{html.escape(row)}</li>" for row in (story_actions or ["No immediate follow-up action recorded."]))
        + '</ul></div>'
        + '</article>'
    )
    latest_packet_card_html = tooling_dashboard_execution_governance_presenter.render_latest_packet_html(
        dict(drawer_payload.get("latest_packet", {})) if isinstance(drawer_payload.get("latest_packet"), Mapping) else {}
    )

    recorder_note = (
        "Only one recent slice is available. Use it to decide whether to keep the current posture or intervene before more spend."
        if str(drawer_signal.get("label", "")).strip().lower() == "sparse"
        else "Read this top to bottom. Intervene on rows that are over budget, weakly aligned, or not route-ready; keep the current posture when spend stays controlled and the signals stay strong."
    )
    recorder_html = (
        '<section class="odylith-recorder-shell" aria-label="Telemetry recorder tape">'
        '<div class="odylith-recorder-head">'
        '<div class="odylith-recorder-copy">'
        '<p class="odylith-recorder-kicker">Recorder Tape</p>'
        '<h3 class="odylith-recorder-title">What recent routed slices need from you.</h3>'
        '</div>'
        f'<p class="odylith-recorder-note">{html.escape(recorder_note)}</p>'
        '</div>'
        f'<div class="odylith-recorder-tape">{"".join(_render_recorder_item(row) for row in drawer_recorder[:8])}</div>'
        '</section>'
    )

    cockpit_grid_html = "".join(
        (
            '<section class="odylith-command-strip" aria-label="Telemetry control strip">',
            f'<div class="odylith-command-ribbon">{drawer_meta_ribbon_html}</div>',
            '</section>',
            '<section class="odylith-cockpit-grid" aria-label="Telemetry maintainer cockpit">',
            '<article class="odylith-visual-card odylith-visual-card-wide">',
            '<div class="odylith-visual-card-head">',
            '<div class="odylith-visual-card-copy">',
            '<p class="odylith-visual-card-kicker">Control Story</p>',
            '<h3 class="odylith-visual-card-title">Spend and packet outcome signals across the latest routed window.</h3>',
            '</div>',
            f'<p class="odylith-visual-card-note">{html.escape(str(drawer_control_story.get("note", "")).strip() or "Spend lane above; outcome signals below.")}</p>',
            '</div>',
            _render_odylith_chart_canvas(
                chart_key="control-story",
                aria_label="Telemetry control story chart",
                fallback_html=_render_odylith_chart_fallback_for_drawer("control-story", drawer_payload),
            ),
            '</article>',
            '<article class="odylith-visual-card">',
            '<div class="odylith-visual-card-head">',
            '<div class="odylith-visual-card-copy">',
            '<p class="odylith-visual-card-kicker">Execution Posture</p>',
            '<h3 class="odylith-visual-card-title">Routed distribution from the richest live execution lane.</h3>',
            '</div>',
            f'<p class="odylith-visual-card-note">Source {html.escape(str(drawer_execution_flow.get("source", "")).strip() or "No distribution")}.</p>',
            '</div>',
            _render_odylith_chart_canvas(
                chart_key="execution-flow",
                aria_label="Telemetry execution flow chart",
                fallback_html=_render_odylith_chart_fallback_for_drawer("execution-flow", drawer_payload),
            ),
            '</article>',
            '<article class="odylith-visual-card">',
            '<div class="odylith-visual-card-head">',
            '<div class="odylith-visual-card-copy">',
            '<p class="odylith-visual-card-kicker">Packet Signals</p>',
            '<h3 class="odylith-visual-card-title">Density, readiness, diversity, and utility across the routed tape.</h3>',
            '</div>',
            '<p class="odylith-visual-card-note">Live packet signal scores, not stale status prose.</p>',
            '</div>',
            _render_odylith_chart_canvas(
                chart_key="signal-envelope",
                aria_label="Telemetry packet signal envelope chart",
                fallback_html=_render_odylith_chart_fallback_for_drawer("signal-envelope", drawer_payload),
            ),
            '</article>',
            '<article class="odylith-visual-card odylith-visual-card-wide">',
            '<div class="odylith-visual-card-head">',
            '<div class="odylith-visual-card-copy">',
            '<p class="odylith-visual-card-kicker">Control Calibration</p>',
            '<h3 class="odylith-visual-card-title">Measured closeout, confidence, alignment, yield, and architecture fit.</h3>',
            '</div>',
            '<p class="odylith-visual-card-note">Decision-quality and benchmark telemetry condensed into one maintainer lane.</p>',
            '</div>',
            _render_odylith_chart_canvas(
                chart_key="control-calibration",
                aria_label="Telemetry control calibration chart",
                fallback_html=_render_odylith_chart_fallback_for_drawer("control-calibration", drawer_payload),
            ),
            '</article>',
            summary_card_html,
            latest_packet_card_html,
            '</section>',
            '<section class="odylith-backend-card" aria-label="Telemetry backend footprint">',
            '<div class="odylith-backend-card-head">',
            '<p class="odylith-command-card-kicker">Backend Footprint</p>',
            f'<p class="odylith-command-card-title">{html.escape(str(drawer_backend.get("actual", "")).strip() or "Current backend unavailable")}</p>',
            '</div>',
            f'<p class="odylith-command-card-copy">Target {html.escape(str(drawer_backend.get("target", "")).strip() or "-")} · {html.escape(str(drawer_backend.get("status", "")).strip() or "Unknown")} · {html.escape(str(drawer_program_context.get("top_intent_family", "")).strip() or "Unknown")} intent family.</p>',
            f"{backend_metrics_html}"
            '</section>',
            memory_areas_html,
            judgment_memory_html,
        )
    )

    return (
        '<section class="system-status-shell" aria-label="Telemetry runtime status">'
        '<section class="system-status-hero">'
        '<div class="system-status-hero-copy">'
        '<p class="system-status-hero-kicker">Telemetry Snapshot</p>'
        f'<p class="system-status-hero-title">{html.escape(str(drawer_payload.get("headline", "")).strip() or "Render-time telemetry for the shared shell runtime.")}</p>'
        f'<p class="system-status-hero-note">{html.escape(str(drawer_payload.get("subhead", "")).strip() or "Dense runtime telemetry for the shared shell.")}</p>'
        f'<div class="system-status-hero-chip-row">{hero_overview}</div>'
        '</div>'
        f'<div class="system-status-hero-aside system-status-hero-gauges"><div class="telemetry-stat-grid">{hero_stats}</div></div>'
        '</section>'
        + recorder_html
        + cockpit_grid_html
        + '</section>'
    )


def build_template_context(payload: Mapping[str, Any]) -> tooling_dashboard_template_context.ToolingDashboardTemplateContext:
    """Build the reusable template context for one tooling shell render."""

    maintainer_notes_html = _render_maintainer_notes_html(_coerce_maintainer_notes(payload) or _default_maintainer_notes())
    cheatsheet_html = tooling_dashboard_cheatsheet_presenter.render_agent_cheatsheet_html(payload)
    system_status_html = tooling_dashboard_system_status_presenter.render_system_status_html(
        payload,
        odylith_switch=_odylith_switch(payload),
        build_drawer_payload=lambda _payload: {},
        render_curated_system_status_html=lambda _payload: "",
    )
    return tooling_dashboard_template_context.build_template_context(
        payload,
        welcome_html=_render_welcome_state_html(payload),
        system_status_html=system_status_html,
        maintainer_notes_html=maintainer_notes_html,
        cheatsheet_html=cheatsheet_html,
    )



def render_html(payload: Mapping[str, Any]) -> str:
    """Render the tooling shell HTML from a prepared payload."""

    context = build_template_context(payload)
    return dashboard_template_runtime.render_template(
        "tooling_dashboard/page.html.j2",
        **asdict(context),
    )
