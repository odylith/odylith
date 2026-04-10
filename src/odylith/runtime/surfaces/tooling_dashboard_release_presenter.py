"""Pure release-spotlight rendering for the tooling dashboard shell."""

from __future__ import annotations

import html
import re
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from typing import Any


def _coerce_release_spotlight(payload: Mapping[str, Any]) -> dict[str, Any]:
    return dict(payload.get("release_spotlight", {})) if isinstance(payload.get("release_spotlight"), Mapping) else {}


def _format_version_label(value: Any) -> str:
    token = str(value or "").strip()
    if not token:
        return ""
    return token if not token[:1].isdigit() else f"v{token}"


def _parse_timestamp(value: Any) -> datetime | None:
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
    parsed = _parse_timestamp(value)
    if parsed is None:
        token = str(value or "").strip()
        return token or "unknown"
    return parsed.strftime("%Y-%m-%d %H:%M UTC")


def _format_timestamp_date(value: Any) -> str:
    parsed = _parse_timestamp(value)
    if parsed is None:
        token = str(value or "").strip()
        return token[:10] if token else ""
    return parsed.strftime("%Y-%m-%d")


def _normalize_release_copy(value: Any, *, limit: int | None = 280) -> str:
    token = str(value or "").strip()
    if not token:
        return ""
    token = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", token)
    token = re.sub(r"<[^>]+>", "", token)
    token = re.sub(r"[*_`>#]", "", token)
    token = re.sub(r"\s+", " ", token).strip(" -:")
    if limit is not None and len(token) > limit:
        token = token[: limit - 3].rstrip() + "..."
    return token


def _release_story_title(story: Mapping[str, Any]) -> str:
    return _normalize_release_copy(story.get("title") or "", limit=120) or _format_version_label(
        story.get("release_tag") or story.get("to_version")
    )


def _release_story_hero_version(story: Mapping[str, Any]) -> str:
    version = _format_version_label(story.get("to_version") or story.get("release_tag"))
    title = _release_story_title(story)
    if not version or not title:
        return ""
    normalized_title = title.lower()
    normalized_version = version.lower()
    if normalized_version in normalized_title or normalized_version.removeprefix("v") in normalized_title:
        return ""
    return version


def _release_story_label(story: Mapping[str, Any], key: str, *, fallback: str = "") -> str:
    return _normalize_release_copy(story.get(key) or "", limit=120) or fallback


def _release_story_notes_label(story: Mapping[str, Any]) -> str:
    return _release_story_label(story, "notes_label", fallback="Open release note on GitHub")


def _append_unique_release_copy(items: list[str], value: Any, *, limit: int = 180) -> None:
    token = _normalize_release_copy(value, limit=limit)
    if token and token not in items:
        items.append(token)


def _release_story_body_candidates(story: Mapping[str, Any], *, limit: int = 4) -> list[str]:
    body = str(story.get("release_body") or "").strip()
    if not body:
        return []
    candidates: list[str] = []
    for raw_line in body.splitlines():
        line = str(raw_line or "").strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith(("- ", "* ", "+ ")):
            line = line[2:].strip()
        else:
            numbered = re.match(r"^\d+\.\s+(?P<text>.+)$", line)
            if numbered is None:
                continue
            line = str(numbered.group("text") or "").strip()
        _append_unique_release_copy(candidates, line)
        if len(candidates) >= limit:
            return candidates[:limit]
    for paragraph in re.split(r"\n\s*\n", body):
        _append_unique_release_copy(candidates, paragraph)
        if len(candidates) >= limit:
            return candidates[:limit]
    normalized_body = _normalize_release_copy(body, limit=None)
    if not normalized_body:
        return candidates[:limit]
    for sentence in re.split(r"(?<=[.!?])\s+", normalized_body):
        _append_unique_release_copy(candidates, sentence)
        if len(candidates) >= limit:
            break
    return candidates[:limit]


def _release_story_meta_tokens(*, from_version: str, to_version: str, published_at: str) -> list[str]:
    tokens: list[str] = []
    if from_version and to_version and from_version != to_version:
        tokens.append(f"{from_version} -> {to_version}")
    elif to_version:
        tokens.append(to_version)
    date_label = _format_timestamp_date(published_at)
    if date_label:
        tokens.append(date_label)
    return tokens


