"""Pure release-spotlight rendering for the tooling dashboard shell."""

from __future__ import annotations

import html
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from typing import Any

from odylith.common.release_text import normalize_release_text as _normalize_release_copy


def _coerce_release_spotlight(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Extract the release spotlight block when the payload contains one."""
    return dict(payload.get("release_spotlight", {})) if isinstance(payload.get("release_spotlight"), Mapping) else {}


def _format_version_label(value: Any) -> str:
    """Normalize release version labels for operator-facing display."""
    token = str(value or "").strip()
    if not token:
        return ""
    return token if not token[:1].isdigit() else f"v{token}"


def _parse_timestamp(value: Any) -> datetime | None:
    """Parse ISO-like timestamps into UTC datetimes when possible."""
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


def _format_timestamp_utc(value: Any) -> str:
    """Render timestamps in a stable UTC label for the dashboard shell."""
    parsed = _parse_timestamp(value)
    if parsed is None:
        token = str(value or "").strip()
        return token or "unknown"
    return parsed.strftime("%Y-%m-%d %H:%M UTC")


def _release_story_title(story: Mapping[str, Any]) -> str:
    """Return the best available title for the spotlight story."""
    return _normalize_release_copy(story.get("title") or "") or _format_version_label(
        story.get("release_tag") or story.get("to_version")
    )


def _release_story_label(story: Mapping[str, Any], key: str, *, fallback: str = "") -> str:
    """Read one release-story label field with normalization and fallback."""
    return _normalize_release_copy(story.get(key) or "") or fallback


def _release_story_notes_label(story: Mapping[str, Any]) -> str:
    """Return the call-to-action label for release-note links."""
    return _release_story_label(story, "notes_label", fallback="Open release notes on GitHub")


def _append_unique_release_copy(items: list[str], value: Any) -> None:
    """Append normalized release copy once, preserving the original order."""
    token = _normalize_release_copy(value)
    if token and token not in items:
        items.append(token)


def _release_story_meta_tokens(*, from_version: str, to_version: str, published_at: str) -> list[str]:
    """Build source metadata chips for the optional release details."""
    tokens: list[str] = []
    if from_version and to_version and from_version != to_version:
        tokens.append(f"{from_version} -> {to_version}")
    elif to_version:
        tokens.append(to_version)
    timestamp = _format_timestamp_utc(published_at)
    if timestamp != "unknown":
        tokens.append(timestamp)
    return tokens


def _spotlight_meta_row(*, from_version: str, to_version: str, published_at: str) -> str:
    """Render the release spotlight metadata chip row."""
    tokens = _release_story_meta_tokens(
        from_version=from_version,
        to_version=to_version,
        published_at=published_at,
    )
    if not tokens:
        return ""
    return (
        '<div class="upgrade-spotlight-meta-row">'
        + "".join(f'<span class="upgrade-spotlight-chip">{html.escape(item)}</span>' for item in tokens)
        + "</div>"
    )


def render_release_spotlight_html(payload: Mapping[str, Any]) -> str:
    """Render the tooling-dashboard release spotlight when the payload is usable."""
    spotlight = _coerce_release_spotlight(payload)
    if not bool(spotlight.get("show")):
        return ""
    from_version = _format_version_label(spotlight.get("from_version"))
    to_version = _format_version_label(spotlight.get("to_version"))
    if not from_version or not to_version:
        return ""
    title = _release_story_title(spotlight)
    raw_highlights = spotlight.get("highlights")
    highlights = (
        [str(item).strip() for item in raw_highlights if str(item).strip()]
        if isinstance(raw_highlights, Sequence) and not isinstance(raw_highlights, (str, bytes, bytearray))
        else []
    )
    summary = _normalize_release_copy(spotlight.get("summary"))
    detail = _normalize_release_copy(spotlight.get("detail"))
    if not summary and highlights:
        summary = highlights[0]
    bullet_items: list[str] = []
    for item in highlights:
        if _normalize_release_copy(item) != summary:
            _append_unique_release_copy(bullet_items, item)
    notes_url = str(spotlight.get("notes_url", "")).strip()
    published_at_raw = str(spotlight.get("release_published_at", "")).strip()
    meta_row_html = _spotlight_meta_row(
        from_version=from_version,
        to_version=to_version,
        published_at=published_at_raw,
    )
    summary_html = (
        f'<p class="upgrade-spotlight-story-summary">{html.escape(summary)}</p>'
        if summary
        else ""
    )
    bullet_list_html = (
        '<ul class="upgrade-spotlight-list">'
        + "".join(f"<li>{html.escape(item)}</li>" for item in bullet_items)
        + "</ul>"
        if bullet_items
        else ""
    )
    notes_link_html = (
        f'<a class="upgrade-spotlight-link" href="{html.escape(notes_url, quote=True)}" target="_blank" rel="noopener noreferrer">{html.escape(_release_story_notes_label(spotlight))}</a>'
        if notes_url and _release_story_notes_label(spotlight)
        else ""
    )
    actions_html = (
        '<div class="upgrade-spotlight-action-row">'
        f"{notes_link_html}"
        "</div>"
        if notes_link_html
        else ""
    )
    detail_html = (
        f'<p class="upgrade-spotlight-story-summary">{html.escape(detail)}</p>'
        if detail and detail != summary and detail not in bullet_items else ""
    )
    body = str(spotlight.get("release_body") or "").strip()
    body_html = (
        f'<div class="upgrade-spotlight-body">{html.escape(body)}</div>'
        if body and not summary and not detail and not bullet_items else ""
    )
    details_html = (
        '<details class="upgrade-spotlight-details"><summary>What changed</summary>'
        f"{bullet_list_html}{detail_html}{body_html}{meta_row_html}</details>"
        if bullet_list_html or detail_html or body_html or meta_row_html else ""
    )
    return (
        '<section id="shellUpgradeSpotlight" class="upgrade-spotlight-stage" aria-label="Latest Odylith upgrade">'
        '<button id="upgradeSpotlightBackdrop" type="button" class="upgrade-spotlight-backdrop" aria-label="Close release spotlight"></button>'
        '<section class="upgrade-spotlight" role="dialog" aria-modal="true" aria-labelledby="upgradeSpotlightTitle">'
        '<button id="upgradeSpotlightDismiss" type="button" class="upgrade-spotlight-dismiss" aria-label="Close release spotlight">Close</button>'
        '<div class="upgrade-spotlight-main">'
        f'<h2 id="upgradeSpotlightTitle" class="upgrade-spotlight-title">{html.escape(title or to_version)}</h2>'
        f"{summary_html}"
        f"{details_html}"
        f"{actions_html}"
        "</div>"
        "</section>"
        "</section>"
    )
