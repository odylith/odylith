"""Pure release-spotlight and release-note rendering for the tooling dashboard shell."""

from __future__ import annotations

import html
import re
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from typing import Any


def _coerce_release_spotlight(payload: Mapping[str, Any]) -> dict[str, Any]:
    return dict(payload.get("release_spotlight", {})) if isinstance(payload.get("release_spotlight"), Mapping) else {}


def _coerce_version_story(payload: Mapping[str, Any]) -> dict[str, Any]:
    return dict(payload.get("version_story", {})) if isinstance(payload.get("version_story"), Mapping) else {}


def _coerce_release_story(payload: Mapping[str, Any]) -> dict[str, Any]:
    spotlight = _coerce_release_spotlight(payload)
    if bool(spotlight.get("show")):
        return spotlight
    version_story = _coerce_version_story(payload)
    if bool(version_story.get("show")):
        return version_story
    return {}


def _format_version_label(value: Any) -> str:
    token = str(value or "").strip()
    if not token:
        return ""
    return token if not token[:1].isdigit() else f"v{token}"


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


def _release_body_paragraphs(value: Any, *, limit: int = 4, text_limit: int | None = 280) -> list[str]:
    text = str(value or "").strip()
    if not text:
        return []
    paragraphs: list[str] = []
    for segment in re.split(r"\n\s*\n", text):
        lines: list[str] = []
        for raw_line in segment.splitlines():
            line = str(raw_line or "").strip()
            if not line or line.startswith("#") or line.startswith(("- ", "* ", "+ ")):
                continue
            numbered = re.match(r"^\d+\.\s+(?P<text>.+)$", line)
            if numbered:
                line = str(numbered.group("text") or "").strip()
            normalized = _normalize_release_copy(line, limit=text_limit)
            if normalized:
                lines.append(normalized)
        paragraph = _normalize_release_copy(" ".join(lines), limit=text_limit)
        if paragraph and paragraph not in paragraphs:
            paragraphs.append(paragraph)
        if len(paragraphs) >= limit:
            break
    return paragraphs[:limit]


def _spotlight_brief(*, to_version: str) -> str:
    return f"Upgrade complete. {to_version} is live in this repo, and the full release note is ready on the right."


def _spotlight_feature_labels(highlights: Sequence[str], *, limit: int = 3) -> list[str]:
    labels: list[str] = []
    for raw_item in highlights:
        item = _normalize_release_copy(raw_item, limit=96)
        if not item:
            continue
        lowered = item.lower()
        compact = ""
        scenario_match = re.search(r"\b(\d+-scenario)\b", lowered)
        if "fails closed" in lowered or "fail-closed" in lowered:
            compact = "Fail-closed runtime trust"
        elif "proof lane" in lowered or "benchmark" in lowered:
            compact = f"{scenario_match.group(1)} proof lane" if scenario_match else "Live proof lane"
        elif lowered.startswith("exact-path grounding"):
            compact = "Exact-path grounding"
        elif "cheatsheet" in lowered:
            compact = "Built-in prompt + CLI cheatsheet"
        elif "install messaging" in lowered:
            compact = "Sharper install messaging"
        elif "shell onboarding" in lowered:
            compact = "Cleaner shell onboarding"
        elif "dashboard refresh" in lowered:
            compact = "Faster dashboard refresh"
        elif "version-story release notes" in lowered or "persistent version-story release notes" in lowered:
            compact = "Persistent version-story notes"
        elif "starter guide" in lowered and "release notes" in lowered:
            compact = "Starter guide stays separate"
        if compact:
            item = compact
        else:
            item = re.sub(
                r"^(?:Odylith(?: now)?|This release|The benchmark stack now|The shell now|The dashboard now)\s+",
                "",
                item,
                flags=re.IGNORECASE,
            )
            item = re.split(r"[,;:]", item, maxsplit=1)[0].strip().rstrip(".")
        if not item:
            continue
        item = item[:1].upper() + item[1:]
        if len(item) > 54:
            item = item[:51].rstrip() + "..."
        if item in labels:
            continue
        labels.append(item)
        if len(labels) >= limit:
            break
    if labels:
        return labels
    return [
        "New runtime active",
        "Dashboard refreshed",
        "Full release note ready",
    ][:limit]