def _release_story_bullets(
    *,
    story: Mapping[str, Any],
    highlights: Sequence[str],
    summary: str,
    detail: str,
    minimum: int = 2,
    limit: int = 4,
) -> list[str]:
    bullets: list[str] = []
    for raw in highlights:
        _append_unique_release_copy(bullets, raw)
        if len(bullets) >= limit:
            return bullets[:limit]
    if len(bullets) < minimum:
        _append_unique_release_copy(bullets, detail)
    if len(bullets) < minimum:
        _append_unique_release_copy(bullets, summary)
    if len(bullets) < minimum:
        for candidate in _release_story_body_candidates(story, limit=max(limit, minimum) + 2):
            _append_unique_release_copy(bullets, candidate)
            if len(bullets) >= minimum:
                break
    return bullets[:limit]


def _spotlight_meta_row(*, from_version: str, to_version: str, published_at: str) -> str:
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
    spotlight = _coerce_release_spotlight(payload)
    if not bool(spotlight.get("show")):
        return ""
    from_version = _format_version_label(spotlight.get("from_version"))
    to_version = _format_version_label(spotlight.get("to_version"))
    if not from_version or not to_version:
        return ""
    title = _release_story_title(spotlight)
    hero_version = _release_story_hero_version(spotlight)
    raw_highlights = spotlight.get("highlights")
    highlights = (
        [str(item).strip() for item in raw_highlights if str(item).strip()]
        if isinstance(raw_highlights, Sequence) and not isinstance(raw_highlights, (str, bytes, bytearray))
        else []
    )[:3]
    summary = _normalize_release_copy(spotlight.get("summary"), limit=None)
    detail = _normalize_release_copy(spotlight.get("detail"), limit=None)
    if not summary and highlights:
        summary = highlights[0]
    bullet_items = _release_story_bullets(
        story=spotlight,
        highlights=[item for item in highlights if item != summary],
        summary=summary,
        detail=detail,
    )
    notes_url = str(spotlight.get("notes_url", "")).strip()
    published_at_raw = str(spotlight.get("release_published_at", "")).strip()
    published_at = _format_timestamp_utc(published_at_raw)
    meta_row_html = _spotlight_meta_row(
        from_version=from_version,
        to_version=to_version,
        published_at=published_at_raw,
    )
    summary_html = (
        f'<p class="upgrade-spotlight-story-summary">{html.escape(summary)}</p>'
        if summary and summary not in bullet_items
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
        f'<a class="upgrade-spotlight-link" href="{html.escape(notes_url, quote=True)}" target="_blank" rel="noreferrer">{html.escape(_release_story_notes_label(spotlight))}</a>'
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
    published_html = (
        f'<p class="upgrade-spotlight-meta">{html.escape(published_at)}</p>'
        if published_at != "unknown"
        else ""
    )
    title_html = (
        f'<span class="upgrade-spotlight-title-copy">{html.escape(title or to_version)}</span>'
        f'<span class="upgrade-spotlight-title-version">{html.escape(hero_version)}</span>'
        if hero_version
        else html.escape(title or to_version)
    )
    return (
        '<section id="shellUpgradeSpotlight" class="upgrade-spotlight-stage" aria-label="Latest Odylith upgrade">'
        '<button id="upgradeSpotlightBackdrop" type="button" class="upgrade-spotlight-backdrop" aria-label="Dismiss release spotlight"></button>'
        '<section class="upgrade-spotlight" role="dialog" aria-modal="true" aria-labelledby="upgradeSpotlightTitle">'
        '<button id="upgradeSpotlightDismiss" type="button" class="upgrade-spotlight-dismiss" aria-label="Dismiss release spotlight">'
        '<span aria-hidden="true">&times;</span>'
        "</button>"
        '<div class="upgrade-spotlight-main">'
        f"{meta_row_html}"
        f'<h2 id="upgradeSpotlightTitle" class="upgrade-spotlight-title">{title_html}</h2>'
        f"{summary_html}"
        f"{bullet_list_html}"
        f"{actions_html}"
        f"{published_html}"
        "</div>"
        "</section>"
        "</section>"
    )
