"""Inline Project-tab deeplinks for source-backed governance references."""

from __future__ import annotations

import html
import re
from urllib.parse import quote

from odylith.runtime.surfaces.dashboard_shell_links import shell_href
from odylith.runtime.surfaces.dashboard_shell_links import surface_href

_WORKSTREAM_RE = r"\bB-\d+\b"
_BUG_RE = r"\bCB-\d+\b"
_DIAGRAM_RE = r"\bD-\d+\b"
_PLAN_RE = r"\bodylith/technical-plans/(?:in-progress|done/[0-9]{4}-[0-9]{2}|done/legacy)/[A-Za-z0-9._/\-]+\.md\b"
_SURFACE_RE = r"(?<![/\w.-])(?:Registry|Radar|Compass|Atlas|Casebook)(?![/\w.-])"
_REFERENCE_RE = re.compile(
    rf"{_PLAN_RE}|{_BUG_RE}|{_WORKSTREAM_RE}|{_DIAGRAM_RE}|{_SURFACE_RE}",
    re.IGNORECASE,
)


def _canonical_surface(token: str) -> str:
    return str(token or "").strip().lower().capitalize()


def _href_for_token(token: str) -> str:
    value = str(token or "").strip()
    canonical = value.upper()
    if re.fullmatch(_BUG_RE, value, re.IGNORECASE):
        return shell_href(tab="casebook", bug=canonical)
    if re.fullmatch(_WORKSTREAM_RE, value, re.IGNORECASE):
        return shell_href(tab="radar", workstream=canonical)
    if re.fullmatch(_DIAGRAM_RE, value, re.IGNORECASE):
        return shell_href(tab="atlas", diagram=canonical)
    if re.fullmatch(_PLAN_RE, value, re.IGNORECASE):
        return quote(value.removeprefix("odylith/"))
    if re.fullmatch(_SURFACE_RE, value, re.IGNORECASE):
        return surface_href(_canonical_surface(value))
    return ""


def inline_deeplink_html(value: object) -> str:
    """Escape text and link recognized Project references to their source surface."""

    raw = str(value or "")
    if not raw:
        return ""
    parts: list[str] = []
    cursor = 0
    for match in _REFERENCE_RE.finditer(raw):
        start, end = match.span()
        if start > cursor:
            parts.append(html.escape(raw[cursor:start], quote=True))
        token = match.group(0)
        href = _href_for_token(token)
        if href:
            parts.append(
                '<a class="project-deeplink" target="_top" '
                f'href="{html.escape(href, quote=True)}">{html.escape(token, quote=True)}</a>'
            )
        else:
            parts.append(html.escape(token, quote=True))
        cursor = end
    if cursor < len(raw):
        parts.append(html.escape(raw[cursor:], quote=True))
    return "".join(parts)