def render_release_spotlight_html(payload: Mapping[str, Any]) -> str:
    spotlight = _coerce_release_spotlight(payload)
    if not bool(spotlight.get("show")):
        return ""
    from_version = _format_version_label(spotlight.get("from_version"))
    to_version = _format_version_label(spotlight.get("to_version"))
    if not from_version or not to_version:
        return ""
    raw_highlights = spotlight.get("highlights")
    highlights = (
        [str(item).strip() for item in raw_highlights if str(item).strip()]
        if isinstance(raw_highlights, Sequence) and not isinstance(raw_highlights, (str, bytes, bytearray))
        else []
    )[:3]
    summary = (
        str(spotlight.get("summary", "")).strip()
        or "The repo is already on the new runtime and the dashboard is ready to use."
    )
    release_url = str(spotlight.get("release_url", "")).strip()
    notes_href = str(spotlight.get("notes_href", "")).strip()
    reopen_label = f"Show {to_version} note"
    published_at = _format_timestamp_utc(spotlight.get("release_published_at"))
    spotlight_brief = _spotlight_brief(to_version=to_version)
    feature_labels = _spotlight_feature_labels(highlights)
    feature_labels_html = (
        '<div class="upgrade-spotlight-quick-group">'
        '<p class="upgrade-spotlight-quick-kicker">At a glance</p>'
        '<ul class="upgrade-spotlight-quick-list">'
        + "".join(f"<li>{html.escape(item)}</li>" for item in feature_labels)
        + "</ul>"
        "</div>"
    )
    published_html = (
        f'<p class="upgrade-spotlight-meta">Published {html.escape(published_at)}</p>'
        if published_at != "unknown"
        else ""
    )
    local_link_html = (
        f'<a class="upgrade-spotlight-link" href="{html.escape(notes_href, quote=True)}">Open full release note</a>'
        if notes_href
        else ""
    )
    remote_link_html = (
        f'<a class="upgrade-spotlight-secondary-link" href="{html.escape(release_url, quote=True)}" target="_blank" rel="noreferrer">GitHub release</a>'
        if release_url
        else ""
    )
    actions_html = (
        '<div class="upgrade-spotlight-action-row">'
        f"{local_link_html}"
        f"{remote_link_html}"
        "</div>"
        if local_link_html or remote_link_html
        else ""
    )
    return (
        '<section id="shellUpgradeSpotlight" class="upgrade-spotlight-stage" aria-label="Latest Odylith upgrade">'
        '<button id="upgradeSpotlightBackdrop" type="button" class="upgrade-spotlight-backdrop" aria-label="Dismiss release spotlight"></button>'
        '<section class="upgrade-spotlight" role="dialog" aria-modal="true" aria-labelledby="upgradeSpotlightTitle">'
        '<button id="upgradeSpotlightDismiss" type="button" class="upgrade-spotlight-dismiss" aria-label="Dismiss release spotlight">'
        '<span aria-hidden="true">&times;</span>'
        "</button>"
        '<div class="upgrade-spotlight-main">'
        '<p class="upgrade-spotlight-kicker">Fresh Odylith Release</p>'
        f'<h2 id="upgradeSpotlightTitle" class="upgrade-spotlight-title">Odylith {html.escape(to_version)} is ready here</h2>'
        f'<p class="upgrade-spotlight-subhead">Upgraded from {html.escape(from_version)}. This repo is already on the new runtime and the dashboard has been refreshed.</p>'
        f'<p class="upgrade-spotlight-story-summary">{html.escape(spotlight_brief)}</p>'
        f"{feature_labels_html}"
        f"{actions_html}"
        f"{published_html}"
        "</div>"
        '<aside class="upgrade-spotlight-notes">'
        '<p class="upgrade-spotlight-notes-kicker">Release note</p>'
        f'<h3 class="upgrade-spotlight-notes-title">What\'s new in {html.escape(to_version)}</h3>'
        f'<p class="upgrade-spotlight-notes-summary">{html.escape(summary)}</p>'
        '<ul class="upgrade-spotlight-list">'
        + "".join(f"<li>{html.escape(item)}</li>" for item in highlights)
        + "</ul>"
        f'<p class="upgrade-spotlight-notes-foot">Close this note with the X, click outside the card, or press Escape. The bottom recovery pill keeps it close for thirty minutes after the upgrade is recorded.</p>'
        "</aside>"
        "</section>"
        "</section>"
    )


def render_release_notes_html(payload: Mapping[str, Any]) -> str:
    spotlight = _coerce_release_story(payload)
    if not bool(spotlight.get("show")):
        return ""
    from_version = _format_version_label(spotlight.get("from_version"))
    to_version = _format_version_label(spotlight.get("to_version"))
    release_body = str(spotlight.get("release_body", "")).strip()
    summary = (
        str(spotlight.get("summary", "")).strip()
        or "Odylith is already running the new release in this repository."
    )
    detail = (
        str(spotlight.get("detail", "")).strip()
        or "The local shell was refreshed as part of the upgrade, so you can keep working immediately."
    )
    release_url = str(spotlight.get("release_url", "")).strip()
    published_at = _format_timestamp_utc(spotlight.get("release_published_at"))
    raw_highlights = spotlight.get("highlights")
    highlights = (
        [str(item).strip() for item in raw_highlights if str(item).strip()]
        if isinstance(raw_highlights, Sequence) and not isinstance(raw_highlights, (str, bytes, bytearray))
        else []
    )[:3]
    if not highlights:
        highlights = [
            "The repo is already aligned on the new Odylith runtime.",
            "The dashboard was refreshed immediately after the upgrade.",
        ]
    shell_repo_name = str(payload.get("shell_repo_name", "")).strip() or "Repository"
    brand_head_html = str(payload.get("brand_head_html", "")).strip()
    shell_brand_lockup_href = str(payload.get("shell_brand_lockup_href", "")).strip()
    body_paragraphs = _release_body_paragraphs(release_body, limit=4, text_limit=None)
    lead_paragraph = next((paragraph for paragraph in body_paragraphs if paragraph != summary), "")
    if not lead_paragraph and detail != summary:
        lead_paragraph = detail
    context_paragraphs = [
        paragraph
        for paragraph in body_paragraphs
        if paragraph not in {summary, lead_paragraph}
    ]
    if not context_paragraphs and detail and detail not in {summary, lead_paragraph}:
        context_paragraphs = [detail]
    if not context_paragraphs:
        context_paragraphs = [
            (
                f"This repo already moved from {from_version} to {to_version}."
                if from_version and to_version and from_version != to_version
                else f"This repo is already on {to_version}."
            ),
            "Pinned runtime, launcher, and refreshed dashboard are already in place.",
        ]
    context_html = "".join(
        f'<p class="release-note-body">{html.escape(paragraph)}</p>'
        for paragraph in context_paragraphs
    )
    lead_html = f'<p class="release-detail">{html.escape(lead_paragraph)}</p>' if lead_paragraph else ""
    highlights_html = "".join(f"<li>{html.escape(item)}</li>" for item in highlights)
    status_points = []
    if from_version and to_version and from_version != to_version:
        status_points.append(f"This repo already moved from {from_version} to {to_version}.")
    elif to_version:
        status_points.append(f"This repo is already on {to_version}.")
    status_points.append("Pinned runtime, launcher, and refreshed dashboard are already in place.")
    status_points_html = "".join(f"<li>{html.escape(item)}</li>" for item in status_points)
    github_release_html = (
        f'<a class="release-note-link" href="{html.escape(release_url, quote=True)}" target="_blank" rel="noreferrer">Open the GitHub release</a>'
        if release_url
        else ""
    )
    published_html = (
        f'<p class="release-note-meta">Published {html.escape(published_at)}</p>'
        if published_at != "unknown"
        else ""
    )
    return (
        "<!doctype html>"
        '<html lang="en">'
        "<head>"
        '  <meta charset="utf-8" />'
        '  <meta name="viewport" content="width=device-width, initial-scale=1" />'
        f"  <title>Odylith {html.escape(to_version)} Release Note</title>"
        f"  {brand_head_html}"
        "  <style>"
        ':root{color-scheme:light;--release-bg:linear-gradient(180deg,#eef4ff 0%,#f8fbff 46%,#ffffff 100%);--release-ink:#16355d;--release-panel:rgba(255,255,255,.92);--release-border:#d7e4f8;--release-pill-bg:rgba(255,255,255,.88);--release-pill-line:#cadbf7;--release-link-bg:#edf4ff;--release-link-line:#bfd8f8;}'
        'body{margin:0;background:var(--release-bg);color:var(--release-ink);font-family:"Avenir Next","Segoe UI","Helvetica Neue",sans-serif;}'
        "*{box-sizing:border-box;}"
        ".release-shell{max-width:1024px;margin:0 auto;padding:28px 18px 42px;display:grid;gap:20px;}"
        ".release-topbar{display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap;}"
        ".release-back{display:inline-flex;align-items:center;gap:8px;padding:10px 14px;border:1px solid var(--release-link-line);border-radius:999px;background:var(--release-panel);color:var(--release-ink);text-decoration:none;font-weight:700;box-shadow:0 10px 26px rgba(23,63,131,.08);}"
        ".release-brand{width:min(180px,100%);height:auto;display:block;}"
        ".release-hero{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));align-items:stretch;gap:18px;padding:24px;border:1px solid var(--release-border);border-radius:30px;background:radial-gradient(circle at 100% 0%,rgba(125,211,252,.18) 0%,transparent 30%),radial-gradient(circle at 0% 100%,rgba(255,207,138,.14) 0%,transparent 36%),linear-gradient(145deg,var(--release-panel),rgba(241,247,255,.96));box-shadow:0 28px 70px rgba(23,48,86,.14);}"
        ".release-kicker,.release-card-kicker{margin:0;font-size:11px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:#0b6a8a;}"
        ".release-title{margin:0;font-size:clamp(30px,4.4vw,52px);line-height:.95;letter-spacing:-.05em;color:var(--release-ink);max-width:12ch;}"
        ".release-subhead,.release-summary,.release-detail,.release-note-body,.release-note-meta{margin:0;color:color-mix(in srgb,var(--release-ink) 78%, white 22%);line-height:1.6;font-size:15px;}"
        ".release-body-stack{display:grid;gap:14px;align-content:start;}"
        ".release-pill-row{display:flex;flex-wrap:wrap;gap:8px;margin-top:14px;}"
        ".release-pill{display:inline-flex;align-items:center;padding:7px 12px;border:1px solid var(--release-pill-line);border-radius:999px;background:var(--release-pill-bg);font-size:12px;font-weight:700;color:var(--release-ink);}"
        ".release-card{display:grid;gap:14px;padding:20px;border:1px solid var(--release-border);border-radius:24px;background:var(--release-panel);box-shadow:0 14px 32px rgba(31,56,94,.08);}"
        ".release-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));align-items:stretch;gap:18px;}"
        ".release-list{margin:0;padding-left:18px;display:grid;gap:8px;color:color-mix(in srgb,var(--release-ink) 76%, white 24%);line-height:1.55;}"
        ".release-actions{display:flex;flex-wrap:wrap;gap:10px;align-items:center;}"
        ".release-note-link{display:inline-flex;align-items:center;justify-content:center;padding:10px 14px;border-radius:999px;border:1px solid var(--release-link-line);background:var(--release-link-bg);color:var(--release-ink);font-weight:700;text-decoration:none;box-shadow:0 10px 24px rgba(23,63,131,.08);}"
        ".release-note-mini{display:grid;gap:14px;grid-template-rows:auto 1fr auto auto;align-content:stretch;}"
        "@media (max-width: 860px){.release-hero,.release-grid{grid-template-columns:minmax(0,1fr);}.release-shell{padding:20px 14px 28px;}}"
        "  </style>"
        "</head>"
        "<body>"
        '<main class="release-shell">'
        '<div class="release-topbar">'
        '<a class="release-back" href="../index.html">Back to dashboard</a>'
        f'<img class="release-brand" src="{html.escape(shell_brand_lockup_href, quote=True)}" alt="Odylith" />'
        "</div>"
        '<section class="release-hero">'
        '<div class="release-card">'
        '<p class="release-kicker">Odylith release note</p>'
        f'<h1 class="release-title">What\'s new in {html.escape(to_version)}</h1>'
        f'<p class="release-subhead">{html.escape(summary)}</p>'
        f"{lead_html}"
        '<div class="release-pill-row">'
        f'<span class="release-pill">{html.escape(shell_repo_name)}</span>'
        f'<span class="release-pill">{html.escape(from_version)} to {html.escape(to_version)}</span>'
        "</div>"
        "</div>"
        '<aside class="release-card release-note-mini">'
        '<p class="release-card-kicker">Why it matters</p>'
        f'<div class="release-body-stack">{context_html}</div>'
        f"{published_html}"
        '<div class="release-actions">'
        f"{github_release_html}"
        "</div>"
        "</aside>"
        "</section>"
        '<section class="release-grid">'
        '<article class="release-card">'
        '<p class="release-card-kicker">What changed</p>'
        f'<ul class="release-list">{highlights_html}</ul>'
        "</article>"
        '<article class="release-card">'
        '<p class="release-card-kicker">Upgrade result in this repo</p>'
        f'<ul class="release-list">{status_points_html}</ul>'
        "</article>"
        "</section>"
        "</main>"
        "</body>"
        "</html>"
    )
